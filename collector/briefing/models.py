from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
import math
from urllib.parse import parse_qsl, urlsplit
from zoneinfo import ZoneInfo


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result
    except (ValueError, AttributeError, TypeError):
        raise ValueError('Expected a timestamp with timezone') from None


def public_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
            raise ValueError()
        if any(key.lower() in {'api_key', 'apikey', 'access_token', 'token', 'password', 'key', 'secret'}
               for key, _ in parse_qsl(parts.query)):
            raise ValueError()
        _ = parts.port
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Invalid public URL') from None
    return value


def previous_week(now: datetime, timezone: str = 'Asia/Singapore') -> tuple[datetime, datetime]:
    if now.tzinfo is None:
        raise ValueError('Expected timezone-aware current time')
    local = now.astimezone(ZoneInfo(timezone))
    end = local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=local.weekday())
    return end - timedelta(days=7), end


@dataclass(frozen=True)
class Signal:
    id: str
    canonicalUrl: str
    source: str
    sourceType: str
    publishedAt: str
    collectedAt: str
    title: str
    excerpt: str | None
    authorOrPublisher: str | None
    lensCandidates: list[str]
    matchedQueries: list[str]
    metrics: dict[str, float | None]
    evidenceUrls: list[str]
    evidenceKind: str = 'discovery'
    publisherGroup: str = ''
    entities: list[str] = field(default_factory=list)
    eventTerms: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def validate_signal(value: dict, *, window: tuple[datetime, datetime] | None = None) -> Signal:
    try:
        signal = Signal(**value)
        for key in ('id', 'source', 'title'):
            if not isinstance(getattr(signal, key), str) or not getattr(signal, key).strip():
                raise ValueError('Missing signal identity or title')
        public_url(signal.canonicalUrl)
        for url in signal.evidenceUrls:
            public_url(url)
        published, collected = timestamp(signal.publishedAt), timestamp(signal.collectedAt)
        if published > collected or window and not window[0] <= published < window[1]:
            raise ValueError('Publication timestamp outside valid window')
        if signal.sourceType not in {'news', 'rss', 'search', 'reddit', 'youtube', 'github', 'x'}:
            raise ValueError('Unknown source type')
        if signal.evidenceKind not in {'factual', 'announcement', 'discussion', 'discovery'}:
            raise ValueError('Unknown evidence kind')
        if not isinstance(signal.lensCandidates, list) or not signal.lensCandidates or any(lens not in {'all', 'tech'} for lens in signal.lensCandidates):
            raise ValueError('Unknown lens')
        for metric in signal.metrics.values():
            if metric is not None and (type(metric) not in (int, float) or not math.isfinite(metric) or metric < 0):
                raise ValueError('Invalid metric')
        for key in ('matchedQueries', 'entities', 'eventTerms', 'evidenceUrls'):
            if not isinstance(getattr(signal, key), list) or any(not isinstance(x, str) for x in getattr(signal, key)):
                raise ValueError('Expected string list')
        if signal.excerpt is not None and not isinstance(signal.excerpt, str):
            raise ValueError('Invalid excerpt')
        return signal
    except (TypeError, AttributeError) as error:
        raise ValueError('Malformed signal') from error
