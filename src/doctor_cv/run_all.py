"""구현된 모든 어댑터를 한 번에 돌려 통합 data/doctors.json을 만든다.

- CMC 계열(서울성모·부천·은평·성빈센트): JSON API, LLM 불필요.
- amc·smc·snubh: 서버렌더 HTML → Claude 추출(ANTHROPIC_API_KEY 필요, .env에서 로드).

LLM 비용을 감안해 기본은 병원별 소량 샘플이다. --max-depts/--max-per-dept로 조절,
--no-llm 으로 CMC(무료)만 돌릴 수 있다.

사용 예:
    python -m doctor_cv.run_all --max-depts 2 --max-per-dept 3
    python -m doctor_cv.run_all --no-llm            # CMC만
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .adapters import cmc, kumc
from .dotenv import load_env_file
from .extractor import extract_doctor
from .fetcher import Fetcher
from .run_amc import crawl_amc
from .run_cmc import crawl_cmc_hospital
from .run_kumc import crawl_kumc_hospital
from .run_smc import crawl_smc
from .run_snubh import crawl_snubh
from .store import dedup, save_doctors

# LLM 기반 어댑터(라벨, crawl 함수). 시그니처: fn(fetch, extract, *, now, max_depts, max_per_dept).
LLM_JOBS = [
    ("서울아산병원", crawl_amc),
    ("삼성서울병원", crawl_smc),
    ("분당서울대학교병원", crawl_snubh),
]


def run_all(fetch, *, now, extract, depts=None, llm_per_dept=5, json_per_dept=15,
            max_depts=None, include_llm=True):
    """모든 어댑터를 돌려 (all_doctors, summary)를 반환한다. 병원 단위로 오류를 격리한다.

    depts(진료과명 부분일치 리스트)로 과를 선별한다. JSON 병원(cmc/kumc)은 무료라
    json_per_dept, LLM 병원(amc/smc/snubh)은 토큰 절약 위해 llm_per_dept 상한을 쓴다.
    """
    all_docs = []
    summary = {}

    for h in cmc.HOSPITALS:  # CMC 계열 (JSON, 무료)
        try:
            docs, errs = crawl_cmc_hospital(
                fetch, hospital=h["name"], base_url=h["base_url"], now=now,
                max_depts=max_depts, max_per_dept=json_per_dept, depts=depts,
            )
        except Exception as exc:  # noqa: BLE001
            docs, errs = [], [(h["base_url"], str(exc))]
        all_docs.extend(docs)
        summary[h["name"]] = {"doctors": len(docs), "error": errs[0][1] if errs else None}

    for h in kumc.HOSPITALS:  # 고려대의료원 (JSON, 무료)
        try:
            docs, errs = crawl_kumc_hospital(
                fetch, hospital=h["name"], base_url=h["base_url"], inst_no=h["inst_no"],
                now=now, depts=depts, max_per_dept=json_per_dept,
                max_doctors=(None if depts else json_per_dept),
            )
        except Exception as exc:  # noqa: BLE001
            docs, errs = [], [(h["base_url"], str(exc))]
        all_docs.extend(docs)
        summary[h["name"]] = {"doctors": len(docs), "error": errs[0][1] if errs else None}

    if include_llm:
        for label, fn in LLM_JOBS:
            try:
                docs, errs = fn(fetch, extract, now=now, max_depts=max_depts,
                                max_per_dept=llm_per_dept, depts=depts)
            except Exception as exc:  # noqa: BLE001
                docs, errs = [], [(label, str(exc))]
            all_docs.extend(docs)
            summary[label] = {"doctors": len(docs), "error": errs[0][1] if errs else None}

    return all_docs, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="구현된 전 어댑터 통합 수집")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--depts", default=None, help='진료과명 부분일치, 쉼표구분. 예: "가정의학과,내과,정형외과"')
    parser.add_argument("--llm-per-dept", type=int, default=5, help="LLM 병원 과당 상한(토큰 절약)")
    parser.add_argument("--json-per-dept", type=int, default=15, help="JSON 병원(cmc/kumc) 과당 상한")
    parser.add_argument("--max-depts", type=int, default=None, help="과 선별 안 할 때 진료과 수 제한")
    parser.add_argument("--no-llm", action="store_true", help="JSON 병원만 수집(무료)")
    args = parser.parse_args()

    load_env_file(".env")
    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()

    from .deptfilter import parse_depts_arg

    all_docs, summary = run_all(
        lambda url: fetcher.fetch(url),
        now=now,
        extract=extract_doctor,
        depts=parse_depts_arg(args.depts),
        llm_per_dept=args.llm_per_dept,
        json_per_dept=args.json_per_dept,
        max_depts=args.max_depts,
        include_llm=not args.no_llm,
    )
    result = dedup(all_docs)
    save_doctors(result, args.out)
    print("=== 통합 수집 요약 ===")
    for name, info in summary.items():
        print(f"{name}: 의사 {info['doctors']}명, 오류={info['error']}")
    print(f"총 {len(result)}명 -> {args.out}")


if __name__ == "__main__":
    main()
