"""서울아산병원(AMC) 어댑터 실행기.

목록/상세 엔드포인트를 순회하며 상세 HTML을 LLM으로 추출해 JSON으로 저장한다.
LLM 추출에는 ANTHROPIC_API_KEY 환경변수가 필요하다.

사용 예 (소량 테스트):
    python -m doctor_cv.run_amc --max-depts 1 --max-per-dept 2
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .adapters import amc
from .extractor import extract_doctor
from .fetcher import Fetcher
from .models import Doctor
from .store import dedup, save_doctors


def crawl_amc(fetch, extract, *, now: str, max_depts=None, max_per_dept=None):
    """AMC 상세 페이지를 순회·추출한다. 의사 단위로 오류를 격리한다.

    반환: (doctors, errors) — errors는 (url, message) 리스트.
    """
    doctors: list[Doctor] = []
    errors: list[tuple[str, str]] = []
    for _code, url in amc.iter_detail_urls(fetch, max_depts=max_depts, max_per_dept=max_per_dept):
        try:
            html = fetch(url)
            doctors.append(
                extract(
                    html,
                    hospital=amc.HOSPITAL_NAME,
                    hospital_url=amc.BASE,
                    source_url=url,
                    crawled_at=now,
                )
            )
        except Exception as exc:  # noqa: BLE001 - 의사 단위 격리
            errors.append((url, str(exc)))
            print(f"[WARN] 상세 실패 {url}: {exc}")
    return doctors, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="서울아산 의료진 크롤러 (어댑터)")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-depts", type=int, default=None, help="진료과 수 제한")
    parser.add_argument("--max-per-dept", type=int, default=None, help="진료과당 의사 수 제한")
    args = parser.parse_args()

    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()

    doctors, errors = crawl_amc(
        lambda url: fetcher.fetch(url),
        extract_doctor,
        now=now,
        max_depts=args.max_depts,
        max_per_dept=args.max_per_dept,
    )
    result = dedup(doctors)
    save_doctors(result, args.out)
    print("=== 서울아산 수집 요약 ===")
    print(f"수집 의사: {len(result)}명, 실패: {len(errors)}건 -> {args.out}")


if __name__ == "__main__":
    main()
