from doctor_cv.adapters import cmc
from doctor_cv.models import Doctor

DEPT_JSON = """[
  {"deptCd":"1","deptNm":"가정의학과","deptClsf":"A"},
  {"deptCd":"6","deptNm":"간담췌외과","deptClsf":"A"},
  {"deptCd":"1","deptNm":"중복","deptClsf":"A"}
]"""

DOCTOR_JSON = """[
  {"drNo":"D0001101","drName":"이재호","nuHptlJobTitle":"교수",
   "doctorDept":{"deptNm":"가정의학과","nuSpecial":"건강검진, 만성질환관리 , 금연"}},
  {"drNo":"D0002222","drName":"김철수","nuHptlJobTitle":"임상과장",
   "doctorDept":{"deptNm":"가정의학과","nuSpecial":""}},
  {"drNo":"D0002222","drName":"김철수중복","nuHptlJobTitle":"교수",
   "doctorDept":{"deptNm":"가정의학과"}}
]"""


def test_parse_dept_codes_dedups():
    assert cmc.parse_dept_codes(DEPT_JSON) == ["1", "6"]


def test_parse_doctors_maps_fields_and_splits_specialty():
    docs = cmc.parse_doctors(DOCTOR_JSON)
    assert docs[0]["name"] == "이재호"
    assert docs[0]["position"] == "교수"
    assert docs[0]["department"] == "가정의학과"
    assert docs[0]["specialty"] == ["건강검진", "만성질환관리", "금연"]
    assert docs[1]["specialty"] == []


def test_to_doctor_builds_model_with_unique_url():
    rec = cmc.parse_doctors(DOCTOR_JSON)[0]
    d = cmc.to_doctor(rec, hospital="가톨릭대학교 서울성모병원", base_url="https://x", crawled_at="2026-07-21T00:00:00+00:00")
    assert isinstance(d, Doctor)
    assert d.name == "이재호"
    assert "dr-D0001101" in d.profile_url  # drNo로 고유 URL


def test_iter_doctors_dedups_by_drno_and_respects_limits():
    def fake_fetch(url):
        if "/api/department" in url:
            return DEPT_JSON
        return DOCTOR_JSON

    # 진료과 2개지만 각 dept가 같은 2명 반환 → 병원 내 drNo dedup으로 2명.
    recs = list(cmc.iter_doctors(fake_fetch, "https://x"))
    assert len(recs) == 2
    drnos = {r["drNo"] for r in recs}
    assert drnos == {"D0001101", "D0002222"}

    limited = list(cmc.iter_doctors(fake_fetch, "https://x", max_depts=1, max_per_dept=1))
    assert len(limited) == 1
