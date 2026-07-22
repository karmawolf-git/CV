"""가톨릭중앙의료원(CMC) 계열 병원 공용 어댑터.

CMC 계열은 동일 Vue 플랫폼(도메인만 다름, window.instNo로 구분)을 쓰며 공용 JSON API를 제공한다:

- 진료과:  {base}/api/department?deptClsf=A       → [{deptCd, deptNm, deptClsf, ...}]
- 의료진:  {base}/api/doctor?deptCd=<code>        → 목록 [{drNo, drName, deptCd, ...}]
- 상세:    {base}/api/doctor/<deptCd>/<drNo>      → doctorDetail.doctorRecordList[]
             (recordTypeText로 학력/경력/연수/수상이력/학회활동/연구분야 구분),
             doctorThesisList[](논문), doctorBookList[](저서)

전부 JSON이라 LLM 없이 직접 파싱한다. 목록에서 (deptCd, drNo)를 얻어 상세를 조회한다.

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


def detail_url(base_url: str, dept_cd: str, dr_no: str) -> str:
    return f"{base_url}/api/doctor/{dept_cd}/{dr_no}"


# recordTypeText -> Doctor 필드 버킷.
_RECORD_MAP = {
    "학력": "education",
    "경력": "career",
    "연수": "training",
    "학회활동": "societies",
    "수상이력": "awards",
    "연구분야": "research",
}


def _period(rec: dict) -> str | None:
    sta = str(rec.get("staYear") or "").strip()
    end = str(rec.get("endYear") or "").strip()
    if sta and end:
        return f"{sta}~{end}"
    if sta:
        return f"{sta}~"
    return end or None


def list_page_url(base_url: str, dr_no: str = "") -> str:
    """사람이 보는 의료진 목록 페이지(출처 링크용). drNo는 고유성 위해 프래그먼트로."""
    url = f"{base_url}/common.examination.doc_list.sp"
    return f"{url}#dr-{dr_no}" if dr_no else url


def parse_departments(dept_json_text: str) -> list[tuple[str, str]]:
    """부서 JSON에서 (deptCd, deptNm) 튜플을 순서 유지·중복 제거하여 반환."""
    data = json.loads(dept_json_text)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for d in data:
        cd = str(d.get("deptCd", "")).strip()
        nm = (d.get("deptNm") or "").strip()
        if cd and cd not in seen:
            seen.add(cd)
            out.append((cd, nm))
    return out


def parse_dept_codes(dept_json_text: str) -> list[str]:
    return [cd for cd, _nm in parse_departments(dept_json_text)]


def parse_doctor_ids(doctor_json_text: str) -> list[tuple[str, str]]:
    """의료진 목록 JSON에서 (drNo, name) 튜플을 순서 유지·중복 제거하여 반환."""
    data = json.loads(doctor_json_text)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for r in data:
        drno = str(r.get("drNo", "")).strip()
        name = (r.get("drName") or "").strip()
        if not drno or not name or drno in seen:
            continue
        seen.add(drno)
        out.append((drno, name))
    return out


def parse_detail(detail_json_text: str) -> dict:
    """상세 JSON에서 이름·직위·진료과·전문분야 + 학력/경력/연수/학회/수상/연구/논문·저서를 파싱한다."""
    j = json.loads(detail_json_text)
    rec = j[0] if isinstance(j, list) else j
    dept = rec.get("doctorDept") or {}
    detail = rec.get("doctorDetail") or {}

    education, career, training = [], [], []
    societies, awards, research = [], [], []
    for r in detail.get("doctorRecordList") or []:
        content = (r.get("recordContent") or "").strip()
        if not content:
            continue
        target = _RECORD_MAP.get((r.get("recordTypeText") or "").strip())
        period = _period(r)
        if target == "education":
            education.append({"institution": content, "year": period})
        elif target == "career":
            career.append({"org": content, "period": period})
        elif target == "training":
            training.append({"org": content, "period": period})
        elif target == "societies":
            societies.append(f"{period} {content}".strip() if period else content)
        elif target == "awards":
            awards.append(f"{period} {content}".strip() if period else content)
        elif target == "research":
            research.append(content)

    publications = []
    for th in detail.get("doctorThesisList") or []:
        title = (th.get("title") or "").strip()
        if not title:
            continue
        jn = (th.get("journalName") or "").strip()
        yr = str(th.get("postedYear") or "").strip()
        meta = ", ".join(x for x in (jn, yr) if x)
        publications.append(f"{title} ({meta})" if meta else title)
    for bk in detail.get("doctorBookList") or []:
        title = (bk.get("title") or "").strip()
        if title:
            publications.append(title)

    special = dept.get("nuSpecial") or ""
    return {
        "drNo": str(rec.get("drNo", "")).strip(),
        "name": (rec.get("drName") or "").strip(),
        "position": ((rec.get("nuHptlJobTitle") or "").strip() or None),
        "department": ((dept.get("deptNm") or rec.get("deptNm") or "").strip() or None),
        "specialty": [s.strip() for s in special.split(",") if s.strip()],
        "education": education,
        "career": career,
        "training": training,
        "societies": societies,
        "awards": awards,
        "research": research,
        "publications": publications,
    }


def to_doctor(detail: dict, *, hospital: str, base_url: str, crawled_at: str) -> Doctor:
    url = list_page_url(base_url, detail.get("drNo", ""))
    return Doctor(
        hospital=hospital,
        hospital_url=base_url,
        name=detail["name"],
        position=detail.get("position"),
        department=detail.get("department"),
        specialty=detail.get("specialty", []),
        education=detail.get("education", []),
        career=detail.get("career", []),
        training=detail.get("training", []),
        societies=detail.get("societies", []),
        awards=detail.get("awards", []),
        research=detail.get("research", []),
        publications=detail.get("publications", []),
        profile_url=url,
        source_url=url,
        crawled_at=crawled_at,
    )


def iter_doctor_details(fetch, base_url: str, *, max_depts=None, max_per_dept=None, depts=None):
    """``fetch(url)->text`` 로 의사별 상세 dict를 순차 생성. drNo 기준 병원 내 중복 제거.

    depts(진료과명 부분일치 리스트)가 주어지면 해당 과만 수집한다.
    """
    from ..deptfilter import dept_matches

    pairs = parse_departments(fetch(dept_url(base_url)))
    if depts:
        pairs = [(cd, nm) for cd, nm in pairs if dept_matches(nm, depts)]
    if max_depts is not None:
        pairs = pairs[:max_depts]
    seen: set[str] = set()
    for cd, _nm in pairs:
        count = 0
        for drno, _name in parse_doctor_ids(fetch(doctor_url(base_url, cd))):
            if drno in seen:
                continue
            seen.add(drno)
            yield parse_detail(fetch(detail_url(base_url, cd, drno)))
            count += 1
            if max_per_dept is not None and count >= max_per_dept:
                break
