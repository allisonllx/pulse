import hashlib
from bs4 import BeautifulSoup
from ..config import matching_lenses
from ..models import validate_signal
from ..normalize import canonical_url


def parse_releases(rows, source, observed_at, catalog):
    if not isinstance(rows, list):
        raise ValueError('Invalid GitHub release response')
    signals, rejected = [], 0
    for row in rows[:30]:
        if row.get('draft'):
            continue
        try:
            url = canonical_url(row['html_url'])
            title = source.get('label', source['id']) + ': ' + (row.get('name') or row['tag_name'])
            excerpt = BeautifulSoup(row.get('body') or '', 'html.parser').get_text(' ', strip=True)[:600]
            signals.append(validate_signal(dict(id=hashlib.sha256((source['id'] + ':' + url).encode()).hexdigest()[:24], canonicalUrl=url,
                           source=source['id'], sourceType='github', publishedAt=row['published_at'], collectedAt=observed_at,
                           title=title, excerpt=excerpt or None, authorOrPublisher=source.get('label', source['id']),
                           lensCandidates=['all', 'tech'], matchedQueries=[], metrics={}, evidenceUrls=[], evidenceKind='announcement',
                           publisherGroup=source.get('publisherGroup', source['id']))))
        except (ValueError, KeyError, TypeError):
            rejected += 1
    return signals, rejected
