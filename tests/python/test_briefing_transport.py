import httpx
import gzip
import pytest
from collector.briefing.transport import Transport, FetchError


def test_compressed_response_is_decoded_exactly_once():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=gzip.compress(b'<rss/>'), headers={'content-encoding': 'gzip'})))
    with Transport({'example.com'}, client=client, resolve=False) as transport:
        assert transport.get('https://example.com').content == b'<rss/>'


def test_block_redirect_before_requesting_private_host():
    seen = []
    def handle(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={'Location': 'http://127.0.0.1/private'})
    with Transport({'example.com'}, client=httpx.Client(transport=httpx.MockTransport(handle)), resolve=False) as transport:
        with pytest.raises(FetchError, match='disallowed_host'):
            transport.get('https://example.com')
    assert seen == ['https://example.com']


def test_rate_limit_does_not_retry_and_size_is_bounded():
    calls = []
    def handle(request):
        calls.append(1)
        return httpx.Response(429)
    with Transport({'example.com'}, client=httpx.Client(transport=httpx.MockTransport(handle)), resolve=False) as transport:
        with pytest.raises(FetchError, match='http_429'):
            transport.get('https://example.com')
    assert len(calls) == 1
    with Transport({'example.com'}, client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b'12345'))), resolve=False, max_bytes=4) as transport:
        with pytest.raises(FetchError, match='response_too_large'):
            transport.get('https://example.com')
