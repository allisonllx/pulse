import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from http.server import ThreadingHTTPServer

import httpx
import pytest

from collector.jobs import plan
from collector.parsers import parse
from collector.publish import build_recording
from collector.scan_server import make_handler
from collector.scans import ScanManager, cache_key, fallback_job, normalize_keyword, plan_scan
from collector.settings import Settings
from collector.store import Store


def test_queries_are_literal_fixed_and_geography_is_explicit():
    jobs = plan_scan('Claude Code', ['SG','US'], 'abc', '2026-10-05T12:01:00Z')
    assert len(jobs) == 14
    searches = [j for j in jobs if j.source == 'google_search']
    assert {j.query for j in searches} == {'"Claude Code"', 'site:instagram.com "Claude Code"', 'site:tiktok.com "Claude Code"', 'site:x.com "Claude Code"', 'site:reddit.com "Claude Code"'}
    assert len({j.url for j in searches}) == 5
    assert all(j.settings['gl'] is None for j in searches)
    assert 'gl=SG' in next(j.url for j in jobs if j.surface == 'scan_news')
    injected = plan_scan('foo" site:evil.com', ['SG'], 'abc')[0]
    assert injected.query == '"foo  site:evil.com"'
    assert cache_key(' CLAUDE  Code ', ['SG','US']) == cache_key('claude code', ['US','SG'])
    with pytest.raises(ValueError):normalize_keyword(' ')
    with pytest.raises(ValueError):plan_scan('foo', ['ZZ'], 'abc')


def test_explicit_query_language_applies_across_sources_and_changes_cache_identity():
    from collector.scans import cache_key
    jobs = plan_scan('新作ゲーム', ['JP','US'], 'abc', query_language='ja')
    assert len(jobs) == 14
    assert {j.language for j in jobs} == {'ja'}
    assert {j.profile for j in jobs} == {'local'}
    news = next(j for j in jobs if j.source == 'google_news')
    video = next(j for j in jobs if j.source == 'youtube')
    assert 'hl=ja' in news.url and 'ceid=JP%3Aja' in news.url
    assert 'hl=ja' in video.url and 'gl=JP' in video.url
    assert cache_key('新作ゲーム',['JP','US']) != cache_key('新作ゲーム',['JP','US'],query_language='ja')
    with pytest.raises(ValueError):plan_scan('foo', ['JP'], 'abc', query_language='xx')


def test_social_domain_and_keyword_gate_preserves_search_rank_and_evidence():
    j = next(j for j in plan_scan('Claude Code', ['SG'], 'abc') if '_instagram_' in j.surface)
    html = b'''<div class="g"><a href="https://evilinstagram.com/p/a"><h3>Claude Code</h3></a></div>
    <div class="g"><a href="https://instagram.com/p/unrelated"><h3>Holiday recipes</h3></a></div>
    <div class="g"><a href="https://www.instagram.com/reel/b"><h3>Claude Code demo</h3></a><p>2 days ago - 12K likes</p></div>'''
    items = parse(html, j)
    assert len(items) == 1 and items[0]['rank'] == 3
    assert items[0]['source'] == 'google_search'
    assert items[0]['discovery'] == {'platform':'instagram','engine':'google_search','relevance':1.0,'freshnessLabel':'2 days ago','engagementLabels':['12K likes'],'basis':'indexed-search'}
    assert parse(html, fallback_job(j)) == []  # No Bing result containers.
    x = next(j for j in plan_scan('Claude Code', ['SG'], 'abc') if '_x_' in j.surface)
    assert parse(b'<a href="https://twitter.com/a/status/1"><h3>Claude Code release</h3></a>', x)


class FakeAdapter:
    calls = []
    def __init__(self, settings, store):self.store=store
    def fetch(self, job):
        self.calls.append(job)
        self.store.account(job.id, 'request', 100, 'success')
        if job.source == 'google_search':
            return {'status':'failed','observedCountry':job.country,'raw':b'blocked'}, []
        if job.source == 'bing':
            domain = {'web':'example.org','instagram':'instagram.com','tiktok':'tiktok.com','x':'x.com','reddit':'reddit.com'}[job.surface.split('_')[1]]
            raw = f'<li class="b_algo"><h2><a href="https://{domain}/post">Claude Code update</a></h2><p>3 days ago 120 views</p></li>'.encode()
        elif job.source == 'google_news':
            raw = b'<rss><channel><item><title>Claude Code update</title><link>https://news.example.org/a</link></item></channel></rss>'
        else:return {'status':'failed','observedCountry':job.country,'raw':b'blocked'}, []
        return {'status':'success','observedCountry':job.country,'raw':raw}, parse(raw, job)


def test_live_progress_fallback_shared_budget_cache_and_panel_isolation(tmp_path):
    FakeAdapter.calls = []
    settings = Settings(tmp_path/'evidence', 'u', 'secret', budget_bytes=500_000_000, host_delay_seconds=0)
    manager = ScanManager(settings, tmp_path/'public', FakeAdapter)
    scan = manager.create('Claude Code', ['SG'])
    manager.run(scan['id'])
    result = manager.read(scan['id'])
    assert result['status'] == 'partial' and result['completed'] == result['planned'] == 7
    assert len(result['events']) == 12
    assert any(e['fallback'] and e['status']=='success' for e in result['events'])
    assert result['recording']['snapshots'][0]['topics']
    assert manager.cached('claude code', ['SG'])['id'] == scan['id']
    assert manager.catalog()[0]['keyword'] == 'Claude Code'
    calls=len(FakeAdapter.calls)
    manager.run(scan['id'])
    assert len(FakeAdapter.calls)==calls and manager.read(scan['id'])==result
    with pytest.raises(ValueError,match='Immutable scan collision'):manager.publish({**result,'keyword':'changed'})
    assert 'secret' not in json.dumps(result)
    store = Store(settings.data_dir)
    assert store.spent == 1200
    assert not store.rows('health')
    assert not store.rows('topics')
    assert not store.rows('memberships')
    assert build_recording(store)['snapshots'] == []
    assert not any(a['kind']=='reservation' for a in store.rows('attempts'))
    store.close()


