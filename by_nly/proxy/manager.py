"""Proxy Manager - free proxies, Tor, custom proxy files."""

import random
import asyncio
import aiohttp
from dataclasses import dataclass


@dataclass
class Proxy:
    url: str
    proxy_type: str = "http"  # http, https, socks5
    alive: bool = True
    fail_count: int = 0
    latency_ms: float = 0.0

    @property
    def proxy_url(self) -> str:
        return self.url


class ProxyManager:
    def __init__(self):
        self.proxies: list[Proxy] = []
        self._index: int = 0
        self._lock = asyncio.Lock()
        self._max_fails: int = 3

    def add_tor(self, host: str = "127.0.0.1", port: int = 9050) -> None:
        url = f"socks5://{host}:{port}"
        if not any(p.url == url for p in self.proxies):
            self.proxies.append(Proxy(url=url, proxy_type="socks5"))

    def add(self, url: str, proxy_type: str = "http") -> None:
        if not url.startswith("http"):
            url = f"{proxy_type}://{url}"
        if not any(p.url == url for p in self.proxies):
            self.proxies.append(Proxy(url=url, proxy_type=proxy_type))

    def load_file(self, filepath: str) -> int:
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    ptype = "http"
                    if line.startswith("socks5://"):
                        ptype = "socks5"
                    elif line.startswith("socks5h://"):
                        ptype = "socks5"
                    elif line.startswith("https://"):
                        ptype = "https"
                    elif "://" not in line:
                        line = f"http://{line}"
                    self.add(line, ptype)
                    count += 1
        except FileNotFoundError:
            pass
        return count

    async def fetch_free_proxies(self, limit: int = 50, health_check: bool = True) -> int:
        """Fetch free HTTP proxies from proxyscrape.com."""
        urls = [
            f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all&limit={limit}",
            f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=5000&country=all&ssl=all&anonymity=all&limit={limit}",
            f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all&ssl=all&anonymity=all&limit={limit}",
        ]
        ptype_map = {0: "http", 1: "https", 2: "socks5"}

        async with aiohttp.ClientSession() as session:
            for idx, url in enumerate(urls):
                try:
                    async with session.get(url, timeout=15) as resp:
                        text = await resp.text()
                        for line in text.strip().split("\n"):
                            line = line.strip()
                            if line and ":" in line:
                                self.add(line, ptype_map[idx])
                except Exception:
                    continue

        # Test proxies in background (only if requested)
        if health_check and self.proxies:
            asyncio.create_task(self._health_check(concurrent=10))

        return len(self.proxies)

    async def _health_check(self, concurrent: int = 10) -> int:
        sem = asyncio.Semaphore(concurrent)
        alive_count = 0

        async def test_one(proxy: Proxy):
            nonlocal alive_count
            async with sem:
                try:
                    timeout = aiohttp.ClientTimeout(total=5)
                    connector = None
                    if proxy.proxy_type == "socks5":
                        try:
                            from aiohttp_socks import ProxyConnector
                            connector = ProxyConnector.from_url(proxy.url)
                        except ImportError:
                            proxy.alive = False
                            return

                    async with aiohttp.ClientSession(
                        timeout=timeout, connector=connector
                    ) as session:
                        start = asyncio.get_event_loop().time()
                        async with session.get(
                            "https://httpbin.org/ip",
                            proxy=proxy.url if proxy.proxy_type != "socks5" else None,
                            timeout=15,
                        ) as resp:
                            if resp.status == 200:
                                proxy.alive = True
                                proxy.latency_ms = (
                                    asyncio.get_event_loop().time() - start
                                ) * 1000
                                alive_count += 1
                            else:
                                proxy.alive = False
                except Exception:
                    proxy.alive = False

        if self.proxies:
            tasks = [test_one(p) for p in self.proxies]
            await asyncio.gather(*tasks, return_exceptions=True)

        self.proxies = [p for p in self.proxies if p.alive]
        return alive_count

    async def get_next(self) -> Proxy | None:
        async with self._lock:
            alive = [p for p in self.proxies if p.alive]
            if not alive:
                return None
            self._index = (self._index + 1) % len(alive)
            return alive[self._index]

    def get_random(self) -> Proxy | None:
        alive = [p for p in self.proxies if p.alive]
        return random.choice(alive) if alive else None

    def mark_dead(self, proxy: Proxy) -> None:
        proxy.fail_count += 1
        if proxy.fail_count >= self._max_fails:
            proxy.alive = False

    def mark_alive(self, proxy: Proxy, latency_ms: float = 0.0) -> None:
        proxy.fail_count = 0
        proxy.alive = True
        proxy.latency_ms = latency_ms

    @property
    def alive_count(self) -> int:
        return sum(1 for p in self.proxies if p.alive)

    @property
    def total_count(self) -> int:
        return len(self.proxies)
