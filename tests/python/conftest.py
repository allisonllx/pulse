import pytest
from collector.store import Store

@pytest.fixture
def store(tmp_path):
    value = Store(tmp_path/"evidence")
    yield value
    value.close()
