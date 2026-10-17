import ipaddress
import socket
from urllib.parse import urljoin, urlsplit
import httpx
from .models import public_url


class FetchError(ValueError):
    pass


class Transport:
    """Bounded requests to an explicitly configured set of public hosts."""
    def __init__(self, hosts, *, client=None, resolve=True, max_bytes=2_000_000, max_requests=20):
        self.hosts = set(hosts)
        self.client = client or httpx.Client(timeout=15, follow_redirects=False, trust_env=False,
                                             headers={'User-Agent': 'PulseWeekly/1.0 (+public research feeds)'})
        self.resolve, self.max_bytes, self.max_requests = resolve, max_bytes, max_requests
        self.requests = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.client.close()

    def _check(self, url):
        public_url(url)
        parts = urlsplit(url)
        if parts.hostname not in self.hosts or parts.port not in (None, 80, 443):
            raise FetchError('disallowed_host')
        if self.resolve:
            try:
                addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
                if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                    raise FetchError('nonpublic_address')
            except socket.gaierror:
                raise FetchError('dns_error') from None

    def get(self, url, *, params=None, headers=None):
        retries, redirects = 0, 0
        while True:
            self._check(url)
            if self.requests >= self.max_requests:
                raise FetchError('request_limit')
            self.requests += 1
            try:
                with self.client.stream('GET', url, params=params, headers=headers, follow_redirects=False) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirects >= 3 or not response.headers.get('location'):
                            raise FetchError('redirect_limit')
                        url = urljoin(str(response.url), response.headers['location'])
                        params = None
                        redirects += 1
                        continue
                    if response.status_code in {502, 503, 504} and retries == 0:
                        retries += 1
                        continue
                    if response.status_code >= 400:
                        raise FetchError('http_' + str(response.status_code))
                    payload = bytearray()
                    for chunk in response.iter_bytes(chunk_size=16384):
                        payload.extend(chunk)
                        if len(payload) > self.max_bytes:
                            raise FetchError('response_too_large')
                    headers = {k: v for k, v in response.headers.items() if k not in {'content-encoding', 'content-length', 'transfer-encoding'}}
                    return httpx.Response(response.status_code, headers=headers, content=bytes(payload), request=response.request)
            except httpx.TransportError:
                if retries:
                    raise FetchError('transport_error') from None
                retries += 1
