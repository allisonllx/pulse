from datetime import datetime,timezone
from dataclasses import replace
import json
import httpx
import pytest
from collector.adapters import HTTPAdapter,HTTP_CAP,FetchError
from collector.jobs import plan
from collector.settings import Settings,QUERIES
from collector.topics import TopicEngine
from collector.parsers import parse
from collector.publish import build_recording

W='2026-10-05T00:00:00Z'
RSS=b'<rss><channel><item><title>AI agents</title><link>https://example.org/agents</link></item></channel></rss>'

def test_topic_version_rollback_preserves_history(store):
    job=plan(['SG'],['google_news'],W)[0]
    items=parse(RSS,job,W)
    original=TopicEngine(store)
    mapping,_=original.assign(items)
    corrections={'version':'2','splits':{items[0]['id']:'manual-topic'},'merges':{}}
    changed=TopicEngine(store,corrections)
    assert changed.assign(items)[0][items[0]['id']]=='manual-topic'
    assert original.assign(items)[0]==mapping
    history={(r['version'],r['item_id']):r['topic_id'] for r in store.rows('membership_versions')}
    assert history[(original.version,items[0]['id'])]==mapping[items[0]['id']]
    assert history[(changed.version,items[0]['id'])]=='manual-topic'

def test_redirect_bodies_accounted_and_retained(store):
    def handler(req):
        if req.url.path=='/start':return httpx.Response(302,headers={'location':'/end'},content=b'x'*100000)
        return httpx.Response(200,content=b'ok')
    client=httpx.Client(transport=httpx.MockTransport(handler),follow_redirects=True)
    job=plan(['SG'],['google_news'],W)[0]
    adapter=HTTPAdapter(Settings(store.root,'u','p'),store)
    assert adapter.request(client,'https://example.org/start',job,'request',HTTP_CAP)==b'ok'
    assert store.spent>=100002
    assert any(r['kind']=='redirect_evidence' and r['raw_path'] for r in store.rows('attempts'))

def test_redirect_chain_hits_aggregate_cap(store):
    client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(302,headers={'location':'/next'},content=b'x'*60000)))
    job=plan(['SG'],['google_news'],W)[0]
    with pytest.raises(FetchError,match='response_too_large'):
        HTTPAdapter(Settings(store.root,'u','p'),store).request(client,'https://example.org/start',job,'request',100000)
    assert store.spent>=100000

def test_restart_closes_historical_jobs_without_fabricating_samples(store):
    jobs=plan(['SG','US'],['google_news'],W)
    store.schedule(jobs)
    assert store.claim(jobs[0])
    with store.db:store.db.execute("UPDATE jobs SET lease='1970-01-01T00:00:00Z' WHERE id=?",(jobs[0].id,))
    assert store.expire_before('2026-10-05T06:00:00Z',datetime(2026,10,5,6,1,tzinfo=timezone.utc))==2
    assert all(r['state']=='done' for r in store.rows('jobs'))
    recording=build_recording(store)
    assert all(c['status']=='missed' for s in recording['snapshots'] for c in s['coverage'])
    assert all(not s['events'] and not s['topics'] for s in recording['snapshots'])

def test_active_other_worker_not_expired(store):
    job=plan(['SG'],['google_news'],W)[0];store.schedule([job]);assert store.claim(job)
    now=datetime.now(timezone.utc)
    assert store.expire_before('2099-01-01T00:00:00Z',now)==0

def test_exact_control_queries_expiry_and_language():
    assert QUERIES==['AI agents','AI coding tools','latest AI models','music','gaming']
    job=plan(['IN'],['google_news'],W)[0]
    assert job.language=='hi'
    assert 'num=20' in plan(['SG'],['google_search'],W)[0].url
    settings=Settings(__import__('pathlib').Path('.'),expires_at='2026-10-05T12:00:00+08:00')
    assert settings.expired(datetime(2026,10,5,4,tzinfo=timezone.utc))
    settings.expires_at='1970-01-01T00:00:00Z'
    with pytest.raises(ValueError,match='expired'):settings.require_live()


def test_promotion_requires_distinct_successful_windows(store):
    jobs=plan(['SG'],['youtube'],W)
    store.schedule(jobs)
    result={'status':'success','observedCountry':'SG','observedAt':W}
    for job in jobs:store.save(job,result,[])
    assert store.rows('health')[0]['streak']==1
    assert store.rows('health')[0]['promoted']==0
    next_jobs=plan(['SG'],['youtube'],'2026-10-05T06:00:00Z');store.schedule(next_jobs)
    store.save(next_jobs[0],result,[])
    assert store.rows('health')[0]['promoted']==1

def test_archive_parquet_matches_sqlite_while_collection_appends(store,tmp_path,monkeypatch):
    import sqlite3,zipfile,shutil
    import pyarrow.parquet as pq
    from collector.archive import export_archive
    first=plan(['SG'],['google_news'],W)[0];store.schedule([first])
    store.save(first,{'status':'success','observedCountry':'SG','observedAt':W,'raw':RSS},parse(RSS,first,W))
    real_copy=shutil.copyfile
    added=False
    def copy_and_append(src,dst,*args,**kwargs):
        nonlocal added
        if not added:
            added=True
            second=plan(['US'],['google_news'],W)[0];store.schedule([second])
            store.save(second,{'status':'success','observedCountry':'US','observedAt':W,'raw':RSS},parse(RSS,second,W))
        return real_copy(src,dst,*args,**kwargs)
    monkeypatch.setattr(shutil,'copyfile',copy_and_append)
    export_archive(store,tmp_path/'recording.zip')
    with zipfile.ZipFile(tmp_path/'recording.zip') as z:z.extractall(tmp_path/'export')
    db=sqlite3.connect(tmp_path/'export/worldview.sqlite')
    count=db.execute('SELECT COUNT(*) FROM observations').fetchone()[0];db.close()
    assert count==1
    assert pq.read_table(tmp_path/'export/observations.parquet').num_rows==count
    assert len(store.rows('observations'))==2
