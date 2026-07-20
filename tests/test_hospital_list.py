from pathlib import Path

from doctor_cv.hospital_list import load_hospitals


def test_load_hospitals(tmp_path):
    yaml_text = """
hospitals:
  - id: amc
    name: 서울아산병원
    base_url: https://www.amc.seoul.kr
    doctor_index_url: https://www.amc.seoul.kr/list
"""
    p = tmp_path / "hospitals.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    hospitals = load_hospitals(p)
    assert len(hospitals) == 1
    assert hospitals[0].id == "amc"
    assert hospitals[0].name == "서울아산병원"


def test_real_hospitals_yaml_has_big5():
    hospitals = load_hospitals(Path("hospitals.yaml"))
    ids = {h.id for h in hospitals}
    assert ids == {"amc", "smc", "severance", "snuh", "snubh"}
