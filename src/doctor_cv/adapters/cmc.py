"""가톨릭중앙의료원(CMC) 계열 병원 공용 어댑터.

CMC 계열은 동일 Vue 플랫폼(도메인만 다름, window.instNo로 구분)을 쓰며 공용 JSON API를 제공한다:

- 진료과:  {base}/api/department?deptClsf=A   → [{deptCd, deptNm, deptClsf, ...}]
- 의료진:  {base}/api/doctor?deptCd=<code>    → [{drNo, drName, nuHptlJobTitle,
             doctorDept:{deptNm, nuSpecial}, ...}]

의사 목록 JSON에 이름·직위·진료과·전문분야가 들어 있어 LLM 없이 직접 파싱한다.
(학력·경력은 이 플랫폼 API로 노출되지 않아 이 병원군에서는 수집하지 않는다.)

공유 API가 확인된 병원만 HOSPITALS에 넣는다(인천/대전성모 등 구형 사이트는 404 → 제외).
"""
from __future__ import annotations

import json
from urllib.parse import urlencode

from ..models import Doctor

# 공유 API가 확인된 CMC 계열 병원.
HOSPITALS = [
    {"name": "가톨릭대학교 서울성모병원", "base_url": "https://www.cmcseoul.or.kr"},
    {"name": "가톨릭대학교 부천성모병원", "base_url": "https://www.cmcbucheon.or.kr"},
    {"name": "가톨릭대학교 은평성모병원", "base_url": "https://www.cmcep.or.kr"},
    {"name": "가톨릭대학교 성빈센트병원", "base_url": "https://www.cmcvincent.or.kr"},
]

# 레지스트리 매칭용 대표값(서울성모).
HOSPITAL_NAME = "서울성모병원"
BASE = "https://www.cmcseoul.or.kr"


def dept_url(base_url: str, dept_clsf: str = "A") -> str:
    return f"{base_url}/api/department?{urlencode({'deptClsf': dept_clsf})}"


def doctor_url(base_url: str, dept_cd: str) -> str:
    return f"{base_url}/api/doctor?{urlencode({'deptCd': dept_cd})}"


def list_page_url(base_url: str, dr_no: str = "") -> str:
    """사람이 보는 의료진 목록 페이지(출처 링크용). drNo는 고유성 위해 프래그먼트로."""
    url = f"{base_url}/common.examination.doc_list.sp"
    return f"{url}#dr-{dr_no}" if dr_no else url


def parse_dept_codes(dept_json_text: str) -> list[str]:
    data = json.loads(dept_json_text)
    codes: list[str] = []
    seen: set[str] = set()
    for d in data:
        cd = str(d.get("deptCd", "")).strip()
        if cd and cd not in seen:
            seen.add(cd)
            codes.append(cd)
    return codes


def parse_doctors(doctor_json_text: str) -> list[dict]:
    """의료진 JSON에서 {drNo, name, position, department, specialty[]} 리스트를 만든다."""
    data = json.loads(doctor_json_text)
    out: list[dict] = []
    for r in data:
        dept = r.get("doctorDept") or {}
        special = dept.get("nuSpecial") or ""
        specialty = [s.strip() for s in special.split(",") if s.strip()]
        out.append(
            {
                "drNo": str(r.get("drNo", "")).strip(),
                "name": (r.get("drName") or "").strip(),
                "position": ((r.get("nuHptlJobTitle") or "").strip() or None),
                "department": ((dept.get("deptNm") or r.get("deptNm") or "").strip() or None),
                "specialty": specialty,
            }
        )
    return out


def to_doctor(rec: dict, *, hospital: str, base_url: str, crawled_at: str) -> Doctor:
    url = list_page_url(base_url, rec.get("drNo", ""))
    return Doctor(
        hospital=hospital,
        hospital_url=base_url,
        name=rec["name"],
        position=rec.get("position"),
        department=rec.get("department"),
        specialty=rec.get("specialty", []),
        profile_url=url,
        source_url=url,
        crawled_at=crawled_at,
    )


def iter_doctors(fetch, base_url: str, *, max_depts: int | None = None, max_per_dept: int | None = None):
    """``fetch(url)->text`` 로 의료진 레코드를 순차 생성. drNo 기준 병원 내 중복 제거."""
    codes = parse_dept_codes(fetch(dept_url(base_url)))
    if max_depts is not None:
        codes = codes[:max_depts]
    seen: set[str] = set()
    for cd in codes:
        recs = parse_doctors(fetch(doctor_url(base_url, cd)))
        count = 0
        for rec in recs:
            if not rec["name"] or rec["drNo"] in seen:
                continue
            seen.add(rec["drNo"])
            yield rec
            count += 1
            if max_per_dept is not None and count >= max_per_dept:
                break
