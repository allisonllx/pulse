from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from .models import timestamp, validate_signal


class BriefingStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'briefing.sqlite', timeout=30)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS signals(id TEXT, observed TEXT, payload TEXT, PRIMARY KEY(id,observed));
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT);
        ''')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.db.close()

    def save_fetch(self, run_id, source, status, signals, *, error=None, **metadata):
        signals = [validate_signal(signal.to_dict()) for signal in signals]
        payload = dict(id=run_id, source=source, status=status, itemCount=len(signals),
                       errorCode=error, finishedAt=datetime.now(timezone.utc).isoformat(), **metadata)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO runs VALUES (?,?)', (run_id, json.dumps(payload)))
            for signal in signals:
                observed = timestamp(signal.collectedAt).astimezone(timezone.utc).isoformat()
                encoded = json.dumps(signal.to_dict(), sort_keys=True, allow_nan=False)
                existing = self.db.execute('SELECT payload FROM signals WHERE id=? AND observed=?', (signal.id, observed)).fetchone()
                if existing and existing[0] != encoded:
                    raise ValueError('Conflicting immutable signal observation')
                self.db.execute('INSERT OR IGNORE INTO signals VALUES (?,?,?)', (signal.id, observed, encoded))

    def signals_between(self, start, end):
        latest = {}
        for row in self.db.execute('SELECT payload FROM signals ORDER BY observed'):
            signal = validate_signal(json.loads(row[0]))
            if start <= timestamp(signal.publishedAt) < end:
                latest[signal.id] = signal
        return list(latest.values())

    def metric_history(self, signal_id):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM signals WHERE id=? ORDER BY observed', (signal_id,))]

    def runs(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM runs ORDER BY rowid')]
