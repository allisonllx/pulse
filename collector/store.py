from __future__ import annotations
import gzip, hashlib, json, sqlite3,os,tempfile
from pathlib import Path
from dataclasses import asdict
from .jobs import utcnow

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending', lease TEXT, attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, country TEXT, window TEXT, profile TEXT, source TEXT, surface TEXT, query TEXT, status TEXT, observed_country TEXT, observed_at TEXT, byte_count INTEGER, promoted INTEGER, raw_hash TEXT, raw_path TEXT, extraction_version TEXT, settings TEXT, session_ref TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS items(id TEXT, observation_id TEXT, payload TEXT, PRIMARY KEY(id, observation_id));
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, job_id TEXT, kind TEXT, bytes INTEGER, status TEXT, recorded_at TEXT, raw_hash TEXT, raw_path TEXT);
CREATE TABLE IF NOT EXISTS health(country TEXT, source TEXT, streak INTEGER NOT NULL DEFAULT 0, promoted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(country, source));
CREATE TABLE IF NOT EXISTS topics(id TEXT PRIMARY KEY, label TEXT, first_seen TEXT);
CREATE TABLE IF NOT EXISTS memberships(item_id TEXT PRIMARY KEY, topic_id TEXT, version TEXT);
CREATE TABLE IF NOT EXISTS membership_versions(version TEXT, item_id TEXT, topic_id TEXT, PRIMARY KEY(version,item_id));
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""

