import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from .adapters.rss import parse_feed
from .adapters.github import parse_releases
from .adapters.youtube import fetch_youtube, parse_videos
from .adapters.browser_social import fetch_browser_posts, parse_posts
from .config import load_catalog
from .models import timestamp
from .transport import Transport, FetchError
from .external import BackendError


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
                if source['type'] in {'x', 'reddit'}:
                    method = 'opencli-browser-search'
                    if fixture_dir:
                        signals, rejected = parse_posts(json.loads((Path(fixture_dir) / (source_id + '.json')).read_text()), source, now, catalog)
                    else:
                        signals, rejected = fetch_browser_posts(source, now, catalog)
                    status = 'partial' if rejected and signals else 'success' if signals else 'empty'
                elif source['type'] == 'youtube':
                    method = 'yt-dlp-public-search'
                    if fixture_dir:
                        signals, rejected = parse_videos(json.loads((Path(fixture_dir) / (source_id + '.json')).read_text()), source, now, catalog)
                    else:
                        signals, rejected = fetch_youtube(source, now, catalog)
                    status = 'partial' if rejected and signals else 'success' if signals else 'empty'
                elif source['type'] not in {'rss', 'github'}:
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
            error = str(exc) if isinstance(exc, (FetchError, BackendError)) else type(exc).__name__
            if isinstance(exc, BackendError) and str(exc) in {'missing_yt_dlp', 'missing_js_runtime', 'login_required', 'browser_consent_required', 'missing_opencli', 'browser_backend_unavailable', 'browser_bridge_unavailable'}:
                status = 'unavailable'
        reasons = {'missing_yt_dlp': 'Install the collector social extra (yt-dlp).',
                   'backend_failed': 'The source backend returned an error; other sources remain available.',
                   'backend_timeout': 'The source exceeded its collection time limit.',
                   'output_limit': 'The source exceeded its metadata size limit.',
                   'missing_js_runtime': 'YouTube needs Node.js or another supported runtime.',
                   'login_required': 'The platform requested a logged-in session; no automatic login was attempted.',
                   'browser_consent_required': 'Browser connection not enabled. Connect and authorize a Chrome session to collect this source.',
                   'missing_opencli': 'Install OpenCLI and its Chrome Browser Bridge, then log in to the source.',
                   'browser_bridge_unavailable': 'OpenCLI cannot connect to its Chrome Browser Bridge.',
                   'rate_limited': 'The platform rate-limited collection; no immediate retry was attempted.'}
        signals = list({signal.id: signal for signal in signals}.values())
        store.save_fetch(run_id, source_id, status, signals, error=error,
                         rejectedCount=rejected, startedAt=now, discoveryMethod=method,
                         reason=reasons.get(error) or source.get('reason'), catalogVersion=catalog.version, sourceCatalogVersion=source_version)
        reports.append(store.runs()[-1] if store.runs()[-1]['id'] == run_id else next(row for row in store.runs() if row['id'] == run_id))
    return reports
