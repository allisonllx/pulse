from pathlib import Path
from collector.briefing.adapters.github import parse_releases
from collector.briefing.config import load_catalog


def test_release_uses_published_at_and_ignores_drafts():
    rows = [{'html_url': 'https://github.com/example/tool/releases/tag/v2', 'name': 'GPU serving v2', 'body': 'New software support', 'published_at': '2026-10-14T00:00:00Z', 'draft': False},
            {'draft': True}]
    signals, rejected = parse_releases(rows, {'id': 'example-tool'}, '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
    assert len(signals) == 1
    assert signals[0].sourceType == 'github'
    assert signals[0].publishedAt == '2026-10-14T00:00:00Z'
    assert signals[0].evidenceKind == 'announcement'
