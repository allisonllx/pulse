from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from urllib.parse import urlencode
from ..config import matching_lenses
from ..external import BackendError, run_json_command
from ..models import validate_signal


def parse_videos(rows, source, observed_at, catalog):
    signals, rejected = [], 0
    for row in rows:
        try:
            video_id = row['id']
            if not isinstance(video_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                raise ValueError('Invalid video id')
            published = row.get('timestamp') or row.get('release_timestamp')
            if type(published) not in (int, float):
                # A calendar date alone cannot establish an exact window boundary.
                raise ValueError('Missing exact publication timestamp')
            title = row['title']
            description = (row.get('description') or '')[:600]
            url = 'https://www.youtube.com/watch?v=' + video_id
            metrics = {label: row[key] for key, label in [('view_count', 'views'), ('like_count', 'likes'), ('comment_count', 'comments')]
                       if type(row.get(key)) in (int, float) and row[key] >= 0}
            signals.append(validate_signal(dict(id=hashlib.sha256((source['id'] + ':' + url).encode()).hexdigest()[:24],
                           canonicalUrl=url, source=source['id'], sourceType='youtube',
                           publishedAt=datetime.fromtimestamp(published, timezone.utc).isoformat(), collectedAt=observed_at,
                           title=title, excerpt=description or None, authorOrPublisher=row.get('channel') or row.get('uploader'),
                           lensCandidates=matching_lenses(title + ' ' + description, catalog), matchedQueries=source.get('queries', []),
                           metrics=metrics, evidenceUrls=[], evidenceKind='discussion', publisherGroup=row.get('channel_id') or source['id'])))
        except (ValueError, TypeError, KeyError, OverflowError, OSError):
            rejected += 1
    return signals, rejected


def fetch_youtube(source, observed_at, catalog, *, runner=run_json_command):
    if runner is run_json_command and not importlib.util.find_spec('yt_dlp'):
        raise BackendError('missing_yt_dlp')
    node = shutil.which('node')
    if not node:
        raise BackendError('missing_js_runtime')
    limit = source.get('limit', 3)
    queries = source.get('queries', [])
    if type(limit) is not int or not 1 <= limit <= 5 or not 1 <= len(queries) <= 2:
        raise ValueError('Invalid bounded YouTube request')
    signals, rejected = [], 0
    for query in queries:
        if not isinstance(query, str) or not 1 <= len(query) <= 120:
            raise ValueError('Invalid YouTube query')
        # Reuse the project's verified This week + popularity search surface.
        search_url = 'https://www.youtube.com/results?' + urlencode({'search_query': query, 'hl': 'en', 'gl': 'US', 'sp': 'CAMSAggD'})
        metadata_template = '%(.{id,title,timestamp,release_timestamp,channel,uploader,channel_id,view_count,like_count,comment_count,description})j'
        command = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-plugin-dirs', '--no-cache-dir',
                   '--skip-download', '--print', metadata_template, '--no-progress', '--no-warnings',
                   '--playlist-end', str(limit), '--socket-timeout', '10', '--retries', '0',
                   '--extractor-retries', '0', '--js-runtimes', 'node:' + node,
                   '--', search_url]
        raw = runner(command)
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        found, skipped = parse_videos(rows, dict(source, queries=[query]), observed_at, catalog)
        signals.extend(found); rejected += skipped
    return list({s.id: s for s in signals}.values()), rejected
