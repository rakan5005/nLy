"""HTTP client adapter using curl_cffi to bypass Cloudflare."""

from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession as CurlAsyncSession


class URLAdapter:
    """Adapts curl_cffi URL string to aiohttp URL-like interface."""

    def __init__(self, url_str: str):
        parsed = urlparse(str(url_str))
        self.path = parsed.path
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc
        self._raw = str(url_str)

    def __str__(self) -> str:
        return self._raw

    def __contains__(self, item: str) -> bool:
        return item in self._raw


class ResponseAdapter:
    """Adapts curl_cffi response to aiohttp-like interface."""

    def __init__(self, resp):
        self._resp = resp
        self._url = None

    @property
    def status(self) -> int:
        return self._resp.status_code

    async def text(self) -> str:
        return self._resp.text

    async def json(self) -> dict:
        return self._resp.json()

    @property
    def url(self) -> URLAdapter:
        if self._url is None:
            self._url = URLAdapter(str(self._resp.url))
        return self._url

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _RequestContext:
    """Wraps a curl_cffi request as an async context manager (like aiohttp)."""

    def __init__(self, coro):
        self._coro = coro
        self._resp = None

    async def __aenter__(self):
        resp = await self._coro
        self._resp = ResponseAdapter(resp)
        return self._resp

    async def __aexit__(self, *args):
        pass


class SessionAdapter:
    """Adapts curl_cffi session to aiohttp-like interface.

    Supports: `async with session.get(url) as resp:` pattern.
    Proxy is injected at session level via curl_cffi's proxies dict.
    """

    def __init__(self, impersonate: str = "chrome131", proxy: str | None = None):
        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}
        self._session = CurlAsyncSession(impersonate=impersonate, proxies=proxies)
        self._proxy = proxy

    def get(self, url, **kwargs):
        return _RequestContext(self._session.get(url, **kwargs))

    def post(self, url, **kwargs):
        return _RequestContext(self._session.post(url, **kwargs))

    async def close(self):
        await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


def create_session(proxy: str | None = None, impersonate: str = "chrome131") -> SessionAdapter:
    """Create a new curl_cffi session with browser impersonation."""
    return SessionAdapter(impersonate=impersonate, proxy=proxy)
