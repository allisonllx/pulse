from datetime import timezone
from email.utils import parsedate_to_datetime
import hashlib
import re
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from ..config import matching_lenses
from ..models import validate_signal, timestamp
from ..normalize import canonical_url


def parse_feed(raw, source, observed_at, catalog):
    root = ET.fromstring(raw)
    signals, rejected = [], 0
    atom = '{http://www.w3.org/2005/Atom}'
    entries = root.findall('.//item') + root.findall(atom + 'entry')
    for entry in entries[:100]:
        def text(name):
            return entry.findtext(name) or entry.findtext(atom + name) or ''
        try:
            title = BeautifulSoup(text('title'), 'html.parser').get_text(' ', strip=True)
            link = text('link')
            if not link:
                links = entry.findall(atom + 'link')
                link = next((node.get('href') for node in links if node.get('rel', 'alternate') == 'alternate'), '')
            article_url = canonical_url(link)
            url = canonical_url(text('comments')) if source.get('evidenceKind') == 'discussion' and text('comments') else article_url
            date = text('pubDate') or text('published')
            if not date:
                raise ValueError('Missing publication date')
            try:
                published = timestamp(date)
            except ValueError:
                published = parsedate_to_datetime(date)
            if published.tzinfo is None:
                raise ValueError('Missing date timezone')
            excerpt = BeautifulSoup(text('description') or text('summary') or text('content'), 'html.parser').get_text(' ', strip=True)[:600]
            metrics = {}
            if source['id'] == 'hacker-news':
                for name, pattern in [('points', r'Points:\s*(\d+)'), ('comments', r'# Comments:\s*(\d+)')]:
                    match = re.search(pattern, excerpt)
                    if match:
                        metrics[name] = int(match.group(1))
                counts = [f'{metrics[key]} {key}' for key in ('points', 'comments') if key in metrics]
                excerpt = 'Public discussion on Hacker News' + (': ' + ' and '.join(counts) + ' at collection.' if counts else '.')
            signals.append(validate_signal(dict(
                id=hashlib.sha256((source['id'] + ':' + url).encode()).hexdigest()[:24], canonicalUrl=url,
                source=source['id'], sourceType='rss', publishedAt=published.astimezone(timezone.utc).isoformat(),
                collectedAt=observed_at, title=title, excerpt=excerpt or None,
                authorOrPublisher=source.get('label', source['id']),
                lensCandidates=matching_lenses(title + ' ' + excerpt, catalog), matchedQueries=[],
                metrics=metrics, evidenceUrls=[article_url] if url != article_url else [], evidenceKind=source.get('evidenceKind', 'factual'),
                publisherGroup=source.get('publisherGroup', source['id']))))
        except (ValueError, TypeError, OverflowError):
            rejected += 1
    return signals, rejected
