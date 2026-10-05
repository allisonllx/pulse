from dataclasses import replace
from datetime import datetime,timezone
import gzip,hashlib,json,sqlite3,zipfile
from pathlib import Path
import httpx,pytest
from collector.jobs import plan,window_at
from collector.settings import Settings,PILOT,QUERIES
from collector.store import Store
from collector.parsers import parse,canonical_url
from collector.adapters import HTTPAdapter,redact,proxy_parts,JOB_RESERVATION,MAX_ATTEMPTS,location_country
from collector.cli import collect,budget_status,main
from collector.publish import publish,build_recording
from collector.archive import export_archive,restore_archive
from collector.topics import TopicEngine,token_match

W = "2026-10-05T00:00:00Z"
RSS = b'<rss><channel><item><title>OpenAI artificial intelligence update</title><link>https://example.org/a</link><description>&lt;b&gt;hello&lt;/b&gt;</description></item><item><title>duplicate</title><link>https://example.org/a</link></item><item><title>unsafe</title><link>javascript:alert(1)</link></item></channel></rss>'

def job(window=W):return plan(["SG"],["google_news"],window)[0]

def save(store,j,raw=RSS,status="success",country="SG"):
    store.schedule([j]);assert store.claim(j)
    items = parse(raw,j,j.window)
    result = {"status":status,"observedCountry":country,"observedAt":j.window,"bytes":100,"raw":raw,"sessionRef":"opaque"}
    store.save(j,result,items)
    return items

def client(handler):
    return lambda **kwargs:httpx.Client(transport=httpx.MockTransport(handler),follow_redirects=True)


def test_plan_settings_and_caps():
    jobs = plan(PILOT,["google_news","google_search","youtube"],W)
    assert len(jobs)==66
    assert len(plan(PILOT,["tiktok"],W))==1
    assert len(plan(PILOT,["google_news","youtube"],W,profile="english"))==30
    for j in jobs:
        assert j.settings["gl"]== (j.country if j.profile=="local" else "US")
        if j.source!="google_news":assert j.language=="en" and j.query in QUERIES
    assert replace(jobs[0],adapter="playwright").id==jobs[0].id
    assert window_at(datetime(2026,1,1,11,59,tzinfo=timezone.utc)).endswith("06:00:00Z")


def test_rss_dedupe_and_provenance():
    items = parse(RSS,job(),W)
    assert len(items)==1 and items[0]["rank"]==1
    assert items[0]["snippet"]=="hello"
    assert items[0]["surface"]=="local_rss" and items[0]["observationId"]==job().id
    assert canonical_url("javascript:x") is None
    assert canonical_url("https://user:pass@example.org") is None
    assert parse(b"malformed",job())==[]


def test_html_surfaces():
    j = replace(job(),surface="local_html")
    assert parse(b'<article><a class="gPFEn" href="./articles/one">Local news</a></article>',j)[0]["url"].startswith("https://news.google.com/")
    j = plan(["US"],["google_search"],W)[0]
    items = parse(b'<a href="/url?q=https%3A%2F%2Fexample.org%2Farticle"><h3>Search result</h3></a>',j)
    assert items[0]["url"]=="https://example.org/article"
    j = plan(["US"],["youtube"],W)[0]
    raw = b'<script>var ytInitialData = {"contents":{"videoRenderer":{"videoId":"abc123","title":{"runs":[{"text":"Video title"}]}}}};</script>'
    assert parse(raw,j)[0]["url"]=="https://www.youtube.com/watch?v=abc123"


def test_verified_sticky_session_and_raw(store):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200,json={"country":"SG"}) if "ip.oxylabs" in str(request.url) else httpx.Response(200,content=RSS)
    settings = Settings(store.root,"name","secret",budget_bytes=100_000_000)
    proxies = []
    def factory(**kwargs):
        proxies.append(kwargs["proxy"])
        return client(handler)(**kwargs)
    result,items = HTTPAdapter(settings,store,factory,sleep=lambda _:None).fetch(job())
    assert result["status"]=="success" and len(items)==1 and len(calls)==3
    assert len(set(proxies))==1 and "sessid-" in proxies[0]
    store.schedule([job()]);assert store.claim(job());store.save(job(),result,items)
    obs = store.rows("observations")[0]
    assert gzip.decompress((store.root/obs["raw_path"]).read_bytes())==RSS
    assert obs["raw_hash"]==hashlib.sha256(RSS).hexdigest()
    assert obs["extraction_version"] and json.loads(obs["settings"])["hl"]=="en"
    assert {a["kind"] for a in store.rows("attempts")}=={"location","request"}


