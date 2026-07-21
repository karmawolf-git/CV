"""고려대학교의료원(KUMC) 계열 어댑터 — 안암·구로·안산.

세 병원이 공용 백엔드를 쓰며 instNo로 구분한다. 상세가 전부 JSON API로 제공되어
LLM 없이 직접 파싱한다(정확·무료).

- 목록:  {base}/api/doctorApi.do?startIndex&pageRow&langType=kr&instNo=<n>&deptClsf=A&deptCd=&chosung=
         → {"doctorList":[{drNo,...}], "doctorTotCnt": N}
- 기본:  {base}/api/doctorApi/<drNo>            → drName, hptlJobTitle, deptNm, special, pid
- 이력:  {base}/api/getDoctorRecordList.do?drNo=<n>&langType=kr
         → [{recordTypeText(학력/경력/연수/학회(활동)/수상이력/연구분야), staYear, endYear, recordContent}]
- 저서:  {base}/api/getDoctorBookList.do?drNo=<n>        → [{title, publishName, publishYear}]
- 논문:  {base}/api/doctor/getDoctorThesisScholarList.do?pid=<pid>  → {items:[{dc_title, dc_citation_title, dc_date_issued}]}

instNo: 1=안암, 2=구로, 3=안산.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode

from ..models import Doctor

HOSPITALS = [
    {"name": "고려대학교 안암병원", "base_url": "https://anam.kumc.or.kr", "inst_no": "1"},
    {"name": "고려대학교 구로병원", "base_url": "https://guro.kumc.or.kr", "inst_no": "2"},
    {"name": "고려대학교 안산병원", "base_url": "https://ansan.kumc.or.kr", "inst_no": "3"},
]

HOSPITAL_NAME = "고려대학교 구로병원"
BASE = "https://guro.kumc.or.kr"

_RECORD_MAP = {
    "학력": "education",
    "경력": "career",
    "연수": "training",
    "학회": "societies",
    "학회활동": "societies",
    "수상이력": "awards",
    "수상": "awards",
    "연구분야": "research",
    "연구": "research",
}


def list_url(base_url: str, inst_no: str, *, start: int = 1, rows: int = 100) -> str:
    q = urlencode({
        "startIndex": start, "pageRow": rows, "drName": "", "langType": "kr",
        "instNo": inst_no, "deptClsf": "A", "deptCd": "", "chosung": "",
    })
    return f"{base_url}/api/doctorApi.do?{q}"


def basic_url(base_url: str, dr_no: str) -> str:
    return f"{base_url}/api/doctorApi/{dr_no}"


def record_url(base_url: str, dr_no: str) -> str:
    return f"{base_url}/api/getDoctorRecordList.do?{urlencode({'drNo': dr_no, 'langType': 'kr'})}"


def book_url(base_url: str, dr_no: str) -> str:
    return f"{base_url}/api/getDoctorBookList.do?{urlencode({'drNo': dr_no})}"


def thesis_url(base_url: str, pid: str) -> str:
    return f"{base_url}/api/doctor/getDoctorThesisScholarList.do?{urlencode({'pid': pid})}"


def profile_url(base_url: str, dr_no: str) -> str:
    return f"{base_url}/kr/doctor-department/doctor/view.do?{urlencode({'drNo': dr_no})}"


def _period(rec: dict) -> str | None:
    sta = str(rec.get("staYear") or "").strip()
    end = str(rec.get("endYear") or "").strip()
    if sta and end:
        return f"{sta}~{end}"
    if sta:
        return f"{sta}~"
    return end or None


def parse_list(list_json_text: str) -> tuple[list[str], int]:
    j = json.loads(list_json_text)
    doctors = j.get("doctorList") or []
    total = int(j.get("doctorTotCnt") or 0)
    drnos = [str(d.get("drNo")).strip() for d in doctors if d.get("drNo") not in (None, "")]
    return drnos, total


def _first_record(j):
    """doctorApi/{drNo} 응답에서 의사 dict를 꺼낸다(형태 방어)."""
    if isinstance(j, list):
        return j[0] if j else {}
    if isinstance(j, dict):
        if "drName" in j:
            return j
        for k in ("doctor", "data", "result"):
            if isinstance(j.get(k), dict):
                return j[k]
    return j if isinstance(j, dict) else {}


def parse_basic(basic_json_text: str) -> dict:
    d = _first_record(json.loads(basic_json_text))
    dept = d.get("doctorDept") or {}
    special = d.get("special") or d.get("emrSpecial") or (dept.get("nuSpecial") if isinstance(dept, dict) else "") or ""
    return {
        "drNo": str(d.get("drNo", "")).strip(),
        "pid": str(d.get("pid") or d.get("emrNo") or "").strip(),
        "name": (d.get("drName") or "").strip(),
        "position": ((d.get("hptlJobTitle") or d.get("schlJobTitle") or "").strip() or None),
        "department": ((d.get("deptNm") or (dept.get("deptNm") if isinstance(dept, dict) else "") or "").strip() or None),
        "specialty": [s.strip() for s in str(special).split(",") if s.strip()],
    }


def parse_records(record_json_text: str) -> dict:
    j = json.loads(record_json_text)
    records = j if isinstance(j, list) else (j.get("recordList") or j.get("list") or [])
    buckets = {"education": [], "career": [], "training": [], "societies": [], "awards": [], "research": []}
    for r in records:
        content = (r.get("recordContent") or "").strip()
        if not content:
            continue
        target = _RECORD_MAP.get((r.get("recordTypeText") or "").strip())
        if not target:
            continue
        period = _period(r)
        if target in ("education",):
            buckets[target].append({"institution": content, "year": period})
        elif target in ("career", "training"):
            buckets[target].append({"org": content, "period": period})
        else:
            buckets[target].append(f"{period} {content}".strip() if period else content)
    return buckets


def parse_publications(book_json_text: str, thesis_json_text: str | None) -> list[str]:
    pubs: list[str] = []
    if thesis_json_text:
        tj = json.loads(thesis_json_text)
        items = tj.get("items") if isinstance(tj, dict) else (tj if isinstance(tj, list) else [])
        for it in items or []:
            title = (it.get("dc_title") or "").strip()
            if not title:
                continue
            jn = (it.get("dc_citation_title") or "").strip()
            yr = str(it.get("dc_date_issued") or "").strip()[:4]
            meta = ", ".join(x for x in (jn, yr) if x)
            pubs.append(f"{title} ({meta})" if meta else title)
    bj = json.loads(book_json_text)
    books = bj if isinstance(bj, list) else (bj.get("bookList") or bj.get("list") or [])
    for b in books:
        title = (b.get("title") or "").strip()
        if title:
            pubs.append(title)
    return pubs


def iter_doctor_ids(fetch, base_url: str, inst_no: str, *, max_doctors: int | None = None, rows: int = 100):
    """``fetch(url)->text`` 로 drNo를 순차 생성(페이지네이션, 중복 제거)."""
    seen: set[str] = set()
    yielded = 0
    start = 1
    while True:
        drnos, total = parse_list(fetch(list_url(base_url, inst_no, start=start, rows=rows)))
        if not drnos:
            break
        for dr in drnos:
            if dr in seen:
                continue
            seen.add(dr)
            yield dr
            yielded += 1
            if max_doctors is not None and yielded >= max_doctors:
                return
        start += rows
        if total and start > total:
            break


def build_doctor(fetch, base_url: str, dr_no: str, *, hospital: str, crawled_at: str) -> Doctor:
    """의사 1명의 기본+이력+저서+논문 API를 조회해 Doctor를 만든다."""
    basic = parse_basic(fetch(basic_url(base_url, dr_no)))
    recs = parse_records(fetch(record_url(base_url, dr_no)))
    thesis_text = fetch(thesis_url(base_url, basic["pid"])) if basic.get("pid") else None
    pubs = parse_publications(fetch(book_url(base_url, dr_no)), thesis_text)
    url = profile_url(base_url, dr_no)
    return Doctor(
        hospital=hospital,
        hospital_url=base_url,
        name=basic["name"],
        position=basic.get("position"),
        department=basic.get("department"),
        specialty=basic.get("specialty", []),
        education=recs["education"],
        career=recs["career"],
        training=recs["training"],
        societies=recs["societies"],
        awards=recs["awards"],
        research=recs["research"],
        publications=pubs,
        profile_url=url,
        source_url=url,
        crawled_at=crawled_at,
    )
