from doctor_cv.adapters import smc

GUBUN_HTML = """
<select><option value="">선택</option>
<option value="FM">가정의학과</option>
<option value="IM1">순환기내과</option>
<option value="FM">가정의학과(중복)</option>
</select>
"""

LIST_P1 = """
<a href="/home/reservation/common/doctorProfile.do?DR_NO=3">홍길동</a>
<a href="/home/reservation/common/doctorProfile.do?DR_NO=3">홍길동(중복링크)</a>
<a href="/home/reservation/common/doctorProfile.do?DR_NO=2207">김철수</a>
"""
LIST_EMPTY = "<div>결과 없음</div>"


def test_parse_dept_codes_excludes_empty_and_dedups():
    assert smc.parse_dept_codes(GUBUN_HTML) == ["FM", "IM1"]


def test_parse_doctor_ids_dedups():
    assert smc.parse_doctor_ids(LIST_P1) == ["3", "2207"]


def test_url_builders():
    assert "dp_type=O" in smc.gubun_url("O")
    lu = smc.list_url("FM", page=2)
    assert "DP_CODE=FM" in lu and "cPage=2" in lu and "FLAG=Y" in lu
    assert "DR_NO=3" in smc.profile_url("3")


def test_iter_profile_urls_paginates_and_stops_on_empty():
    def fake_fetch(url):
        if url == smc.gubun_url("O"):
            return GUBUN_HTML
        if "cPage=1" in url:
            return LIST_P1
        return LIST_EMPTY  # page 2+ -> 종료

    # 진료과 2개(FM, IM1) 각각 page1에 [3,2207] → 전역 중복제거로 총 2명.
    results = list(smc.iter_profile_urls(fake_fetch))
    assert len(results) == 2
    assert any("DR_NO=3" in u for _c, u in results)
    assert any("DR_NO=2207" in u for _c, u in results)


def test_iter_profile_urls_respects_limits():
    def fake_fetch(url):
        if url == smc.gubun_url("O"):
            return GUBUN_HTML
        if "cPage=1" in url:
            return LIST_P1
        return LIST_EMPTY

    limited = list(smc.iter_profile_urls(fake_fetch, max_depts=1, max_per_dept=1))
    assert len(limited) == 1
