from doctor_cv.adapters import snubh

DEPT_XML = """<data>
<DEPT><NM>암센터</NM><TP>H</TP><DPCD>CCC</DPCD></DEPT>
<DEPT><NM>가정의학과</NM><TP>O</TP><DPCD>FM</DPCD></DEPT>
</data>"""

# 실제 카드 구조 모사: bh_doctor_name_n(이름) + page_move 버튼. 카드당 page_move 여러 번 등장.
LIST_HTML = """
<div class="bh_doctor_box_n">
  <div class="bh_doctor_name_n"><strong>이근욱 <em>교수</em></strong></div>
  <input onclick="page_move('drIntroduce', { 'sDpCdDtl' : 'IMH', 'sDrSid' : '1001304', 'sDrStfNo' : '01123' })">
  <input onclick="page_move('drIntroduce', { 'sDpCdDtl' : 'IMH', 'sDrSid' : '1001304', 'sDrStfNo' : '01123' })">
</div>
<div class="bh_doctor_box_n">
  <div class="bh_doctor_name_n"><strong>김철수 <em>교수</em></strong></div>
  <input onclick="page_move('drIntroduce', { 'sDpCdDtl' : 'GS', 'sDrSid' : '1000290', 'sDrStfNo' : '01033' })">
</div>
"""
LIST_EMPTY = "<div>없음</div>"


def test_parse_depts():
    assert snubh.parse_depts(DEPT_XML) == [("H", "CCC"), ("O", "FM")]


def test_parse_doctors_dedups_by_sid_with_names():
    docs = snubh.parse_doctors(LIST_HTML)
    assert docs == [
        ("이근욱", "IMH", "1001304", "01123"),
        ("김철수", "GS", "1000290", "01033"),
    ]


def test_url_builders():
    assert "DP_TP=H" in snubh.list_url("H", "CCC") and "DP_CD=CCC" in snubh.list_url("H", "CCC")
    du = snubh.detail_url("H", "CCC", "IMH", "1001304", "01123")
    assert "sDrSid=1001304" in du and "sDpCdDtl=IMH" in du and "sDrStfNo=01123" in du


def test_iter_detail_urls_dedups_across_depts():
    def fake_fetch(url):
        if url == snubh.dept_list_url():
            return DEPT_XML
        return LIST_HTML  # 두 부서 모두 같은 두 의사 반환 → 전역 dedup으로 2명

    results = list(snubh.iter_detail_urls(fake_fetch))
    assert len(results) == 2
    assert any("sDrSid=1001304" in u for _c, u, _n in results)
    assert any("sDrSid=1000290" in u for _c, u, _n in results)
    assert any(n == "이근욱" for _c, _u, n in results)


def test_trim_detail_isolates_profile_block():
    # 큰 페이지에서 경력+학력을 함께 담은 블록만 골라낸다.
    big = (
        "<html><body>"
        + "<div class='junk'>" + ("잡담 " * 500) + "</div>"
        + "<div class='profile'><h3>홍길동</h3>"
        + "<div class='career'>경력: 서울대병원 전임의 2010~2012 " + ("경력내용 " * 20) + "</div>"
        + "<div class='edu'>학력: 서울대학교 의학박사 " + ("학력내용 " * 20) + "</div>"
        + "</div>"
        + "</body></html>"
    )
    trimmed = snubh.trim_detail(big)
    assert "홍길동" in trimmed
    assert "경력" in trimmed and "학력" in trimmed
    assert "잡담" not in trimmed
    assert len(trimmed) < len(big)


def test_trim_detail_returns_original_when_no_markers():
    html = "<html><body><p>no profile markers here</p></body></html>"
    assert snubh.trim_detail(html) == html


def test_iter_detail_urls_respects_limits():
    def fake_fetch(url):
        if url == snubh.dept_list_url():
            return DEPT_XML
        return LIST_HTML

    limited = list(snubh.iter_detail_urls(fake_fetch, max_depts=1, max_per_dept=1))
    assert len(limited) == 1
