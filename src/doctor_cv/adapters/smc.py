"""삼성서울병원(SMC) 의료진 어댑터.

SMC 의료진 검색 페이지의 하위 엔드포인트는 서버 렌더링 HTML을 반환한다(httpx로 수집 가능):

- 진료과 코드:  /home/reservation/DoctorScheduleGubun.do?dp_type=O
    ``<option value="FM">가정의학과</option>`` 형태(빈 값 옵션 제외).
- 진료과별 목록: /home/reservation/doctorInfoLists.do?DP_CODE=<code>&DP_TYPE=O&cPage=<n>&SW=&SUB_DEPT_YN=A&FLAG=Y
    ``doctorProfile.do?DR_NO=<번호>`` 링크가 들어 있다(cPage 페이지네이션).
- 상세:         /home/reservation/common/doctorProfile.do?DR_NO=<번호>

dp_type: O=진료과, C=센터, N=클리닉. 기본은 진료과(O).
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

HOSPITAL_NAME = "삼성서울병원"
BASE = "https://www.samsunghospital.com"
GUBUN_PATH = "/home/reservation/DoctorScheduleGubun.do"
LIST_PATH = "/home/reservation/doctorInfoLists.do"
PROFILE_PATH = "/home/reservation/common/doctorProfile.do"

_OPT_RE = re.compile(r'<option\s+value="([^"]+)"', re.IGNORECASE)
_DRNO_RE = re.compile(r"doctorProfile\.do\?DR_NO=(\d+)")


def gubun_url(dp_type: str = "O") -> str:
    return f"{BASE}{GUBUN_PATH}?{urlencode({'dp_type': dp_type})}"


def list_url(dept_code: str, *, dp_type: str = "O", page: int = 1) -> str:
    q = urlencode(
        {
            "cPage": page,
            "SW": "",
            "SUB_DEPT_YN": "A",
            "DP_CODE": dept_code,
            "DP_TYPE": dp_type,
            "FLAG": "Y",
        }
    )
    return f"{BASE}{LIST_PATH}?{q}"


def profile_url(dr_no: str) -> str:
    return f"{BASE}{PROFILE_PATH}?{urlencode({'DR_NO': dr_no})}"


def parse_dept_codes(gubun_html: str) -> list[str]:
    """gubun HTML의 <option> 값에서 진료과 코드를 순서 유지·중복 제거하여 반환(빈 값 제외)."""
    codes = [v for v in _OPT_RE.findall(gubun_html) if v.strip()]
    return list(dict.fromkeys(codes))


def parse_doctor_ids(list_html: str) -> list[str]:
    """목록 HTML의 doctorProfile.do?DR_NO=... 에서 DR_NO를 순서 유지·중복 제거하여 반환."""
    return list(dict.fromkeys(_DRNO_RE.findall(list_html)))


def iter_profile_urls(
    fetch,
    *,
    dp_type: str = "O",
    max_depts: int | None = None,
    max_per_dept: int | None = None,
    max_pages: int = 30,
):
    """``fetch(url)->html`` 콜러블로 상세 프로필 URL을 (dept_code, url)로 순차 생성.

    진료과별로 cPage를 1부터 증가시키며, 새 DR_NO가 없는 페이지를 만나면 그 진료과를 종료한다.
    DR_NO는 전 진료과에 걸쳐 중복 제거한다.
    """
    codes = parse_dept_codes(fetch(gubun_url(dp_type)))
    if max_depts is not None:
        codes = codes[:max_depts]
    seen: set[str] = set()
    for code in codes:
        dept_count = 0
        for page in range(1, max_pages + 1):
            ids = parse_doctor_ids(fetch(list_url(code, dp_type=dp_type, page=page)))
            new = [i for i in ids if i not in seen]
            if not new:
                break  # 이 페이지에 새 의사가 없음 → 진료과 종료
            for dr in new:
                seen.add(dr)
                yield code, profile_url(dr)
                dept_count += 1
                if max_per_dept is not None and dept_count >= max_per_dept:
                    break
            if max_per_dept is not None and dept_count >= max_per_dept:
                break
