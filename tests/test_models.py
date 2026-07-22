from doctor_cv.models import Doctor, Hospital, EducationItem


def test_doctor_minimal_valid():
    d = Doctor(
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        name="홍길동",
        source_url="https://www.amc.seoul.kr/doctor/1",
        crawled_at="2026-07-20T00:00:00+00:00",
    )
    assert d.name == "홍길동"
    assert d.specialty == []
    assert d.education == []


def test_doctor_with_nested_items():
    d = Doctor(
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        name="홍길동",
        education=[{"institution": "서울대학교 의과대학", "degree": "의학박사", "year": "2005"}],
        source_url="https://www.amc.seoul.kr/doctor/1",
        crawled_at="2026-07-20T00:00:00+00:00",
    )
    assert isinstance(d.education[0], EducationItem)
    assert d.education[0].institution == "서울대학교 의과대학"


def test_hospital_model():
    h = Hospital(
        id="amc",
        name="서울아산병원",
        base_url="https://www.amc.seoul.kr",
        doctor_index_url="https://www.amc.seoul.kr/asan/depts/doctor.do",
    )
    assert h.id == "amc"
