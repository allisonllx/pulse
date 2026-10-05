from __future__ import annotations
import gzip, hashlib, json, os, re, shutil, sqlite3, tempfile, zipfile
from pathlib import Path, PurePosixPath
from .store import Store
from .publish import canonical


def export_archive(store,destination):
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ValueError("Export requires pyarrow; install the collector dependencies.") from None
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        backup = sqlite3.connect(root/"worldview.sqlite")
        store.db.backup(backup);backup.close()
        # Every export format must represent the same committed SQLite snapshot,
        # even while the collector is appending new observations.
        snapshot = sqlite3.connect(root/"worldview.sqlite")
        snapshot.row_factory=sqlite3.Row
        tables = ["observations","items","attempts","health","topics","memberships","membership_versions"]
        rows_by_table={table:[dict(r) for r in snapshot.execute("SELECT * FROM "+table)] for table in tables}
        snapshot.close()
        for row in rows_by_table["observations"]+rows_by_table["attempts"]:
            if row["raw_path"]:
                source = store.root/row["raw_path"]
                target = root/row["raw_path"];target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
        for table in tables:
            rows = rows_by_table[table]
            # Explicit empty table schema preserves a usable Parquet file.
            arrow = pa.Table.from_pylist(rows) if rows else pa.table({"_empty":pa.array([],type=pa.string())})
            pq.write_table(arrow,root/(table+".parquet"))
        files = sorted(p for p in root.rglob("*") if p.is_file())
        manifest = {"schemaVersion":1,"files":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        (root/"checksums.json").write_bytes(canonical(manifest))
        fd,tmp = tempfile.mkstemp(prefix=".export-",dir=destination.parent);os.close(fd)
        try:
            with zipfile.ZipFile(tmp,"w",compression=zipfile.ZIP_DEFLATED) as archive:
                for p in sorted(root.rglob("*")):
                    if p.is_file(): archive.write(p,str(p.relative_to(root)))
            os.replace(tmp,destination)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    return {"path":str(destination),"sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),"files":len(manifest["files"])}


def restore_archive(source,destination):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()): raise ValueError("Restore requires an empty destination; existing evidence is never overwritten.")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".restore-",dir=destination.parent) as temporary:
        staging = Path(temporary)/"data";staging.mkdir()
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(names)!=len(set(names)):raise ValueError("Duplicate archive paths")
            if sum(i.file_size for i in infos)>2_000_000_000:raise ValueError("Archive too large")
            for info in infos:
                p = PurePosixPath(info.filename)
                if p.is_absolute() or ".." in p.parts or "\\" in info.filename or not p.parts or (info.external_attr>>16)&0o170000 == 0o120000:
                    raise ValueError("Unsafe archive path")
            if "checksums.json" not in names:raise ValueError("Missing checksums")
            manifest = json.loads(archive.read("checksums.json"))
            if manifest.get("schemaVersion")!=1 or set(names)!=(set(manifest.get("files",{}))|{"checksums.json"}):raise ValueError("Checksum inventory mismatch")
            for name,digest in manifest["files"].items():
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest()!=digest:raise ValueError("Checksum mismatch: "+name)
                target = staging/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        if not (staging/"worldview.sqlite").exists():raise ValueError("Missing SQLite database")
        db = sqlite3.connect("file:"+str(staging/"worldview.sqlite")+"?mode=ro",uri=True)
        try:
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Corrupt SQLite database")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"jobs","observations","items","attempts","health","topics","memberships","membership_versions","meta"}<=tables:raise ValueError("Invalid database schema")
            if db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]:raise ValueError("Unexpected database triggers")
            for raw_path,digest in db.execute("SELECT raw_path,raw_hash FROM observations WHERE raw_path IS NOT NULL UNION SELECT raw_path,raw_hash FROM attempts WHERE raw_path IS NOT NULL"):
                if not digest or not re.fullmatch(r"[0-9a-f]{64}",digest) or raw_path != "raw/"+digest+".gz":raise ValueError("Invalid raw path")
                with gzip.open(staging/raw_path,"rb") as raw_stream:raw = raw_stream.read(10_000_001)
                if len(raw)>10_000_000:raise ValueError("Raw evidence too large")
                if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("Raw evidence hash mismatch")
        finally:db.close()
        # Copy the validated snapshot through SQLite backup to ensure a clean database.
        clean = staging/"clean.sqlite"
        src = sqlite3.connect(staging/"worldview.sqlite");dst = sqlite3.connect(clean)
        src.backup(dst);dst.close();src.close();os.replace(clean,staging/"worldview.sqlite")
        if destination.exists():destination.rmdir()
        os.replace(staging,destination)
    return {"restored":str(destination),"files":len(manifest["files"])}
