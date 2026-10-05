from __future__ import annotations
from collections import Counter
import hashlib, json, re, unicodedata
from pathlib import Path

ENGINE_VERSION = "topics-2"
STOP = {"the","a","an","and","of","to","in","for","on","with","new","news","latest","launches","launch","announces","announced","de","do","da","o","e","el","la","le","der","die","das","un","une"}
GLOSSARY = {"inteligência artificial":"artificial intelligence", "inteligencia artificial":"artificial intelligence",
 "intelligence artificielle":"artificial intelligence", "künstliche intelligenz":"artificial intelligence",
 "人工知能":"artificial intelligence", "인공지능":"artificial intelligence", "kecerdasan buatan":"artificial intelligence",
 "tecnologia":"technology", "technologie":"technology", "música":"music", "musique":"music", "音楽":"music",
 "ゲーム":"gaming", "jogos":"gaming", "cultura":"culture", "文化":"culture", "lança":"launches", "lancement":"launch",
 "actualización":"update", "atualização":"update", "mise à jour":"update", "アップデート":"update"}
KNOWN = {"openai","anthropic","google","apple","microsoft","meta","nvidia","samsung","sony","nintendo","tiktok","youtube","tesla","swift","drake","beyoncé","claude","chatgpt","gemini","gpt","llama"}


def normalize(title):
    text = unicodedata.normalize("NFKC",title).casefold()
    for key,value in GLOSSARY.items(): text = text.replace(key," "+value+" ")
    return " ".join(re.findall(r"[^\W_]+",text,flags=re.UNICODE))


def signature(title):
    norm = normalize(title)
    tokens = set(norm.split())-STOP
    entities = tokens & KNOWN
    numbers = set(re.findall(r"\d+(?:\.\d+)?",title))
    # Preserve other explicit proper nouns, excluding sentence-initial capitalization.
    proper = {x.casefold() for x in re.findall(r"\b[A-Z][a-z]{2,}\b",title)[1:] if x.casefold() not in STOP}
    return norm,tokens,entities,proper,numbers


def compatible(a,b):
    sa,sb = signature(a),signature(b)
    if sa[4] != sb[4]: return False
    if sa[2] and sb[2] and sa[2] != sb[2]: return False
    if sa[3] and sb[3] and not (sa[3]&sb[3]): return False
    return True


def token_match(a,b):
    sa,sb = signature(a),signature(b)
    if not compatible(a,b): return False
    if sa[0] == sb[0]: return True
    common = sa[1]&sb[1]
    return len(common)>=2 and len(common)/max(1,len(sa[1]|sb[1]))>=0.8

class TopicEngine:
    def __init__(self,store,corrections=None,embeddings=False):
        self.store = store
        self.corrections = corrections or {"version":"1","merges":{},"splits":{}}
        self.encoder = None
        self.method = "deterministic-token-fallback"
        if embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
                self.method = "multilingual-sentence-transformer"
            except (ImportError,OSError):
                self.method = "deterministic-token-fallback (embeddings unavailable)"
        model_revision = None
        if self.encoder:
            model_revision = getattr(self.encoder[0].auto_model.config,"_commit_hash",None)
        payload = {"engine":ENGINE_VERSION,"method":self.method,"modelRevision":model_revision,"corrections":self.corrections}
        self.version = hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
        self.vectors = {}

    def match(self,a,b):
        if token_match(a,b): return True
        if not self.encoder or not compatible(a,b): return False
        for title in (a,b):
            if title not in self.vectors:
                self.vectors[title] = self.encoder.encode(title,normalize_embeddings=True)
        return float(self.vectors[a] @ self.vectors[b]) >= 0.82

    def assign(self,items):
        db = self.store.db
        # Only this version's immutable membership history can seed an incremental run.
        membership = {r["item_id"]:r["topic_id"] for r in db.execute("SELECT * FROM membership_versions WHERE version=?",(self.version,))}
        topic_ids = set(membership.values())
        topics = {r["id"]:dict(r) for r in db.execute("SELECT * FROM topics ORDER BY first_seen,id") if r["id"] in topic_ids}
        if self.encoder and items:
            titles = sorted({i["title"] for i in items} | {t["label"] for t in topics.values()})
            vectors = self.encoder.encode(titles,normalize_embeddings=True,batch_size=32)
            self.vectors.update(zip(titles,vectors))
        mapping = {}
        for item in sorted(items,key=lambda x:(x["observedAt"],x["id"])):
            topic_id = self.corrections.get("splits",{}).get(item["id"]) or membership.get(item["id"])
            if not topic_id:
                topic_id = next((tid for tid,t in topics.items() if self.match(item["title"],t["label"])),None)
            if not topic_id: topic_id = "topic-"+hashlib.sha256(item["id"].encode()).hexdigest()[:16]
            merges = self.corrections.get("merges",{})
            visited = set()
            while topic_id in merges:
                if topic_id in visited: raise ValueError("Correction merge cycle")
                visited.add(topic_id);topic_id = merges[topic_id]
            if topic_id not in topics:
                topics[topic_id] = {"id":topic_id,"label":item["title"],"first_seen":item["observedAt"]}
            if item["observedAt"]<topics[topic_id]["first_seen"]: topics[topic_id]["first_seen"] = item["observedAt"]
            membership[item["id"]] = topic_id
            mapping[item["id"]] = topic_id
        with db:
            for t in topics.values(): db.execute("INSERT INTO topics VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET first_seen=MIN(topics.first_seen,excluded.first_seen)",(t["id"],t["label"],t["first_seen"]))
            for item_id,topic_id in mapping.items():
                db.execute("INSERT OR REPLACE INTO memberships VALUES(?,?,?)",(item_id,topic_id,self.version))
                db.execute("INSERT OR IGNORE INTO membership_versions VALUES(?,?,?)",(self.version,item_id,topic_id))
            db.execute("INSERT OR REPLACE INTO meta VALUES('cluster_version',?)",(self.version,))
            db.execute("INSERT OR REPLACE INTO meta VALUES('cluster_method',?)",(self.method,))
        return mapping,topics


def category(title):
    t = normalize(title)
    if re.search(r"\b(ai|llm|gpt|agents?|gemini|anthropic|deepseek|llama)\b",t): return "ai"
    for key,tokens in {"ai":["artificial intelligence","openai","chatgpt","claude"],"technology":["technology","apple","google","nvidia"],"gaming":["gaming","nintendo","playstation"],"music":["music","swift","drake"],"culture":["culture","film","cinema"],"news":["election","president","earthquake"]}.items():
        if any(token in t for token in tokens): return key
    return "other"
