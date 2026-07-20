"""공공 CSV로 전체 병원 카탈로그를 만들고, 어댑터 보유 여부를 표시해 저장/요약한다.

사용 예:
    python -m doctor_cv.run_catalog --basic data/기본정보.csv --facility data/시설정보.csv
    python -m doctor_cv.run_catalog --basic data/기본정보.csv   # 병상 필터 없이 종별만
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import registry
from .hospital_catalog import load_catalog


def annotate(catalog: list[dict]) -> list[dict]:
    """각 항목에 has_adapter 플래그를 붙인다."""
    for c in catalog:
        c["has_adapter"] = registry.has_adapter(c.get("name", ""))
    return catalog


def summarize(catalog: list[dict]) -> dict:
    with_home = sum(1 for c in catalog if c.get("homepage"))
    with_adapter = [c["name"] for c in catalog if c.get("has_adapter")]
    return {
        "total": len(catalog),
        "with_homepage": with_home,
        "with_adapter": len(with_adapter),
        "adapter_hospitals": with_adapter,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="전체 병원 카탈로그 생성 (공공 CSV)")
    parser.add_argument("--basic", required=True, help="기본정보 CSV 경로")
    parser.add_argument("--facility", default=None, help="시설정보 CSV 경로(병상수). 있으면 병상 필터 적용")
    parser.add_argument("--min-beds", type=int, default=300)
    parser.add_argument("--out", default="data/catalog.json")
    args = parser.parse_args()

    catalog = annotate(
        load_catalog(args.basic, facility_path=args.facility, min_beds=args.min_beds)
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    s = summarize(catalog)
    print("=== 병원 카탈로그 요약 ===")
    print(f"대상 병원(종합/상급종합{'·병상필터' if args.facility else ''}): {s['total']}곳")
    print(f"홈페이지 보유: {s['with_homepage']}곳")
    print(f"어댑터 구현(수집 가능): {s['with_adapter']}곳 -> {s['adapter_hospitals']}")
    print(f"저장: {args.out}")


if __name__ == "__main__":
    main()