def test_admission_uses_existing_spend_and_preserves_reserve(tmp_path):
    settings = Settings(tmp_path, 'u', 'p', budget_bytes=100_000_000)
    manager = ScanManager(settings, tmp_path/'published', FakeAdapter)
    with pytest.raises(ValueError, match='remaining traffic budget'):manager.create('Claude Code', ['SG'])
    assert not list(manager.root.glob('*.json'))


def test_api_origin_gate_validation_and_cached_scan_without_credentials(tmp_path):
    manager = ScanManager(Settings(tmp_path), tmp_path/'published')
    manager.translate = lambda texts, language: [{'original': texts[0], 'english': 'Fixture English', 'language': language}]
    saved = {'id':'a'*24,'key':cache_key('Claude Code',['SG']),'keyword':'Claude Code','countries':['SG'],'createdAt':'2026-10-05T00:00:00Z','status':'complete','events':[],'recording':None}
    manager.save(saved)
    with ThreadPoolExecutor(max_workers=1) as executor:
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(manager, executor, threading.Lock(), str(tmp_path), port=0))
        port = server.server_address[1]
        # Handler knows the listener's assigned port for its Host check.
        server.RequestHandlerClass = make_handler(manager, executor, threading.Lock(), str(tmp_path), port=port)
        thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        base = f'http://127.0.0.1:{port}'
        try:
            assert httpx.post(base+'/api/scans', json={'keyword':'Claude Code','countries':['SG']}).json()['cached'] is True
            translated = httpx.post(base+'/api/translate', json={'language':'ja','texts':['新作ゲーム']})
            assert translated.status_code == 200 and translated.json()['translations'][0]['english'] == 'Fixture English'
            assert httpx.post(base+'/api/scans', json={'keyword':'foo'}, headers={'Origin':'https://evil.example'}).status_code == 403
            assert httpx.post(base+'/api/scans', content='foo').status_code == 415
            assert httpx.post(base+'/api/scans', json={'keyword':'foo','countries':['ZZ']}).status_code == 400
            assert httpx.post(base+'/api/scans', json={'conceptId':'not-a-concept'}).status_code == 400
            assert httpx.post(base+'/api/scans', json={'keyword':'foo','countries':['SG']}).status_code == 422
            assert httpx.get(base+'/api/scans/../../.env.local').status_code == 404
        finally:server.shutdown();server.server_close();thread.join()


def test_concept_plan_is_bounded_and_identical_across_markets():
    from collector.concepts import get_concept
    from collector.scans import plan_concept, discovery_evidence
    concept = get_concept('bubble-tea')
    jobs = plan_concept(concept, ['US','SG'], 'abc', '2026-10-05T00:00:00Z')
    assert len(jobs) == 26
    assert len({j.id for j in jobs}) == 26
    assert {j.query for j in jobs if j.country == 'US'} == {j.query for j in jobs if j.country == 'SG'}
    assert len([j for j in jobs if j.surface.split('_')[1] == 'instagram']) == 2
    assert cache_key('Bubble tea & boba',['US','SG'],'bubble-tea') != cache_key('Bubble tea & boba',['US','SG'])
    assert cache_key('ignored',['SG','US'],'bubble-tea') == cache_key('ignored',['US','SG'],'bubble-tea')
    chinese = next(j for j in jobs if j.query == '"珍珠奶茶"')
    assert discovery_evidence(chinese, '喜欢珍珠奶茶的朋友', 'https://example.org', '')['relevance'] == 1
    with pytest.raises(ValueError):get_concept('unknown')


def test_local_market_terms_are_targeted_and_separate_from_english_controls():
    from collector.concepts import get_concept
    from collector.scans import plan_concept
    concept = get_concept('bubble-tea')
    jobs = plan_concept(concept, ['US','JP','KR'], 'abc', '2026-10-05T00:00:00Z')
    local = [j for j in jobs if j.profile == 'local']
    assert {(j.country, j.query, j.language) for j in local} == {
        ('JP', '"タピオカ"', 'ja'), ('JP', '"バブルティー"', 'ja'), ('KR', '"버블티"', 'ko')}
    assert all(j.source in {'google_news','youtube'} for j in local)
    assert all('hl=ja' in j.url or 'hl=ko' in j.url for j in local)
    assert not any(j.country == 'US' and j.profile == 'local' for j in jobs)


def test_concept_snapshot_and_cache_keep_bundle_identity(tmp_path):
    settings = Settings(tmp_path/'evidence', 'u', 'p', budget_bytes=900_000_000, host_delay_seconds=0)
    manager = ScanManager(settings, tmp_path/'public', FakeAdapter)
    scan = manager.create('ignored', ['SG'], 'short-dramas')
    assert scan['keyword'] == 'Short dramas' and scan['planned'] == 13
    assert manager.active('ignored',['SG'],'short-dramas')['id'] == scan['id']
    assert not manager.active('Short dramas',['SG'])
    assert [a['term'] for a in scan['concept']['aliases']] == ['short drama','microdrama','vertical drama']
    manager.run(scan['id'])
    result = manager.read(scan['id'])
    # FakeAdapter returns irrelevant titles for every term; no fabricated evidence.
    assert result['completed'] == 13
    assert not manager.active('ignored',['SG'],'short-dramas')
    assert not manager.cached('Short dramas',['SG'])
