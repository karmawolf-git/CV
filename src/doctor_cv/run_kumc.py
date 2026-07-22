"""고려대학교의료원(KUMC) 어댑터 실행기 (안암·구로·안산). LLM 추출.

사용 예:
    python -m doctor_cv.run_kumc --only 구로 --max-doctors 3
    python -m doctor_cv.run_kumc --max-doctors 5
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .adapters import kumc
from .dotenv import load_env_file
from .fetcher import Fetcher
from .store import dedup, save_doctors


def crawl_kumc_hospital(fetch, *, hospital, base_url, inst_no, now, max_doctors=None, depts=None, max_per_dept=None):
    """KUMC 병원 1곳을 JSON API로 수집한다(LLM 불필요). 의사 단위 오류 격리."""
    doctors, errors = [], []
    for dr_no in kumc.iter_doctor_ids(
        fetch, base_url, inst_no, max_doctors=max_doctors, depts=depts, max_per_dept=max_per_dept
    ):
        try:
            doctors.append(kumc.build_doctor(fetch, base_url, dr_no, hospital=hospital, crawled_at=now))
        except Exception as exc:  # noqa: BLE001 - 의사 단위 격리
            errors.append((kumc.profile_url(base_url, dr_no), str(exc)))
            print(f"[WARN] 상세 실패 {dr_no}: {exc}")
    return doctors, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="고려대의료원 의료진 크롤러 (어댑터)")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--only", default=None, help="병원명 부분일치로 한 곳만")
    parser.add_argument("--max-doctors", type=int, default=None, help="병원당 의사 수 제한")
    args = parser.parse_args()

    load_env_file(".env")
    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()
    targets = [h for h in kumc.HOSPITALS if not args.only or args.only in h["name"]]

    all_docs, summary = [], {}
    for h in targets:
        docs, errs = crawl_kumc_hospital(
            lambda url: fetcher.fetch(url),
            hospital=h["name"], base_url=h["base_url"], inst_no=h["inst_no"],
            now=now, max_doctors=args.max_doctors,
        )
        all_docs.extend(docs)
        summary[h["name"]] = {"doctors": len(docs), "error": errs[0][1] if errs else None}

    result = dedup(all_docs)
    save_doctors(result, args.out)
    print("=== 고려대의료원 수집 요약 ===")
    for name, info in summary.items():
        print(f"{name}: 의사 {info['doctors']}명, 오류={info['error']}")
    print(f"총 {len(result)}명 -> {args.out}")


if __name__ == "__main__":
    main()
