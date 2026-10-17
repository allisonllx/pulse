from pathlib import Path
from collector.briefing.adapters.github import parse_releases
from collector.briefing.config import load_catalog
import pytest


def test_release_uses_published_at_and_ignores_drafts():
    rows = [{'html_url': 'https://github.com/example/tool/releases/tag/v2', 'name': 'GPU serving v2', 'body': 'New software support', 'published_at': '2026-10-14T00:00:00Z', 'draft': False},
            {'draft': True}]
    signals, rejected = parse_releases(rows, {'id': 'example-tool'}, '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
    assert len(signals) == 1
    assert signals[0].sourceType == 'github'
    assert signals[0].publishedAt == '2026-10-14T00:00:00Z'
    assert signals[0].evidenceKind == 'announcement'


def test_youtube_metadata_is_dated_and_metrics_remain_optional():
    from collector.briefing.adapters.youtube import parse_videos
    rows = [{'id': 'abcdefghijk', 'title': 'DeepSeek model serving', 'timestamp': 1791936000,
             'uploader': 'Example', 'view_count': 321, 'description': 'A public tutorial.'},
            {'id': 'lmnopqrstuv', 'title': 'Undated', 'upload_date': '20261014'}]
    signals, rejected = parse_videos(rows, {'id': 'youtube'}, '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
    assert rejected == 1
    assert signals[0].canonicalUrl == 'https://www.youtube.com/watch?v=abcdefghijk'
    assert signals[0].sourceType == 'youtube'
    assert signals[0].evidenceKind == 'discussion'
    assert signals[0].metrics == {'views': 321}
    assert signals[0].lensCandidates == ['all', 'tech']


def test_youtube_command_does_not_read_browser_credentials():
    from collector.briefing.adapters.youtube import fetch_youtube
    import json
    commands = []
    def runner(command):
        commands.append(command)
        return json.dumps({'id': 'abcdefghijk', 'title': 'Claude tutorial', 'timestamp': 1791936000}).encode()
    signals, rejected = fetch_youtube({'id': 'youtube', 'queries': ['AI infrastructure'], 'limit': 2},
                                      '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')), runner=runner)
    assert len(signals) == 1
    assert '--ignore-config' in commands[0]
    assert '--no-plugin-dirs' in commands[0]
    assert '--skip-download' in commands[0]
    assert 'sp=CAMSAggD' in commands[0][-1]
    assert not any('cookies' in arg for arg in commands[0])


def test_external_command_is_bounded_and_redacts_provider_errors():
    import sys
    from collector.briefing.external import run_json_command, BackendError
    with pytest.raises(BackendError, match='output_limit'):
        run_json_command([sys.executable, '-c', 'print("x"*10000)'], max_bytes=100)
    with pytest.raises(BackendError, match='backend_failed') as error:
        run_json_command([sys.executable, '-c', 'import sys;print("secret_token", file=sys.stderr);sys.exit(1)'])
    assert 'secret_token' not in str(error.value)


def test_opencli_discussions_preserve_platform_and_topic():
    from collector.briefing.adapters.browser_social import parse_posts
    catalog = load_catalog(Path('config/briefing-lenses.json'))
    rows = [{'id': '123', 'author': 'example', 'text': 'DeepSeek GPU serving guide',
             'created_at': 'Wed Oct 14 12:00:00 +0000 2026', 'likes': 12, 'views': '300', 'url': 'https://x.com/i/status/123'}]
    signals, rejected = parse_posts(rows, {'id': 'x', 'type': 'x'}, '2026-10-18T00:00:00Z', catalog)
    assert rejected == 0
    assert signals[0].sourceType == 'x'
    assert signals[0].lensCandidates == ['all', 'tech']
    assert signals[0].metrics == {'likes': 12, 'views': 300}
    rows = [{'id': 'abc', 'title': 'Claude Code workflow', 'created_utc': 1791936000, 'score': 5, 'comments': 2, 'url': 'https://www.reddit.com/r/LocalLLaMA/comments/abc/example/'}]
    signals, _ = parse_posts(rows, {'id': 'reddit', 'type': 'reddit'}, '2026-10-18T00:00:00Z', catalog)
    assert signals[0].metrics == {'score': 5, 'comments': 2}


def test_browser_backend_never_runs_without_explicit_opt_in(monkeypatch):
    from collector.briefing.adapters.browser_social import fetch_browser_posts
    from collector.briefing.external import BackendError
    monkeypatch.delenv('PULSE_BROWSER_SOURCES', raising=False)
    with pytest.raises(BackendError, match='browser_consent_required'):
        fetch_browser_posts({'id': 'x', 'type': 'x', 'queries': ['AI']}, '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
