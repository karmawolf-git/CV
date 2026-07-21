from doctor_cv.adapters import kumc
from doctor_cv.models import Doctor

LIST_P1 = '{"doctorTotCnt":3,"doctorList":[{"drNo":"7454","drName":"강동오"},{"drNo":"8723","drName":"김철수"}]}'
LIST_P2 = '{"doctorTotCnt":3,"doctorList":[{"drNo":"6349","drName":"이영희"}]}'
LIST_EMPTY = '{"doctorTotCnt":3,"doctorList":[]}'

BASIC = '{"drNo":"7454","drName":"강동오","hptlJobTitle":"교수","deptNm":"심혈관센터(순환기)","special":"관상동맥, 부정맥","pid":"144311"}'
RECORDS = """[
  {"recordTypeText":"학력","staYear":"1998","endYear":"2002","recordContent":"고려대 의학박사"},
  {"recordTypeText":"경력","staYear":"2011","endYear":"현재","recordContent":"구로병원 교수"},
  {"recordTypeText":"수상이력","staYear":"2020","endYear":"","recordContent":"우수논문상"},
  {"recordTypeText":"학회","staYear":"2015","endYear":"현재","recordContent":"대한심장학회 이사"}
]"""
BOOKS = '[{"title":"혈관영상생리 매뉴얼 (공저)","publishYear":"2023"}]'
THESIS = '{"items":[{"dc_title":"Drug-coated balloon study","dc_citation_title":"JACC","dc_date_issued":"2023-05"}]}'


def test_parse_list():
    drnos, total = kumc.parse_list(LIST_P1)
    assert drnos == ["7454", "8723"] and total == 3


def test_url_builders():
    lu = kumc.list_url("https://guro.kumc.or.kr", "2", start=1, rows=50)
    assert "instNo=2" in lu and "pageRow=50" in lu and "deptClsf=A" in lu
    assert "doctorApi/7454" in kumc.basic_url("https://guro.kumc.or.kr", "7454")
    assert "getDoctorRecordList.do?drNo=7454" in kumc.record_url("https://guro.kumc.or.kr", "7454")
    assert "doctor/view.do?drNo=7454" in kumc.profile_url("https://guro.kumc.or.kr", "7454")


def test_parse_basic_and_records():
    b = kumc.parse_basic(BASIC)
    assert b["name"] == "강동오" and b["position"] == "교수" and b["pid"] == "144311"
    assert b["specialty"] == ["관상동맥", "부정맥"]
    r = kumc.parse_records(RECORDS)
    assert r["education"] == [{"institution": "고려대 의학박사", "year": "1998~2002"}]
    assert r["career"] == [{"org": "구로병원 교수", "period": "2011~현재"}]
    assert r["awards"] == ["2020~ 우수논문상"]
    assert r["societies"] == ["2015~현재 대한심장학회 이사"]


def test_parse_publications_thesis_and_books():
    pubs = kumc.parse_publications(BOOKS, THESIS)
    assert pubs == ["Drug-coated balloon study (JACC, 2023)", "혈관영상생리 매뉴얼 (공저)"]


def test_iter_doctor_ids_paginates_and_limits():
    def fetch(url):
        if "startIndex=1&" in url:
            return LIST_P1
        if "startIndex=3" in url:
            return LIST_P2
        return LIST_EMPTY

    ids = list(kumc.iter_doctor_ids(fetch, "https://guro.kumc.or.kr", "2", rows=2))
    assert ids == ["7454", "8723", "6349"]
    assert list(kumc.iter_doctor_ids(fetch, "https://guro.kumc.or.kr", "2", rows=2, max_doctors=1)) == ["7454"]


def test_build_doctor_assembles_from_apis():
    def fetch(url):
        if "/doctorApi/" in url:
            return BASIC
        if "getDoctorRecordList" in url:
            return RECORDS
        if "getDoctorBookList" in url:
            return BOOKS
        if "ThesisScholar" in url:
            return THESIS
        raise AssertionError("unexpected " + url)

    d = kumc.build_doctor(fetch, "https://guro.kumc.or.kr", "7454", hospital="고려대학교 구로병원", crawled_at="2026-07-21T00:00:00+00:00")
    assert isinstance(d, Doctor)
    assert d.name == "강동오" and d.department == "심혈관센터(순환기)"
    assert d.career and d.awards and d.societies and d.publications
