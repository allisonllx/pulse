"""Read-only OpenCLI adapters. Browser access requires a separate explicit opt-in."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlsplit
from ..config import matching_lenses
from ..external import BackendError, run_json_command
from ..models import timestamp, validate_signal
from ..normalize import canonical_url


def parse_posts(rows, source, observed_at, catalog):
    if not isinstance(rows, list):
        raise ValueError('Expected OpenCLI post list')
    signals, rejected = [], 0
    platform = source['type']
    for row in rows[:20]:
        try:
            url = canonical_url(row['url'])
            host = urlsplit(url).hostname
            allowed = {'x.com', 'twitter.com', 'www.x.com'} if platform == 'x' else {'reddit.com', 'www.reddit.com'}
            if host not in allowed:
                raise ValueError('Unexpected post domain')
            if platform == 'x':
                published = parsedate_to_datetime(row['created_at'])
                title, excerpt = row['text'][:200], row['text'][:600]
                metric_keys = ('likes', 'views')
            else:
                if type(row.get('created_utc')) not in (int, float) or row['created_utc'] <= 0:
                    raise ValueError('Missing Reddit publication time')
                published = datetime.fromtimestamp(row['created_utc'], timezone.utc)
                title, excerpt = row['title'], row.get('selftext', '')[:600]
                metric_keys = ('score', 'comments')
            if published.tzinfo is None:
                raise ValueError('Missing timezone')
            metrics = {}
            for key in metric_keys:
                value = row.get(key)
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                if type(value) in (int, float) and value >= 0:
                    metrics[key] = value
            signals.append(validate_signal(dict(id=hashlib.sha256((source['id'] + ':' + url).encode()).hexdigest()[:24],
                           canonicalUrl=url, source=source['id'], sourceType=platform,
                           publishedAt=published.astimezone(timezone.utc).isoformat(), collectedAt=observed_at,
                           title=title, excerpt=excerpt or None, authorOrPublisher=row.get('author'),
                           lensCandidates=matching_lenses(title + ' ' + excerpt, catalog), matchedQueries=source.get('queries', []),
                           metrics=metrics, evidenceUrls=[], evidenceKind='discussion', publisherGroup=source['id'])))
        except (KeyError, ValueError, TypeError, AttributeError, OverflowError, OSError):
            rejected += 1
    return signals, rejected


def fetch_browser_posts(source, observed_at, catalog, *, runner=run_json_command):
    if os.getenv('PULSE_BROWSER_SOURCES') != '1':
        raise BackendError('browser_consent_required')
    local = Path(__file__).resolve().parents[3] / '.worldview/tools/opencli/node_modules/.bin/opencli'
    binary = str(local) if local.is_file() else shutil.which('opencli')
    if not binary:
        raise BackendError('missing_opencli')
    queries, limit = source.get('queries', []), source.get('limit', 10)
    if not isinstance(queries, list) or not 1 <= len(queries) <= 2 or type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError('Invalid bounded browser request')
    signals, rejected = [], 0
    for query in queries:
        if not isinstance(query, str) or not 1 <= len(query) <= 120 or query.startswith('-'):
            raise ValueError('Invalid browser query')
        if source['type'] == 'x':
            now = timestamp(observed_at)
            query += ' since:' + (now - timedelta(days=7)).date().isoformat() + ' until:' + (now + timedelta(days=1)).date().isoformat()
            args = ['twitter', 'search', query, '--product', 'top']
        else:
            args = ['reddit', 'search', query, '--time', 'week', '--sort', 'top']
        raw = runner([binary, *args, '--limit', str(limit), '-f', 'json'])
        payload = json.loads(raw)
        if isinstance(payload, dict):
            if payload.get('ok') is not True:
                raise BackendError('browser_backend_unavailable')
            payload = payload.get('data')
        found, skipped = parse_posts(payload, source, observed_at, catalog)
        signals.extend(found); rejected += skipped
    return list({s.id: s for s in signals}.values()), rejected
