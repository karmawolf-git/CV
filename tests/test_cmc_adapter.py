from doctor_cv.adapters import cmc
from doctor_cv.models import Doctor

DEPT_JSON = """[
  {"deptCd":"1","deptNm":"가정의학과","deptClsf":"A"},
  {"deptCd":"6","deptNm":"간담췌외과","deptClsf":"A"},
  {"deptCd":"1","deptNm":"중복","deptClsf":"A"}
]"""

LIST_JSON = """[
  {"drNo":"D0001101","drName":"이재호"},
  {"drNo":"D0002222","drName":"김철수"},
  {"drNo":"D0002222","drName":"김철수중복"}
]"""

DETAIL_JSON = """{
  "drNo":"D0001101","drName":"이재호","nuHptlJobTitle":"교수",
  "doctorDept":{"deptNm":"가정의학과","nuSpecial":"건강검진, 금연"},
  "doctorDetail":{
    "doctorRecordList":[
      {"recordTypeText":"학력","staYear":"1998","endYear":"2002","recordContent":"가톨릭대학교 의학 박사"},
      {"recordTypeText":"경력","staYear":"2011","endYear":"현재","recordContent":"서울성모병원 교수"},
      {"recordTypeText":"연수","staYear":"2005","endYear":"2006","recordContent":"Baylor College"},
      {"recordTypeText":"학회활동","staYear":"2006","endYear":"현재","recordContent":"일차의료연구회 회장"},
      {"recordTypeText":"수상이력","staYear":"2012","endYear":"","recordContent":"우수논문상"},
      {"recordTypeText":"연구분야","staYear":"","endYear":"","recordContent":"일차의료 연구"},
      {"recordTypeText":"학력","staYear":"","endYear":"","recordContent":""}
    ],
    "doctorThesisList":[{"title":"Diabetes study","journalName":"KHP","postedYear":"2023"}],
    "doctorBookList":[{"title":"가정의학 교과서"}]
  }
}"""


def test_parse_dept_codes_dedups():
    assert cmc.parse_dept_codes(DEPT_JSON) == ["1", "6"]


def test_parse_doctor_ids_dedups():
    assert cmc.parse_doctor_ids(LIST_JSON) == [("D0001101", "이재호"), ("D0002222", "김철수")]


def test_parse_detail_maps_all_record_types():
    d = cmc.parse_detail(DETAIL_JSON)
    assert d["name"] == "이재호" and d["position"] == "교수" and d["department"] == "가정의학과"
    assert d["specialty"] == ["건강검진", "금연"]
    assert d["education"] == [{"institution": "가톨릭대학교 의학 박사", "year": "1998~2002"}]  # 빈 content 제외
    assert d["career"] == [{"org": "서울성모병원 교수", "period": "2011~현재"}]
    assert d["training"] == [{"org": "Baylor College", "period": "2005~2006"}]
    assert d["societies"] == ["2006~현재 일차의료연구회 회장"]
    assert d["awards"] == ["2012~ 우수논문상"]
    assert d["research"] == ["일차의료 연구"]
    assert d["publications"] == ["Diabetes study (KHP, 2023)", "가정의학 교과서"]


def test_to_doctor_builds_full_model():
    d = cmc.to_doctor(cmc.parse_detail(DETAIL_JSON), hospital="가톨릭대학교 서울성모병원", base_url="https://x", crawled_at="2026-07-21T00:00:00+00:00")
    assert isinstance(d, Doctor)
    assert d.name == "이재호"
    assert d.career[0].org == "서울성모병원 교수"
    assert d.training[0].org == "Baylor College"
    assert d.awards == ["2012~ 우수논문상"]
    assert "dr-D0001101" in d.profile_url


def test_iter_doctor_details_fetches_detail_and_dedups():
    def fake_fetch(url):
        if "/api/department" in url:
            return DEPT_JSON
        if "/api/doctor?" in url:
            return LIST_JSON
        return DETAIL_JSON  # detail endpoint

    details = list(cmc.iter_doctor_details(fake_fetch, "https://x", max_depts=1, max_per_dept=1))
    assert len(details) == 1
    assert details[0]["name"] == "이재호"
    assert details[0]["career"]
