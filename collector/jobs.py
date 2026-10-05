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
        settings={"hl": self.language, "gl": None if self.source in {"instagram","tiktok","bing","reddit"} else self.country if self.profile == "local" else "US",
                "acceptLanguage": self.language, "loggedIn": False, "personalization": False}
        if self.surface=='discovery_week_popular':settings['uploadDateFilter']='this_week';settings['sort']='platform_popularity';settings['querySet']='discovery-v1'
        if self.source=='tiktok' and self.surface.startswith('creative_center'):
            from urllib.parse import urlsplit,parse_qs
            settings['platformRegion']=parse_qs(urlsplit(self.url).query).get('region',[None])[0]
        return settings


def plan(countries, sources, window=None, profile="all", news_surface="local_rss",youtube_surface="search_html",query_set=None):
    if query_set not in {None,'discovery-v1'}:raise ValueError('Unknown query set')
    if query_set=='discovery-v1' and any(source!='youtube' for source in sources):raise ValueError('Discovery query set is currently validated for YouTube only')
    if news_surface not in ("local_rss", "local_html"):
        raise ValueError("News surface must be local_rss or local_html")
    jobs = []
    for country in countries:
        if country not in COUNTRIES:
            raise ValueError("Unknown country: " + country)
        for source in sources:
            if source not in CAPABILITIES:
                raise ValueError("Unknown source: " + source)
            source_profile = "local" if source=="youtube" and youtube_surface=="gaming_discovery" else CAPABILITIES[source]["profile"]
            if profile not in ("all", source_profile):
                continue
            lang = COUNTRIES[country][2] if source_profile == "local" else "en"
            queries = [None] if source in {"google_news","reddit"} or (source=="youtube" and youtube_surface=="gaming_discovery") else QUERIES
            if query_set=='discovery-v1' and source in {'bing','youtube'} and queries!=[None]:
                from .discovery import discovery_queries
                queries=discovery_queries(window or window_at(),source)
            if source in {"tiktok","instagram"}:
                # Experimental capability is a single bounded probe per invocation.
                if any(j.source == source for j in jobs):
                    continue
                queries = [QUERIES[0]]
            for query in queries:
                surface = news_surface if source == "google_news" else youtube_surface if source=="youtube" else CAPABILITIES[source]["surfaces"][0]
                if query_set=='discovery-v1' and source in {'bing','youtube'} and query is not None:surface='discovery_week_popular' if source=='youtube' else 'discovery_search'
                if source == "google_news":
                    url = "https://news.google.com/" + ("rss?" if surface == "local_rss" else "?") + urlencode({"hl":lang, "gl":country, "ceid":country+":"+lang})
                elif source == "google_search":
                    url = "https://www.google.com/search?" + urlencode({"q":query, "hl":"en", "gl":"us", "pws":"0", "num":"20"})
                elif source == "youtube":
                    url = ("https://www.youtube.com/gaming?"+urlencode({'hl':lang,'gl':country})) if youtube_surface=='gaming_discovery' else "https://www.youtube.com/results?" + urlencode({"search_query":query, "hl":"en", "gl":"US"})
                elif source == 'instagram':
                    url = 'https://www.instagram.com/explore/search/keyword/?'+urlencode({'q':query})
                elif source == 'bing':
                    url = 'https://www.bing.com/search?'+urlencode({'q':query,'setlang':'en-US'})
                elif source == 'reddit':
                    url = 'https://www.reddit.com/r/popular/'
                else:
                    url = "https://www.tiktok.com/search?" + urlencode({"q":query, "lang":"en"})
                if source=='youtube' and surface=='discovery_week_popular':url+='&'+urlencode({'sp':'CAMSAggD'})
                jobs.append(Job(country, window or window_at(), source_profile, source, surface, query, url, lang, CAPABILITIES[source]["adapter"]))
    return jobs


def plan_watches(countries,queries,window=None):
    jobs=[]
    for country in countries:
        if country not in COUNTRIES:raise ValueError('Unknown country: '+country)
        language=COUNTRIES[country][2]
        for query in queries:
            if not isinstance(query,str) or not query.strip() or len(query)>160:raise ValueError('Invalid watch query')
            url='https://news.google.com/rss/search?'+urlencode({'q':'"'+query.strip()+'"','hl':language,'gl':country,'ceid':country+':'+language})
            jobs.append(Job(country,window or window_at(),'local','google_news','watch_rss',query.strip(),url,language))
    return jobs