def test_geo_mismatch_blocks_fetch(store):
    calls = []
    def handler(request):calls.append(request);return httpx.Response(200,json={"country":"JP"})
    result,items = HTTPAdapter(Settings(store.root,"u","p"),store,client(handler),lambda _:None).fetch(job())
    assert result["status"]=="failed" and result["error"]=="geography_mismatch"
    assert not items and len(calls)==1 and store.spent>0


def test_changed_geo_keeps_failed_raw(store):
    calls = [0]
    def handler(request):
        calls[0]+=1
        if calls[0]==2:return httpx.Response(200,content=RSS)
        return httpx.Response(200,json={"country":"SG" if calls[0]==1 else "US"})
    result,items = HTTPAdapter(Settings(store.root,"u","p"),store,client(handler),lambda _:None).fetch(job())
    assert result["error"]=="geography_changed" and result["raw"]==RSS and not items


def test_bounded_retries_charge_failures_and_redact(store):
    attempts = []
    def handler(request):attempts.append(1);raise httpx.ConnectError("secret http://u:p@private.example 1.2.3.4")
    settings = Settings(store.root,"u","secret","private.example")
    result,items = HTTPAdapter(settings,store,client(handler),lambda _:None).fetch(job())
    assert len(attempts)==MAX_ATTEMPTS and not items and store.spent>=3*32000
    assert "secret" not in json.dumps(result,default=str) and "private.example" not in json.dumps(result,default=str)
    redacted = redact("secret https://private.example 1.2.3.4",settings)
    assert "secret" not in redacted and "1.2.3.4" not in redacted


def test_idempotency_restart_health(store):
    save(store,job())
    assert not store.claim(job())
    other = Store(store.root)
    assert not other.claim(job())
    save(other,job("2026-10-05T06:00:00Z"))
    assert other.rows("health")[0]["promoted"]==1
    save(other,job("2026-10-05T12:00:00Z"),status="failed")
    assert other.rows("health")[0]["streak"]==0
    other.close()
    orphan = job("2026-10-05T18:00:00Z");store.schedule([orphan]);assert store.claim(orphan)
    with store.db:store.db.execute("UPDATE jobs SET lease='1970-01-01T00:00:00Z' WHERE id=?",(orphan.id,))
    assert store.claim(orphan)


def test_budget_dry_run_and_no_live_without_credentials(store):
    settings = Settings(store.root,budget_bytes=1000)
    report = collect(store,settings,[job()],dry_run=True)
    assert report["budget"]["remainingBytes"]==800 and report["budget"]["reserveBytes"]==200
    assert report["projectedBytes"]==JOB_RESERVATION and not report["fitsBudget"]
    assert not store.rows("jobs") and store.spent==0
    with pytest.raises(ValueError,match="OXYLABS"):collect(store,settings,[job()])
    with pytest.raises(ValueError,match="Projected"):collect(store,Settings(store.root,"u","p",budget_bytes=1000),[job()])


def test_partial_failure_visible_without_departures(store):
    save(store,job())
    save(store,job("2026-10-05T06:00:00Z"),status="failed")
    save(store,job("2026-10-05T12:00:00Z"),raw=RSS.replace(b"example.org/a",b"example.org/b"))
    recording = build_recording(store)
    assert [s["coverage"][0]["status"] for s in recording["snapshots"]]==["success","failed","success"]
    assert all(not s["events"] for s in recording["snapshots"])


def test_events_comparable_contiguous_and_first_seen(store):
    first = save(store,job())
    second = save(store,job("2026-10-05T06:00:00Z"),raw=RSS.replace(b"example.org/a",b"example.org/b").replace(b"OpenAI",b"Apple"))
    recording = build_recording(store)
    assert not recording["snapshots"][0]["events"]
    events = recording["snapshots"][1]["events"]
    assert {(e["kind"],e["itemId"]) for e in events}=={("departure",first[0]["id"]),("arrival",second[0]["id"])}
    assert recording["snapshots"][1]["topics"][0]["firstSeen"]=="2026-10-05T06:00:00Z"
    save(store,job("2026-10-05T18:00:00Z"),raw=RSS)
    assert not build_recording(store)["snapshots"][-1]["events"]


