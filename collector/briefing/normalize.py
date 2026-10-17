from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from .models import public_url


def canonical_url(url: str) -> str:
    public_url(url)
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in {'fbclid', 'gclid'}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(query), ''))
