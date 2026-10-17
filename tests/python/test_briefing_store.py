from datetime import datetime
from collector.briefing.models import validate_signal
from collector.briefing.store import BriefingStore
from collector.briefing.normalize import canonical_url
from test_briefing_contract import sample


def test_history_survives_refetch_and_excludes_other_weeks(tmp_path):
    with BriefingStore(tmp_path) as store:
        data = sample(); data['metrics'] = {'views': 10}
        store.save_fetch('first', 'example', 'success', [validate_signal(data)])
        store.save_fetch('first', 'example', 'success', [validate_signal(data)])
        data['metrics'] = {'views': 20}; data['collectedAt'] = '2026-10-18T12:00:00Z'
        store.save_fetch('second', 'example', 'success', [validate_signal(data)])
        store.save_fetch('failed', 'x', 'failed', [], error='rate_limited')
        signals = store.signals_between(datetime.fromisoformat('2026-10-12T00:00:00Z'), datetime.fromisoformat('2026-10-19T00:00:00Z'))
        assert len(signals) == 1
        assert [x['metrics']['views'] for x in store.metric_history('one')] == [10, 20]
        assert store.runs()[-1]['errorCode'] == 'rate_limited'
    assert not (tmp_path / 'worldview.sqlite').exists()


def test_canonical_preserves_content_query():
    assert canonical_url('https://EXAMPLE.com/story?id=7&utm_source=test#top') == 'https://example.com/story?id=7'
