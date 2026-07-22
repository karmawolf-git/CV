from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

PROFILE_HINTS = ("의료진", "교수", "전문의", "doctor", "staff", "profile", "physician")


def find_profile_urls(html: str, base_url: str) -> list[str]:
    """의료진 목록 HTML에서 개별 프로필 링크를 휴리스틱으로 추출한다."""
    soup = BeautifulSoup(html, "html.parser")
    result: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        haystack = f"{href} {text}".lower()
        if not any(hint.lower() in haystack for hint in PROFILE_HINTS):
            continue
        absolute = urljoin(base_url + "/", href)
        if absolute not in seen:
            seen.add(absolute)
            result.append(absolute)
    return result
