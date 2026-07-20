"""삼성서울병원(SMC) 어댑터 실행기.

사용 예 (소량 테스트):
    python -m doctor_cv.run_smc --max-depts 1 --max-per-dept 2
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .adapters import smc
from .crawl import crawl_details
from .dotenv import load_env_file
from .extractor import extract_doctor
from .fetcher import Fetcher
from .store import dedup, save_doctors


def crawl_smc(fetch, extract, *, now: str, max_depts=None, max_per_dept=None):
    urls = (
        u
        for _code, u in smc.iter_profile_urls(
            fetch, max_depts=max_depts, max_per_dept=max_per_dept
        )
    )
    return crawl_details(
        urls, fetch, extract, hospital=smc.HOSPITAL_NAME, hospital_url=smc.BASE, now=now
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="삼성서울병원 의료진 크롤러 (어댑터)")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-depts", type=int, default=None, help="진료과 수 제한")
    parser.add_argument("--max-per-dept", type=int, default=None, help="진료과당 의사 수 제한")
    args = parser.parse_args()

    load_env_file(".env")
    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()

    doctors, errors = crawl_smc(
        lambda url: fetcher.fetch(url),
        extract_doctor,
        now=now,
        max_depts=args.max_depts,
        max_per_dept=args.max_per_dept,
    )
    result = dedup(doctors)
    save_doctors(result, args.out)
    print("=== 삼성서울병원 수집 요약 ===")
    print(f"수집 의사: {len(result)}명, 실패: {len(errors)}건 -> {args.out}")


if __name__ == "__main__":
    main()