class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "raw").mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / "worldview.sqlite", timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        existing = {r[1] for r in self.db.execute("PRAGMA table_info(attempts)")}
        for name in ("raw_hash","raw_path"):
            if name not in existing:self.db.execute("ALTER TABLE attempts ADD COLUMN "+name+" TEXT")
        health_columns={r[1] for r in self.db.execute("PRAGMA table_info(health)")}
        if 'last_window' not in health_columns:self.db.execute("ALTER TABLE health ADD COLUMN last_window TEXT")
        self.db.commit()

    def close(self):
        self.db.close()

    def preserve_raw(self,raw):
        if not raw:return None,None
        digest=hashlib.sha256(raw).hexdigest();path='raw/'+digest+'.gz'
        target=self.root/path
        if not target.exists():
            fd,tmp=tempfile.mkstemp(prefix='.raw-',dir=target.parent)
            try:
                with os.fdopen(fd,'wb') as stream:
                    stream.write(gzip.compress(raw,mtime=0));stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,target)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        return digest,path

    def schedule(self, jobs):
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO jobs(id,payload) VALUES(?,?)", [(j.id,json.dumps(asdict(j),sort_keys=True)) for j in jobs])

    def expire_before(self, window, now=None):
        """Close historical unfinished jobs as missing, never fetch today's page as history."""
        from datetime import datetime, timezone, timedelta
        from .jobs import Job
        now = now or datetime.now(timezone.utc)
        expired_lease = (now-timedelta(minutes=5)).isoformat().replace("+00:00","Z")
        count = 0
        for row in self.rows("jobs"):
            if row["state"] == "done":continue
            job = Job(**json.loads(row["payload"]))
            if job.window>=window:continue
            if row["state"]=="running" and row["lease"] and row["lease"]>=expired_lease:continue
            self.save(job,{"status":"missed","observedCountry":None,"observedAt":now.isoformat().replace("+00:00","Z"),"error":"missed_window","bytes":self.job_spent(job.id)},[])
            count += 1
        return count

    def claim(self, job, lease_seconds=300):
        from datetime import datetime, timezone, timedelta
        expired = (datetime.now(timezone.utc)-timedelta(seconds=lease_seconds)).isoformat().replace("+00:00","Z")
        with self.db:
            cur = self.db.execute("UPDATE jobs SET state='running',lease=?,attempts=attempts+1 WHERE id=? AND (state='pending' OR (state='running' AND lease<?))", (utcnow(),job.id,expired))
        return cur.rowcount == 1

    def claim_budget(self, job, allocation, budget, lease_seconds=300):
        from datetime import datetime, timezone, timedelta
        expired = (datetime.now(timezone.utc)-timedelta(seconds=lease_seconds)).isoformat().replace("+00:00","Z")
        # BEGIN IMMEDIATE serializes spend admission across foreground collectors.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            available = budget-(budget+4)//5-self.spent
            if allocation>available:
                self.db.rollback();return None
            cur = self.db.execute("UPDATE jobs SET state='running',lease=?,attempts=attempts+1 WHERE id=? AND (state='pending' OR (state='running' AND lease<?))",(utcnow(),job.id,expired))
            if not cur.rowcount:
                self.db.rollback();return None
            hold = self.db.execute("INSERT INTO attempts(job_id,kind,bytes,status,recorded_at) VALUES(?,'reservation',?,'in_flight',?)",(job.id,allocation,utcnow())).lastrowid
            self.db.commit();return hold
        except Exception:
            self.db.rollback();raise

    def settle_budget(self, reservation):
        # Interrupted attempts retain the whole conservative reservation until review.
        with self.db:self.db.execute("DELETE FROM attempts WHERE id=? AND kind='reservation'",(reservation,))

    def job_spent(self, job_id):
        return self.db.execute("SELECT COALESCE(SUM(bytes),0) FROM attempts WHERE job_id=?",(job_id,)).fetchone()[0]

    def account(self, job_id, kind, count, status, raw=b""):
        digest,path = self.preserve_raw(raw)
        with self.db:
            self.db.execute("INSERT INTO attempts(job_id,kind,bytes,status,recorded_at,raw_hash,raw_path) VALUES(?,?,?,?,?,?,?)", (job_id,kind,max(0,count),status,utcnow(),digest,path))

    @property
    def spent(self):
        return self.db.execute("SELECT COALESCE(SUM(bytes),0) FROM attempts").fetchone()[0]

    def save(self, job, result, items):
        from .settings import EXTRACTION_VERSION
        if self.db.execute("SELECT 1 FROM observations WHERE id=?",(job.id,)).fetchone():
            return
        if result["status"]=="success" and result.get("observedCountry")!=job.country:
            result = {**result,"status":"failed","error":"geography_mismatch"}
        raw = result.get("raw", b"")
        digest,raw_path = self.preserve_raw(raw)
        success = result["status"] == "success" and result.get("observedCountry") == job.country
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO health(country,source) VALUES(?,?)", (job.country,job.source))
            health=self.db.execute("SELECT streak,last_window FROM health WHERE country=? AND source=?",(job.country,job.source)).fetchone()
            from datetime import datetime,timedelta
            consecutive=health['last_window'] and datetime.fromisoformat(job.window.replace('Z','+00:00'))-datetime.fromisoformat(health['last_window'].replace('Z','+00:00'))==timedelta(hours=6)
            same_window=health['last_window']==job.window
            streak=(health['streak'] if same_window else health['streak']+1 if consecutive else 1) if success else 0
            self.db.execute("UPDATE health SET streak=?,promoted=?,last_window=? WHERE country=? AND source=?",(streak,streak>=2,job.window,job.country,job.source))
            promoted = self.db.execute("SELECT promoted FROM health WHERE country=? AND source=?",(job.country,job.source)).fetchone()[0]
            self.db.execute("INSERT OR REPLACE INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (job.id,job.id,job.country,job.window,job.profile,job.source,job.surface,job.query,result["status"],result.get("observedCountry"),result.get("observedAt",utcnow()),result.get("bytes",0),promoted,digest,raw_path,EXTRACTION_VERSION,json.dumps(job.settings),result.get("sessionRef"),result.get("error","")))
            self.db.execute("DELETE FROM items WHERE observation_id=?",(job.id,))
            for item in items if success else []:
                self.db.execute("INSERT OR IGNORE INTO items VALUES(?,?,?)",(item["id"],job.id,json.dumps(item,ensure_ascii=False)))
            self.db.execute("UPDATE jobs SET state='done',lease=NULL WHERE id=?",(job.id,))

    def rows(self, table):
        if table not in {"jobs","observations","items","attempts","health","topics","memberships","membership_versions","meta"}:
            raise ValueError("Unknown table")
        return [dict(r) for r in self.db.execute("SELECT * FROM " + table)]
