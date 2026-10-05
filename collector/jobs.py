from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlencode
import hashlib, json
from .settings import COUNTRIES, QUERIES, CAPABILITIES


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def window_at(value=None):
    dt = value or datetime.now(timezone.utc)
    return dt.replace(hour=dt.hour // 6 * 6, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")

@dataclass(frozen=True)
class Job:
    country: str
    window: str
    profile: str
    source: str
    surface: str
    query: str | None
    url: str
    language: str
    adapter: str = "http"

    @property
    def id(self):
        return hashlib.sha256(json.dumps({k:getattr(self,k) for k in ("country","window","profile","source","surface","query","language")}, sort_keys=True).encode()).hexdigest()[:24]

    @property
    def settings(self):
        return {"hl": self.language, "gl": self.country if self.profile == "local" else "US",
                "acceptLanguage": self.language, "loggedIn": False, "personalization": False}


def plan(countries, sources, window=None, profile="all", news_surface="local_rss"):
    if news_surface not in ("local_rss", "local_html"):
        raise ValueError("News surface must be local_rss or local_html")
    jobs = []
    for country in countries:
        if country not in COUNTRIES:
            raise ValueError("Unknown country: " + country)
        for source in sources:
            if source not in CAPABILITIES:
                raise ValueError("Unknown source: " + source)
            source_profile = CAPABILITIES[source]["profile"]
            if profile not in ("all", source_profile):
                continue
            lang = COUNTRIES[country][2] if source_profile == "local" else "en"
            queries = [None] if source == "google_news" else QUERIES
            if source == "tiktok":
                # Experimental capability is a single bounded probe per invocation.
                if any(j.source == "tiktok" for j in jobs):
                    continue
                queries = [QUERIES[0]]
            for query in queries:
                surface = news_surface if source == "google_news" else CAPABILITIES[source]["surfaces"][0]
                if source == "google_news":
                    url = "https://news.google.com/" + ("rss?" if surface == "local_rss" else "?") + urlencode({"hl":lang, "gl":country, "ceid":country+":"+lang})
                elif source == "google_search":
                    url = "https://www.google.com/search?" + urlencode({"q":query, "hl":"en", "gl":"us", "pws":"0", "num":"20"})
                elif source == "youtube":
                    url = "https://www.youtube.com/results?" + urlencode({"search_query":query, "hl":"en", "gl":"US"})
                else:
                    url = "https://www.tiktok.com/search?" + urlencode({"q":query, "lang":"en"})
                jobs.append(Job(country, window or window_at(), source_profile, source, surface, query, url, lang, CAPABILITIES[source]["adapter"]))
    return jobs
