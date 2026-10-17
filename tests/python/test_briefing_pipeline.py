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
