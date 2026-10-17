from datetime import datetime
from collector.briefing.worker import due_actions, exclusive_run
import pytest


def test_singapore_schedule_is_independent_of_host_timezone():
    assert due_actions(datetime.fromisoformat('2026-10-18T22:30:00Z'), set()) == ['collect']
    assert due_actions(datetime.fromisoformat('2026-10-19T00:30:00Z'), set()) == ['collect', 'publish']
    assert due_actions(datetime.fromisoformat('2026-10-19T00:30:00Z'), {'collect:2026-10-19', 'publish:2026-10-19'}) == []


def test_overlapping_workers_cannot_claim_same_directory(tmp_path):
    with exclusive_run(tmp_path):
        with pytest.raises(ValueError, match='already running'):
            with exclusive_run(tmp_path):
                pass
