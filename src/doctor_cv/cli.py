from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .discovery import find_profile_urls
from .extractor import extract_doctor
from .fetcher import Fetcher
from .hospital_list import load_hospitals
from .models import Doctor, Hospital
from .store import dedup, save_doctors


def run_pipeline(
    hospitals: list[Hospital],
    *,
    out_path: str | Path,
    fetch,
    discover,
    extract,
    now: str,
) -> dict:
    all_doctors: list[Doctor] = []
    summary: dict = {}
    for h in hospitals:
        try:
            index_html = fetch(h.doctor_index_url)
            profile_urls = discover(index_html, base_url=h.base_url)
            docs: list[Doctor] = []
            for url in profile_urls:
                try:
                    html = fetch(url)
                    doc = extract(
                        html,
                        hospital=h.name,
                        hospital_url=h.base_url,
                        source_url=url,
                        crawled_at=now,
                    )
                    docs.append(doc)
                except Exception as exc:  # noqa: BLE001 - 의사 단위 격리
                    print(f"[WARN] {h.id} 프로필 실패 {url}: {exc}")
            all_doctors.extend(docs)
            summary[h.id] = {"doctors": len(docs), "error": None}
        except Exception as exc:  # noqa: BLE001 - 병원 단위 격리
            summary[h.id] = {"doctors": 0, "error": str(exc)}
            print(f"[ERROR] {h.id} 병원 실패: {exc}")

    save_doctors(dedup(all_doctors), out_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="의료진 경력 크롤러 (Phase 1)")
    parser.add_argument("--hospitals", default="hospitals.yaml")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=1.0)
    args = parser.parse_args()

    hospitals = load_hospitals(args.hospitals)
    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()

    summary = run_pipeline(
        hospitals,
        out_path=args.out,
        fetch=lambda url, **kw: fetcher.fetch(url),
        discover=find_profile_urls,
        extract=extract_doctor,
        now=now,
    )
    print("=== 수집 요약 ===")
    for hid, info in summary.items():
        print(f"{hid}: 의사 {info['doctors']}명, 오류={info['error']}")


if __name__ == "__main__":
    main()
