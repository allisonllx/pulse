import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from .adapters.rss import parse_feed
from .adapters.github import parse_releases
from .config import load_catalog
from .models import timestamp
from .transport import Transport, FetchError


ROOT = Path(__file__).resolve().parents[2]


def collect_sources(sources, store, now, *, fixture_dir=None, dry_run=False):
    timestamp(now)
    catalog = load_catalog(ROOT / 'config/briefing-lenses.json')
    source_version = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()[:16]
    reports = []
    for source in sources:
        source_id = source['id']
        if not source_id.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Invalid source identifier')
        run_id = hashlib.sha256((source_id + now).encode()).hexdigest()[:24]
        if dry_run:
            reports.append(dict(source=source_id, status='planned' if source['enabled'] else 'disabled'))
            continue
        status, error, rejected, signals = 'disabled', None, 0, []
        method = source.get('type', 'unknown')
        try:
            if source['enabled']:
                if source['type'] not in {'rss', 'github'}:
                    status, error = 'unavailable', 'provider_not_configured'
                else:
                    if fixture_dir:
                        raw = (Path(fixture_dir) / (source_id + ('.json' if source['type'] == 'github' else '.xml'))).read_bytes()
                    else:
                        url = source['url']
                        with Transport(source.get('allowedHosts', [urlsplit(url).hostname])) as transport:
                            raw = transport.get(url).content
                    from .evidence import preserve_raw
                    preserve_raw(store.root, raw)
                    signals, rejected = (parse_releases(json.loads(raw), source, now, catalog) if source['type'] == 'github'
                                         else parse_feed(raw, source, now, catalog))
                    status = 'partial' if rejected and signals else 'success' if signals else 'empty'
        except Exception as exc:
            status = 'failed'
            error = str(exc) if isinstance(exc, FetchError) else type(exc).__name__
        signals = list({signal.id: signal for signal in signals}.values())
        store.save_fetch(run_id, source_id, status, signals, error=error,
                         rejectedCount=rejected, startedAt=now, discoveryMethod=method,
                         reason=source.get('reason'), catalogVersion=catalog.version, sourceCatalogVersion=source_version)
        reports.append(store.runs()[-1] if store.runs()[-1]['id'] == run_id else next(row for row in store.runs() if row['id'] == run_id))
    return reports
