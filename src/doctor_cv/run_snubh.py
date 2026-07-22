"""분당서울대학교병원(SNUBH) 어댑터 실행기.

사용 예 (소량 테스트):
    python -m doctor_cv.run_snubh --max-depts 1 --max-per-dept 2
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .adapters import snubh
from .dotenv import load_env_file
from .extractor import extract_doctor
from .fetcher import Fetcher
from .store import dedup, save_doctors


def crawl_snubh(fetch, extract, *, now: str, max_depts=None, max_per_dept=None, depts=None):
    """상세 페이지가 크므로 프로필 블록만 잘라내고, 목록에서 얻은 이름을 주입해 추출한다.

    (상세 경력 블록에는 이름이 없어 목록 카드의 이름을 앞에 덧붙인다.)
    """
    doctors = []
    errors = []
    for _cd, url, name in snubh.iter_detail_urls(
        fetch, max_depts=max_depts, max_per_dept=max_per_dept, depts=depts
    ):
        try:
            trimmed = snubh.trim_detail(fetch(url))
            if name:
                trimmed = f"<p>의료진 이름: {name}</p>\n{trimmed}"
            doctors.append(
                extract(
                    trimmed,
                    hospital=snubh.HOSPITAL_NAME,
                    hospital_url=snubh.BASE,
                    source_url=url,
                    crawled_at=now,
                )
            )
        except Exception as exc:  # noqa: BLE001 - 의사 단위 격리
            errors.append((url, str(exc)))
            print(f"[WARN] 상세 실패 {url}: {exc}")
    return doctors, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="분당서울대 의료진 크롤러 (어댑터)")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-depts", type=int, default=None, help="부서 수 제한")
    parser.add_argument("--max-per-dept", type=int, default=None, help="부서당 의사 수 제한")
    args = parser.parse_args()

    load_env_file(".env")
    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()

    doctors, errors = crawl_snubh(
        lambda url: fetcher.fetch(url),
        extract_doctor,
        now=now,
        max_depts=args.max_depts,
        max_per_dept=args.max_per_dept,
    )
    result = dedup(doctors)
    save_doctors(result, args.out)
    print("=== 분당서울대 수집 요약 ===")
    print(f"수집 의사: {len(result)}명, 실패: {len(errors)}건 -> {args.out}")


if __name__ == "__main__":
    main()
