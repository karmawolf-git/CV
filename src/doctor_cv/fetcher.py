from __future__ import annotations

import hashlib
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_UA = "DoctorCV-Research-Crawler/0.1 (+public medical staff info; research use)"


def _make_ssl_context():
    """OS 신뢰저장소(truststore)로 SSL 컨텍스트를 만든다.

    이 환경은 회사망 SSL 검사/중간 인증서 문제로 certifi 기본 번들로는 일부
    .or.kr 사이트 검증이 실패한다. Chrome처럼 OS 저장소를 쓰면 해결된다.
    truststore가 없으면 httpx 기본(certifi) 검증으로 폴백한다.
    """
    try:
        import ssl

        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:  # noqa: BLE001
        return True


_SSL_CONTEXT = _make_ssl_context()


def looks_unrendered(html: str) -> bool:
    """본문이 비어 있거나 지나치게 짧으면 JS 렌더링이 필요하다고 판단.

    <body>가 아예 없으면 HTML 문서가 아니라 XML/JSON 같은 ajax 응답이므로,
    JS 렌더링 대상이 아니라고 보고 False를 반환한다(불필요한 Playwright 폴백 방지)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body is None:
        return False
    return len(body.get_text(strip=True)) < 100


class Fetcher:
    def __init__(self, cache_dir: str | Path, user_agent: str = DEFAULT_UA, min_delay: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent
        self.min_delay = min_delay
        self._robots: dict[str, RobotFileParser] = {}
        self._last_request = 0.0

    def cache_path(self, url: str) -> Path:
        host = urlparse(url).netloc
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / host / f"{digest}.html"

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._robots:
            rp = RobotFileParser()
            rp.set_url(urljoin(root, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                # robots.txt 접근 불가 시 공개 페이지 대상이므로 허용으로 처리.
                self._robots[root] = None  # type: ignore[assignment]
                return True
            self._robots[root] = rp
        rp = self._robots[root]
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request = time.monotonic()

    def _default_static(self, url: str) -> str:
        self._throttle()
        resp = httpx.get(
            url,
            headers={"User-Agent": self.user_agent},
            timeout=20.0,
            follow_redirects=True,
            verify=_SSL_CONTEXT,
        )
        resp.raise_for_status()
        return resp.text

    def _default_dynamic(self, url: str) -> str:
        from playwright.sync_api import sync_playwright

        self._throttle()
        with sync_playwright() as p:
            # 시스템에 설치된 Google Chrome을 사용한다(다운로드 Chromium 불필요).
            browser = p.chromium.launch(channel="chrome")
            page = browser.new_page(user_agent=self.user_agent)
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
        return html

    def fetch(self, url: str, static_getter=None, dynamic_getter=None, check_robots: bool = True) -> str:
        cache = self.cache_path(url)
        if cache.exists():
            return cache.read_text(encoding="utf-8")

        if check_robots and not self.allowed(url):
            raise PermissionError(f"robots.txt disallows: {url}")

        static_getter = static_getter or self._default_static
        html = static_getter(url)

        if looks_unrendered(html):
            dyn = dynamic_getter if dynamic_getter is not None else self._default_dynamic
            if dyn is not None:
                html = dyn(url)

        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(html, encoding="utf-8")
        return html
