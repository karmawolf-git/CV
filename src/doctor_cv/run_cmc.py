"""가톨릭중앙의료원(CMC) 계열 어댑터 실행기 (JSON API, LLM 불필요).

사용 예:
    python -m doctor_cv.run_cmc                          # HOSPITALS 전체
    python -m doctor_cv.run_cmc --only 서울성모           # 이름 부분일치 한 곳
    python -m doctor_cv.run_cmc --max-depts 1 --max-per-dept 2
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .adapters import cmc
from .fetcher import Fetcher
from .store import dedup, save_doctors


def crawl_cmc_hospital(fetch, *, hospital: str, base_url: str, now: str, max_depts=None, max_per_dept=None, depts=None):
    doctors = []
    errors = []
    try:
        details = cmc.iter_doctor_details(fetch, base_url, max_depts=max_depts, max_per_dept=max_per_dept, depts=depts)
        for detail in details:
            doctors.append(cmc.to_doctor(detail, hospital=hospital, base_url=base_url, crawled_at=now))
    except Exception as exc:  # noqa: BLE001 - 병원 단위 격리
        errors.append((base_url, str(exc)))
        print(f"[ERROR] {hospital} 실패: {exc}")
    return doctors, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="CMC 계열 의료진 크롤러 (JSON API)")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--only", default=None, help="병원명 부분일치로 한 곳만")
    parser.add_argument("--max-depts", type=int, default=None)
    parser.add_argument("--max-per-dept", type=int, default=None)
    args = parser.parse_args()

    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()
    targets = [h for h in cmc.HOSPITALS if not args.only or args.only in h["name"]]

    all_docs = []
    summary = {}
    for h in targets:
        docs, errs = crawl_cmc_hospital(
            lambda url: fetcher.fetch(url),
            hospital=h["name"],
            base_url=h["base_url"],
            now=now,
            max_depts=args.max_depts,
            max_per_dept=args.max_per_dept,
        )
        all_docs.extend(docs)
        summary[h["name"]] = {"doctors": len(docs), "error": errs[0][1] if errs else None}

    result = dedup(all_docs)
    save_doctors(result, args.out)
    print("=== CMC 계열 수집 요약 ===")
    for name, info in summary.items():
        print(f"{name}: 의사 {info['doctors']}명, 오류={info['error']}")
    print(f"총 {len(result)}명 -> {args.out}")


if __name__ == "__main__":
    main()