def test_publish_contract_immutable_and_no_private_fields(store,tmp_path):
    empty = publish(store,tmp_path/"public")
    assert empty["mode"]=="recording" and empty["coverage"]=={"successful":0,"failed":0}
    save(store,job())
    a = publish(store,tmp_path/"public");b = publish(store,tmp_path/"public")
    assert a==b and a["recordingUrl"].startswith("/data/")
    payload = (tmp_path/"public"/a["datasetVersion"]/"recording.json").read_text()
    assert all(s not in payload for s in ["sessionRef","raw_path","proxy","password","settings"])
    data = json.loads(payload)
    assert set(data)=={"schemaVersion","mode","generatedAt","clusterVersion","countries","windows","snapshots"}
    assert data["snapshots"][0]["topics"][0]["score"]==1


def test_topics_stable_corrections_and_collisions(store):
    items = save(store,job())
    engine = TopicEngine(store);mapping,_ = engine.assign(items)
    assert engine.assign(items)[0]==mapping
    corrections = {"version":"2","splits":{items[0]["id"]:"topic-manual"},"merges":{}}
    corrected,_ = TopicEngine(store,corrections).assign(items)
    assert corrected[items[0]["id"]]=="topic-manual"
    assert len(store.rows("membership_versions"))==2
    assert not token_match("Apple artificial intelligence update","OpenAI artificial intelligence update")
    assert not token_match("GPT 4 release","GPT 5 release")


def test_export_restore_parquet_checksums_corruption(store,tmp_path):
    save(store,job());build_recording(store)
    result = export_archive(store,tmp_path/"export.zip")
    restored = tmp_path/"restored"
    restore_archive(result["path"],restored)
    other = Store(restored)
    assert build_recording(other)==build_recording(store);other.close()
    with zipfile.ZipFile(result["path"]) as archive:
        assert "observations.parquet" in archive.namelist()
        files = {name:archive.read(name) for name in archive.namelist()}
    files["worldview.sqlite"]+=b"corrupt"
    corrupt = tmp_path/"corrupt.zip"
    with zipfile.ZipFile(corrupt,"w") as archive:
        for name,data in files.items():archive.writestr(name,data)
    with pytest.raises(ValueError,match="Checksum"):restore_archive(corrupt,tmp_path/"bad")
    with pytest.raises(ValueError,match="empty destination"):restore_archive(result["path"],restored)


def test_restore_path_traversal(tmp_path):
    source = tmp_path/"traversal.zip"
    with zipfile.ZipFile(source,"w") as archive:archive.writestr("../secret",b"x")
    with pytest.raises(ValueError,match="Unsafe"):restore_archive(source,tmp_path/"restored")
    assert not (tmp_path/"secret").exists()


def test_oxylabs_provider_consensus():
    assert location_country(b'{"providers":{"dbip":{"country":"SG"},"maxmind":{"country":"SG"}}}')=="SG"
    assert location_country(b'{"providers":{"dbip":{"country":"SG"},"maxmind":{"country":"JP"}}}')==""


def test_atomic_budget_admission_and_crash_charge(store):
    jobs = plan(["SG","US"],["google_news"],W);store.schedule(jobs)
    budget = JOB_RESERVATION*2
    token = store.claim_budget(jobs[0],JOB_RESERVATION,budget)
    assert token and store.spent==JOB_RESERVATION
    other = Store(store.root)
    assert other.claim_budget(jobs[1],JOB_RESERVATION,budget) is None
    assert other.spent==JOB_RESERVATION
    store.account(jobs[0].id,"request",100,"success")
    store.settle_budget(token)
    assert other.spent==100
    assert other.claim_budget(jobs[1],JOB_RESERVATION,budget)
    other.close()


def test_failed_content_evidence_exported(store,tmp_path):
    def handler(request):
        if "ip.oxylabs" in str(request.url):return httpx.Response(200,json={"providers":{"dbip":{"country":"SG"},"maxmind":{"country":"SG"}}})
        return httpx.Response(403,content=b"blocked evidence")
    result,items = HTTPAdapter(Settings(store.root,"u","p"),store,client(handler),lambda _:None).fetch(job())
    assert result["status"]=="failed" and not items
    failed = [a for a in store.rows("attempts") if a["kind"]=="request"]
    assert len(failed)==3 and all(a["raw_hash"] for a in failed)
    assert gzip.decompress((store.root/failed[0]["raw_path"]).read_bytes())==b"blocked evidence"
    output = export_archive(store,tmp_path/"failed.zip")
    restore_archive(output["path"],tmp_path/"restored-failure")
    assert (tmp_path/"restored-failure"/failed[0]["raw_path"]).exists()
