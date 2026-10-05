import json
from pathlib import Path
import pytest
from collector.topics import token_match
CASES = json.loads((Path(__file__).parent/"topic-review-corpus.json").read_text())
@pytest.mark.parametrize("case",CASES,ids=[str(i+1) for i in range(len(CASES))])
def test_reviewed_topic_match(case):
    assert token_match(case["a"],case["b"]) == case["match"]
