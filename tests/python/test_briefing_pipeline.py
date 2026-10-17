from collector.briefing.pipeline import collect_sources
from collector.briefing.store import BriefingStore
from pathlib import Path
from test_briefing_sources import RSS


def test_fixture_collection_survives_unavailable_x(tmp_path):
    fixtures = tmp_path / 'fixtures'; fixtures.mkdir()
    (fixtures / 'example.xml').write_bytes(RSS)
    sources = [{'id': 'example', 'type': 'rss', 'enabled': True, 'url': 'https://example.com/feed'},
               {'id': 'x', 'type': 'x', 'enabled': False}]
    with BriefingStore(tmp_path / 'store') as store:
        report = collect_sources(sources, store, '2026-10-18T00:00:00Z', fixture_dir=fixtures)
        assert [row['status'] for row in report] == ['partial', 'disabled']
        assert report[0]['itemCount'] == 1


def test_dry_run_creates_no_observations(tmp_path):
    with BriefingStore(tmp_path) as store:
        report = collect_sources([{'id': 'news', 'enabled': True, 'type': 'rss'}], store,
                                 '2026-10-18T00:00:00Z', dry_run=True)
        assert report[0]['status'] == 'planned'
        assert store.runs() == []


def test_missing_browser_authorization_is_a_setup_gap(tmp_path, monkeypatch):
    monkeypatch.delenv('PULSE_BROWSER_SOURCES', raising=False)
    with BriefingStore(tmp_path) as store:
        report = collect_sources([{'id': 'x', 'enabled': True, 'type': 'x', 'queries': ['AI']}], store, '2026-10-18T00:00:00Z')
        assert report[0]['status'] == 'unavailable'
        assert report[0]['errorCode'] == 'browser_consent_required'
        assert 'authorize a Chrome session' in report[0]['reason']


def test_youtube_fixture_reaches_public_signal_contract(tmp_path):
    import json
    from datetime import datetime
    fixtures = tmp_path / 'fixtures'; fixtures.mkdir()
    (fixtures / 'youtube.json').write_text(json.dumps([{'id': 'abcdefghijk', 'title': 'Claude Code tutorial', 'timestamp': 1791936000}]))
    with BriefingStore(tmp_path / 'store') as store:
        report = collect_sources([{'id': 'youtube', 'enabled': True, 'type': 'youtube', 'queries': ['AI']}], store, '2026-10-18T00:00:00Z', fixture_dir=fixtures)
        assert report[0]['status'] == 'success'
        signals = store.signals_between(datetime.fromisoformat('2026-10-12T00:00:00Z'), datetime.fromisoformat('2026-10-19T00:00:00Z'))
        assert signals[0].sourceType == 'youtube'
        assert signals[0].lensCandidates == ['all', 'tech']
