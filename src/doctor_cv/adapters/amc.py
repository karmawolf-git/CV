"""서울아산병원(AMC) 의료진 어댑터.

AMC 의료진 페이지는 JS 프론트지만, 뒤의 엔드포인트는 서버 렌더링 HTML을 반환한다
(httpx만으로 수집 가능, Playwright 불필요):

- 목록 진입:  /asan/staff/base/staffBaseInfoList.do
    진료과 코드가 ``fnSelectDeptPopup('D001')`` 형태로 들어 있다.
- 진료과별:  /asan/staff/base/staffBaseInfoList.do?searchHpCd=<code>
    의사가 ``fnDrDetail('<empId>','<code>')`` 형태로 들어 있다(카드당 여러 번 → 중복제거).
- 상세:      /asan/staff/base/staffBaseInfoDetail.do?drEmpId=<empId>&searchHpCd=<code>
    학력·경력·전문분야 등이 서버 렌더링 HTML로 존재.
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

HOSPITAL_NAME = "서울아산병원"
BASE = "https://www.amc.seoul.kr"
LIST_PATH = "/asan/staff/base/staffBaseInfoList.do"
DETAIL_PATH = "/asan/staff/base/staffBaseInfoDetail.do"

_DEPT_RE = re.compile(r"fnSelectDeptPopup\('([^']+)'\)")
_DR_RE = re.compile(r"fnDrDetail\('([^']+)','([^']+)'\)")


def index_url() -> str:
    return f"{BASE}{LIST_PATH}"


def list_url(dept_code: str) -> str:
    q = urlencode({"drEmpId": "", "deptTabIndex": "", "searchHpCd": dept_code, "searchKeyword": ""})
    return f"{BASE}{LIST_PATH}?{q}"


def detail_url(emp_id: str, dept_code: str) -> str:
    q = urlencode({"drEmpId": emp_id, "deptTabIndex": "", "searchHpCd": dept_code, "searchKeyword": ""})
    return f"{BASE}{DETAIL_PATH}?{q}"


# 프로필 탭: 1=소개(직위·전문분야·요약), 3=학력/경력, 5=학술활동(논문·저서 등).
# changeTab(str)이 #tabIndex1을 세팅해 제출하므로 GET tabIndex1로 각 탭을 가져올 수 있다.
PROFILE_TABS = ("1", "3", "5")


def detail_tab_url(emp_id: str, dept_code: str, tab: str) -> str:
    q = urlencode(
        {"drEmpId": emp_id, "searchHpCd": dept_code, "searchKeyword": "", "pageIndex": "1", "tabIndex1": tab}
    )
    return f"{BASE}{DETAIL_PATH}?{q}"


def detail_tab_urls(emp_id: str, dept_code: str) -> list[str]:
    return [detail_tab_url(emp_id, dept_code, t) for t in PROFILE_TABS]


def parse_dept_codes(index_html: str) -> list[str]:
    """목록 진입 HTML에서 진료과 코드를 순서 유지·중복 제거하여 반환."""
    return list(dict.fromkeys(_DEPT_RE.findall(index_html)))


def parse_doctor_ids(list_html: str) -> list[str]:
    """진료과 목록 HTML에서 의사 empId를 순서 유지·중복 제거하여 반환."""
    return list(dict.fromkeys(m[0] for m in _DR_RE.findall(list_html)))


def iter_doctor_refs(fetch, *, max_depts: int | None = None, max_per_dept: int | None = None):
    """``fetch(url)->html`` 콜러블로 (dept_code, emp_id)를 순차 생성. empId 기준 전역 중복 제거."""
    codes = parse_dept_codes(fetch(index_url()))
    if max_depts is not None:
        codes = codes[:max_depts]
    seen: set[str] = set()
    for code in codes:
        ids = parse_doctor_ids(fetch(list_url(code)))
        if max_per_dept is not None:
            ids = ids[:max_per_dept]
        for emp_id in ids:
            if emp_id in seen:
                continue
            seen.add(emp_id)
            yield code, emp_id


def iter_detail_urls(fetch, *, max_depts: int | None = None, max_per_dept: int | None = None):
    """(dept_code, 소개탭 URL) 생성 — 하위호환용. 전체 수집은 detail_tab_urls를 쓴다."""
    for code, emp_id in iter_doctor_refs(fetch, max_depts=max_depts, max_per_dept=max_per_dept):
        yield code, detail_url(emp_id, code)
