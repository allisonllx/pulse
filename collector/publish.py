from __future__ import annotations
from collections import defaultdict
import hashlib, json, os, tempfile
from pathlib import Path
from .settings import COUNTRIES
from .topics import TopicEngine,category
from .jobs import utcnow


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()


def build_recording(store,corrections=None,embeddings=False):
    observations = sorted(store.rows("observations"),key=lambda r:(r["window"],r["country"],r["profile"],r["source"],r["surface"],r["query"] or ""))
    all_items = [json.loads(r["payload"]) for r in store.rows("items")]
    by_observation = defaultdict(list)
    for item in all_items: by_observation[item["observationId"]].append(item)
    engine = TopicEngine(store,corrections,embeddings)
    mapping,topics = engine.assign(all_items)
    snapshots = {}
    previous = {}
    for obs in observations:
        snapshot_key = obs["country"],obs["window"],obs["profile"]
        snap = snapshots.setdefault(snapshot_key,{"country":obs["country"],"window":obs["window"],"profile":obs["profile"],"coverage":[],"topics":[],"events":[]})
        items = sorted(by_observation[obs["id"]],key=lambda x:x["rank"])
        snap["coverage"].append({"source":obs["source"],"surface":obs["surface"],"query":obs["query"],"status":obs["status"],"itemCount":len(items),"observedCountry":obs["observed_country"],"observedAt":obs["observed_at"],"observationId":obs["id"],"bytes":obs["byte_count"],"promoted":bool(obs["promoted"])})
        # A failure or skipped six-hour window breaks comparison continuity.
        key = obs["country"],obs["profile"],obs["source"],obs["surface"],obs["query"]
        current = {i["id"]:i for i in items}
        prior = previous.get(key)
        if obs["status"] == "success":
            from datetime import datetime,timedelta
            consecutive = prior and datetime.fromisoformat(obs["window"].replace("Z","+00:00"))-datetime.fromisoformat(prior[0].replace("Z","+00:00")) == timedelta(hours=6)
            if consecutive:
                for kind,ids in [("arrival",current.keys()-prior[1].keys()),("departure",prior[1].keys()-current.keys())]:
                    for item_id in sorted(ids):
                        event_id = hashlib.sha256(canonical([key,obs["window"],kind,item_id])).hexdigest()[:24]
                        snap["events"].append({"id":event_id,"topicId":mapping[item_id],"itemId":item_id,"source":obs["source"],"kind":kind,"window":obs["window"]})
            previous[key] = obs["window"],current
        else:
            previous.pop(key,None)
    for snap in snapshots.values():
        grouped = defaultdict(list)
        for cov in snap["coverage"]:
            if cov["status"] == "success":
                for item in by_observation[cov["observationId"]]: grouped[mapping[item["id"]]].append(item)
        for topic_id,items in grouped.items():
            topic = topics[topic_id]
            platforms = defaultdict(float)
            # Every reciprocal rank belongs to exactly one source/surface/query observation.
            for item in items: platforms[item["source"]] += 1/item["rank"]
            aliases = sorted({i["title"] for i in items if i["title"] != topic["label"]})
            snap["topics"].append({"id":topic_id,"label":topic["label"],"aliases":aliases,"category":category(topic["label"]),"score":round(sum(platforms.values()),6),"count":len(items),"firstSeen":topic["first_seen"],"platforms":{k:round(v,6) for k,v in sorted(platforms.items())},"items":sorted(items,key=lambda x:(x["source"],x["surface"],x["query"] or "",x["rank"]))})
        snap["topics"].sort(key=lambda t:(-t["score"],t["id"]))
    country_codes = sorted({o["country"] for o in observations})
    generated = max((o["observed_at"] for o in observations),default="1970-01-01T00:00:00Z")
    return {"schemaVersion":1,"mode":"recording","generatedAt":generated,"clusterVersion":engine.version,"countries":[{"code":c,"name":COUNTRIES[c][0],"flag":COUNTRIES[c][1],"language":COUNTRIES[c][2]} for c in country_codes],"windows":sorted({o["window"] for o in observations}),"snapshots":list(snapshots.values())}


def atomic_write(path,data):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name = tempfile.mkstemp(prefix=".tmp-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def publish(store,destination,corrections=None,embeddings=False):
    recording = build_recording(store,corrections,embeddings)
    payload = canonical(recording)
    version = hashlib.sha256(payload).hexdigest()[:24]
    root = Path(destination)
    recording_path = root/version/"recording.json"
    if recording_path.exists() and recording_path.read_bytes()!=payload: raise ValueError("Immutable recording collision")
    if not recording_path.exists(): atomic_write(recording_path,payload)
    coverage = [c for s in recording["snapshots"] for c in s["coverage"]]
    manifest = {"schemaVersion":1,"datasetVersion":version,"generatedAt":recording["generatedAt"],"mode":"recording","recordingUrl":"/data/"+version+"/recording.json","countries":[c["code"] for c in recording["countries"]],"windows":recording["windows"],"coverage":{"successful":sum(c["status"]=="success" for c in coverage),"failed":sum(c["status"]!="success" for c in coverage)},"clusterVersion":recording["clusterVersion"]}
    atomic_write(root/"manifest.json",canonical(manifest))
    return manifest
