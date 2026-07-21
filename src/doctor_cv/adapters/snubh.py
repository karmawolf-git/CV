"""분당서울대학교병원(SNUBH) 의료진 어댑터.

엔드포인트(모두 서버 응답, httpx로 수집 가능):

- 부서 목록:   /common/ajax/getDeptList.do  (XML: <DEPT><TP>..</TP><DPCD>..</DPCD></DEPT>)
- 부서별 목록: /medical/drMedicalTeam.do?DP_TP=<tp>&DP_CD=<dpcd>&grp_val=Y
    의사 카드에 ``page_move('drIntroduce', {'sDpCdDtl':..,'sDrSid':..,'sDrStfNo':..})`` 형태.
- 상세:        /medical/drIntroduce.do?sDpCdDtl=<..>&sDrSid=<drNo>&sDrStfNo=<..>&DP_TP=<tp>&DP_CD=<dpcd>&grp_val=Y

주의: 부서에는 센터(TP=H)와 진료과(TP=O)가 섞여 있고 의사가 여러 부서에 중복 등장하므로
sDrSid(의사 고유번호) 기준으로 전역 중복 제거한다.
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

HOSPITAL_NAME = "분당서울대학교병원"
BASE = "https://www.snubh.org"
DEPT_LIST_PATH = "/common/ajax/getDeptList.do"
LIST_PATH = "/medical/drMedicalTeam.do"
DETAIL_PATH = "/medical/drIntroduce.do"

# 태그명 대소문자 무시(정적 XML은 대문자, 혹시 렌더러가 소문자로 바꿔도 대응).
_DEPT_RE = re.compile(r"<TP>([^<]+)</TP>\s*<DPCD>([^<]+)</DPCD>", re.IGNORECASE)
_DR_RE = re.compile(
    r"page_move\(\s*'drIntroduce'\s*,\s*\{\s*"
    r"'sDpCdDtl'\s*:\s*'([^']*)'\s*,\s*"
    r"'sDrSid'\s*:\s*'([^']*)'\s*,\s*"
    r"'sDrStfNo'\s*:\s*'([^']*)'"
)


def dept_list_url() -> str:
    return f"{BASE}{DEPT_LIST_PATH}"


def list_url(dp_tp: str, dp_cd: str) -> str:
    q = urlencode({"DP_TP": dp_tp, "DP_CD": dp_cd, "grp_val": "Y"})
    return f"{BASE}{LIST_PATH}?{q}"


def detail_url(dp_tp: str, dp_cd: str, dpcd_dtl: str, dr_sid: str, stf_no: str) -> str:
    q = urlencode(
        {
            "sDpCdDtl": dpcd_dtl,
            "sDrSid": dr_sid,
            "sDrStfNo": stf_no,
            "DP_TP": dp_tp,
            "DP_CD": dp_cd,
            "grp_val": "Y",
        }
    )
    return f"{BASE}{DETAIL_PATH}?{q}"


def parse_depts(xml: str) -> list[tuple[str, str]]:
    """부서 XML에서 (DP_TP, DP_CD) 쌍을 순서 유지·중복 제거하여 반환."""
    return list(dict.fromkeys(_DEPT_RE.findall(xml)))


def parse_doctors(list_html: str) -> list[tuple[str, str, str, str]]:
    """부서 목록 HTML에서 (name, sDpCdDtl, sDrSid, sDrStfNo) 4튜플을 반환.

    상세 페이지의 경력 블록에는 이름이 없으므로, 목록 카드(``bh_doctor_name_n``)에서
    이름을 함께 수집해 추출 단계에 넘긴다. sDrSid 기준 중복 제거.
    """
    soup = BeautifulSoup(list_html, "html.parser")
    seen: set[str] = set()
    out: list[tuple[str, str, str, str]] = []
    for el in soup.find_all(onclick=lambda v: bool(v) and _DR_RE.search(v)):
        m = _DR_RE.search(el.get("onclick", ""))
        if not m:
            continue
        dtl, sid, stf = m.group(1), m.group(2), m.group(3)
        if sid in seen:
            continue
        seen.add(sid)
        name = ""
        node = el
        for _ in range(6):
            node = node.parent
            if node is None:
                break
            nm = node.select_one(".bh_doctor_name_n")
            if nm:
                raw = nm.get_text(" ", strip=True)
                name = raw.split()[0] if raw.split() else ""
                break
        out.append((name, dtl, sid, stf))
    return out


def trim_detail(html: str, *, max_len: int = 8000, per_block: int = 6000, total_cap: int = 16000) -> str:
    """drIntroduce.do 상세 HTML에서 해당 의사 프로필만 잘라낸다.

    프로필은 탭 패널(id=cont_wrap1..N)로 나뉜다: 소개/전문분야/(학력·경력·연수·학회·수상·
    연구분야)/논문·저서/언론. 논문 패널은 공저자까지 포함해 매우 클 수 있으므로(수십만 자)
    패널마다 상한(per_block)을 두고 이어붙인 뒤 total_cap으로 자른다. 이렇게 하면
    부서 전체 사이드바(수십만 자)는 빼고 해당 의사 전 섹션을 담는다.

    cont_wrap 패널이 없으면, '경력'+('학력'|'약력')을 담은 가장 작은 블록으로 폴백한다.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    panels = soup.select('[id*="cont_wrap"]')
    if panels:
        parts = [p.get_text(" ", strip=True)[:per_block] for p in panels]
        return "\n\n".join(x for x in parts if x)[:total_cap]

    best = None
    best_len = None
    for el in soup.find_all(True):
        txt = el.get_text(" ", strip=True)
        n = len(txt)
        if n < 200 or n > max_len:
            continue
        if "경력" in txt and ("학력" in txt or "약력" in txt):
            if best_len is None or n < best_len:
                best, best_len = el, n
    return html if best is None else str(best)


def iter_detail_urls(fetch, *, max_depts: int | None = None, max_per_dept: int | None = None):
    """``fetch(url)->html`` 콜러블로 상세 URL을 (dp_cd, url)로 순차 생성. sDrSid 전역 중복 제거."""
    depts = parse_depts(fetch(dept_list_url()))
    if max_depts is not None:
        depts = depts[:max_depts]
    seen: set[str] = set()
    for dp_tp, dp_cd in depts:
        doctors = parse_doctors(fetch(list_url(dp_tp, dp_cd)))
        count = 0
        for name, dtl, sid, stf in doctors:
            if sid in seen:
                continue
            seen.add(sid)
            yield dp_cd, detail_url(dp_tp, dp_cd, dtl, sid, stf), name
            count += 1
            if max_per_dept is not None and count >= max_per_dept:
                break
