"""어댑터 공통 실행 헬퍼: 상세 URL들을 순회하며 추출한다(의사 단위 오류 격리)."""
from __future__ import annotations

from .models import Doctor


def crawl_details(detail_urls, fetch, extract, *, hospital: str, hospital_url: str, now: str):
    """(detail_urls) 각각을 fetch→extract 한다.

    반환: (doctors, errors) — errors는 (url, message) 리스트.
    한 의사가 실패해도 나머지는 계속 진행한다.
    """
    doctors: list[Doctor] = []
    errors: list[tuple[str, str]] = []
    for url in detail_urls:
        try:
            html = fetch(url)
            doctors.append(
                extract(
                    html,
                    hospital=hospital,
                    hospital_url=hospital_url,
                    source_url=url,
                    crawled_at=now,
                )
            )
        except Exception as exc:  # noqa: BLE001 - 의사 단위 격리
            errors.append((url, str(exc)))
            print(f"[WARN] 상세 실패 {url}: {exc}")
    return doctors, errors
