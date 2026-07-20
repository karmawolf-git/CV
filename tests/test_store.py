import json

from doctor_cv.models import Doctor
from doctor_cv.store import dedup, save_doctors


def _doc(name, url):
    return Doctor(
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        name=name,
        profile_url=url,
        source_url=url,
        crawled_at="2026-07-20T00:00:00+00:00",
    )


def test_dedup_by_name_and_profile_url():
    docs = [_doc("홍길동", "u1"), _doc("홍길동", "u1"), _doc("김철수", "u2")]
    result = dedup(docs)
    assert len(result) == 2


def test_save_doctors_writes_json(tmp_path):
    out = tmp_path / "doctors.json"
    save_doctors([_doc("홍길동", "u1")], out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["name"] == "홍길동"
    assert data[0]["hospital"] == "서울아산병원"
