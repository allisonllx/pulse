"""Keyword scans: bounded public search discovery, never platform popularity estimates."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import unicodedata
import uuid
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .concepts import get_concept
from .adapters import HTTPAdapter
from .cli import allocation_for, budget_status
from .jobs import Job, utcnow
from .publish import atomic_write, build_recording, canonical
from .settings import COUNTRIES
from .store import Store

DEFAULT_COUNTRIES = ['SG', 'US', 'GB', 'JP']
SOCIAL_DOMAINS = {'instagram': ('instagram.com',), 'tiktok': ('tiktok.com',),
                  'x': ('x.com', 'twitter.com'), 'reddit': ('reddit.com',)}
SCAN_VERSION = 'keyword-v1'


def normalize_keyword(value):
    if not isinstance(value, str):raise ValueError('Enter a keyword.')
    value = ' '.join(unicodedata.normalize('NFKC', value).split())
    if not value or len(value) > 100 or not any(c.isalnum() for c in value):
        raise ValueError('Use a keyword between 1 and 100 characters.')
    if any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('The keyword contains unsupported characters.')
    return value


def normalize_countries(values):
    if not isinstance(values, list) or not values or len(values) > 8:
        raise ValueError('Choose between 1 and 8 countries.')
    if any(not isinstance(c, str) or c not in COUNTRIES for c in values):
        raise ValueError('Unknown country.')
    return list(dict.fromkeys(values))


QUERY_LANGUAGES = {'en','de','es','fr','hi','id','ja','ko','pt','sv','zh'}


def normalize_query_language(language='en'):
    if not isinstance(language, str) or language not in QUERY_LANGUAGES:
        raise ValueError('Choose a supported search language.')
    return language


def cache_key(keyword, countries, concept_id=None, query_language='en'):
    query_language = normalize_query_language(query_language)
    if concept_id:
        concept = get_concept(concept_id)
        return hashlib.sha256(canonical([concept['version'], concept_id, concept['aliases'], sorted(countries), query_language])).hexdigest()[:24]
    parts = [SCAN_VERSION, normalize_keyword(keyword).casefold(), sorted(countries)]
    if query_language != 'en':parts.append(query_language)
    return hashlib.sha256(canonical(parts)).hexdigest()[:24]


def phrase(keyword):
    # Keep user text inside one literal phrase, so it cannot inject search operators.
    return '"' + keyword.replace('"', ' ').replace('\\', ' ') + '"'


def plan_scan(keyword, countries, scan_id, observed_at=None, query_language='en'):
    keyword = normalize_keyword(keyword)
    countries = normalize_countries(countries)
    query_language = normalize_query_language(query_language)
    timestamp = observed_at or utcnow()
    jobs = []
    queries = [('web', phrase(keyword))] + [(platform, 'site:' + domains[0] + ' ' + phrase(keyword)) for platform, domains in SOCIAL_DOMAINS.items()]
    for country in countries:
        profile = 'english' if query_language == 'en' else 'local'
        for channel, query in queries:
            # No explicit Google country setting: the verified residential country varies.
            url = 'https://www.google.com/search?' + urlencode({'q': query, 'hl': query_language, 'pws': '0', 'num': '20'})
            jobs.append(Job(country, timestamp, profile, 'google_search', 'scan_' + channel + '_' + scan_id, query, url, query_language))
        news = 'https://news.google.com/rss/search?' + urlencode({'q': phrase(keyword), 'hl': query_language, 'gl': country, 'ceid': country + ':' + query_language})
        jobs.append(Job(country, timestamp, profile, 'google_news', 'scan_news', phrase(keyword), news, query_language))
        video = 'https://www.youtube.com/results?' + urlencode({'search_query': keyword, 'hl': query_language, 'gl': country if profile == 'local' else 'US', 'sp': 'CAMSAggD'})
        jobs.append(Job(country, timestamp, profile, 'youtube', 'scan_video', keyword, video, query_language))
    return jobs


def plan_concept(concept, countries, scan_id, observed_at=None):
    timestamp = observed_at or utcnow()
    jobs = []
    for index, alias in enumerate(concept['aliases']):
        for job in plan_scan(alias['term'], countries, scan_id, timestamp):
            if index == 0 or job.surface.split('_')[1] in {'web', 'news', 'video'}:
                jobs.append(job)
    # Market terms are intentionally additive and country-scoped. They are kept
    # separate from the English control queries so comparisons stay like-for-like.
    for country in countries:
        language = COUNTRIES[country][2]
        for term in concept.get('marketTerms', {}).get(country, []):
            local_phrase = phrase(term)
            news = 'https://news.google.com/rss/search?' + urlencode({
                'q': local_phrase, 'hl': language, 'gl': country, 'ceid': country + ':' + language})
            video = 'https://www.youtube.com/results?' + urlencode({
                'search_query': term, 'hl': language, 'gl': country, 'sp': 'CAMSAggD'})
            jobs.extend((
                Job(country, timestamp, 'local', 'google_news', 'scan_news', local_phrase, news, language),
                Job(country, timestamp, 'local', 'youtube', 'scan_video', local_phrase, video, language),
            ))
    return jobs


def fallback_job(job):
    locale = {'en':'en-US','de':'de-DE','es':'es-ES','fr':'fr-FR','hi':'hi-IN','id':'id-ID','ja':'ja-JP','ko':'ko-KR','pt':'pt-BR','sv':'sv-SE','zh':'zh-CN'}.get(job.language,'en-US')
    return replace(job, source='bing', url='https://www.bing.com/search?' + urlencode({'q': job.query, 'setlang': locale}))


def tokens(text):
    return re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', text).casefold())


def discovery_evidence(job, title, url, snippet):
    channel = job.surface.split('_')[1]
    if channel in SOCIAL_DOMAINS:
        host = urlsplit(url).hostname or ''
        if not any(host == d or host.endswith('.' + d) for d in SOCIAL_DOMAINS[channel]):return None
    keyword = re.sub(r'^site:\S+\s+', '', job.query or '').strip('"')
    wanted = set(tokens(keyword))
    found = set(tokens(title + ' ' + snippet))
    matched = len(wanted & found)
    if any(ord(c) > 127 for c in keyword) and unicodedata.normalize('NFKC', keyword).casefold() in unicodedata.normalize('NFKC', title + ' ' + snippet).casefold():
        matched = len(wanted)
    if not wanted or matched / len(wanted) < 0.6:return None
    # Preserve literal snippet metrics; don't turn them into inferred engagement rates.
    metrics = re.findall(r'(?i)\b[\d,.]+\s*[kmb]?\s+(?:likes|views|comments|reposts|upvotes)\b', snippet)
    freshness = re.search(r'(?i)\b(?:\d+\s+(?:minutes?|hours?|days?|weeks?|months?|years?)\s+ago|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})\b', snippet)
    return {'platform': channel if channel in SOCIAL_DOMAINS else channel,
            'engine': job.source, 'relevance': round(matched / len(wanted), 3),
            'freshnessLabel': freshness.group(0) if freshness else None,
            'engagementLabels': metrics[:4],
            'basis': 'indexed-search' if channel in SOCIAL_DOMAINS else 'public-search'}


class ScanManager:
    """One worker owns collection. Requests inspect atomically saved scan documents."""
    def __init__(self, settings, publication=Path('public/data/scans'), adapter_factory=None):
        self.settings = settings
        self.root = settings.data_dir / 'scans'
        self.root.mkdir(parents=True, exist_ok=True)
        self.publication = Path(publication)
        self.adapter_factory = adapter_factory
        self._translation_cache = None
        self._translator = None
        self._translation_lock = threading.Lock()

    def translate(self, texts, language):
        from .translations import LocalTranslator, TranslationCache, translate_texts
        with self._translation_lock:
            if self._translation_cache is None:
                self._translation_cache = TranslationCache(self.settings.data_dir / 'scan-translations.sqlite')
                self._translator = LocalTranslator()
            return translate_texts(texts, language, self._translation_cache, self._translator)

    def read(self, scan_id):
        if not re.fullmatch(r'[a-f0-9]{24}', scan_id):raise ValueError('Invalid scan ID.')
        path = self.root / (scan_id + '.json')
        return json.loads(path.read_text()) if path.exists() else None

    def cached(self, keyword, countries, concept_id=None, query_language='en'):
        key = cache_key(keyword, countries, concept_id, query_language)
        candidates = [json.loads(p.read_text()) for p in self.root.glob('*.json')]
        return max((s for s in candidates if s['key'] == key and s['status'] in {'complete','partial'}), key=lambda s: s['createdAt'], default=None)

    def active(self, keyword, countries, concept_id=None, query_language='en'):
        key = cache_key(keyword, countries, concept_id, query_language)
        return next((scan for path in self.root.glob('*.json')
                     if (scan := json.loads(path.read_text()))['key'] == key and scan['status'] in {'queued', 'running'}), None)

    def create(self, keyword, countries, concept_id=None, query_language='en'):
        concept = get_concept(concept_id) if concept_id else None
        if concept:keyword = concept['label']
        keyword, countries = normalize_keyword(keyword), normalize_countries(countries)
        query_language = 'en' if concept else normalize_query_language(query_language)
        self.settings.require_live()
        scan_id = uuid.uuid4().hex[:24]
        jobs = plan_concept(concept, countries, scan_id) if concept else plan_scan(keyword, countries, scan_id, query_language=query_language)
        worst = sum(allocation_for(j) * (2 if j.source == 'google_search' else 1) for j in jobs)
        store = Store(self.settings.data_dir)
        try:
            if worst > budget_status(store, self.settings)['remainingBytes']:
                raise ValueError('This scan exceeds the remaining traffic budget. Choose fewer countries.')
        finally:store.close()
        scan = {'id': scan_id, 'key': cache_key(keyword, countries, concept_id, query_language), 'keyword': keyword, 'queryLanguage': query_language,
                'countries': countries, 'createdAt': jobs[0].window, 'status': 'queued',
                'planned': len(jobs), 'completed': 0, 'events': [], 'recording': None,
                'version': SCAN_VERSION}
        if concept:scan['concept'] = concept
        self.save(scan)
        return scan

    def save(self, scan):
        atomic_write(self.root / (scan['id'] + '.json'), canonical(scan))

    def catalog(self):
        path = self.publication / 'index.json'
        return json.loads(path.read_text()) if path.exists() else []

    def publish(self, scan):
        # Only completed evidence is public. Private raw data and credentials stay local.
        path=self.publication / (scan['id'] + '.json')
        payload=canonical(scan)
        if path.exists() and path.read_bytes()!=payload:raise ValueError('Immutable scan collision.')
        if not path.exists():atomic_write(path,payload)
        catalog = [s for s in self.catalog() if s['key'] != scan['key']]
        catalog.insert(0, {k: scan[k] for k in ('id','key','keyword','countries','createdAt','status','queryLanguage') if k in scan})
        if scan.get('concept'):catalog[0]['conceptId'] = scan['concept']['id']
        atomic_write(self.publication / 'index.json', canonical(catalog[:24]))

    def run(self, scan_id):
        scan = self.read(scan_id)
        if not scan or scan['status']!='queued':return
        store = Store(self.settings.data_dir)
        ids = set()
        successful = 0
        try:
            query_language = scan.get('queryLanguage', 'en')
            jobs = plan_concept(scan['concept'], scan['countries'], scan_id, scan['createdAt']) if scan.get('concept') else plan_scan(scan['keyword'], scan['countries'], scan_id, scan['createdAt'], query_language)
            scan['status'] = 'running'
            self.save(scan)
            last_request = 0.0
            for job in jobs:
                import time
                self.settings.require_live()
                scan['active'] = {'country': job.country, 'source': job.source, 'query': job.query, 'channel': job.surface.split('_')[1]}
                self.save(scan)
                accepted = False
                candidates = [job, fallback_job(job)] if job.source == 'google_search' else [job]
                for candidate in candidates:
                    delay = max(0, self.settings.host_delay_seconds - (time.monotonic() - last_request))
                    if delay:time.sleep(delay)
                    self.settings.require_live()
                    store.schedule([candidate])
                    hold = store.claim_budget(candidate, allocation_for(candidate), self.settings.budget_bytes)
                    if hold is None:raise ValueError('Traffic budget or collection admission is unavailable.')
                    adapter = self.adapter_factory(self.settings, store) if self.adapter_factory else HTTPAdapter(self.settings, store, max_attempts=1)
                    result, items = adapter.fetch(candidate)
                    last_request = time.monotonic()
                    result['bytes'] = store.job_spent(candidate.id) - allocation_for(candidate)
                    store.save(candidate, result, items)
                    store.settle_budget(hold)
                    ids.add(candidate.id)
                    observation = store.db.execute('SELECT status FROM observations WHERE id=?', (candidate.id,)).fetchone()
                    accepted = observation['status'] == 'success'
                    scan['events'].append({'country': candidate.country, 'source': candidate.source,
                                           'channel': candidate.surface.split('_')[1], 'query': candidate.query,
                                           'profile': candidate.profile, 'language': candidate.language,
                                           'status': observation['status'], 'itemCount': len(items) if accepted else 0,
                                           'observedAt': result.get('observedAt', utcnow()),
                                           'error': result.get('error') if not accepted else None,
                                           'fallback': candidate.source == 'bing'})
                    scan['recording'] = build_recording(store, observation_ids=ids)
                    self.save(scan)
                    if accepted:break
                successful += accepted
                scan['completed'] += 1
                self.save(scan)
            scan['status'] = 'complete' if successful == len(jobs) else 'partial' if successful else 'failed'
        except Exception:
            # Library exceptions can contain proxy credentials. Never serialize them.
            scan['status'] = 'partial' if successful else 'failed'
            scan['error'] = 'Collection stopped. Available evidence is preserved; check local budget and source availability.'
        finally:
            scan.pop('active', None)
            scan['finishedAt'] = utcnow()
            self.save(scan)
            try:
                if scan['status'] in {'complete', 'partial'}:self.publish(scan)
            finally:store.close()
