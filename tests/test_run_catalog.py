from doctor_cv.run_catalog import annotate, summarize


def test_annotate_and_summarize():
    catalog = [
        {"name": "서울아산병원", "homepage": "https://www.amc.seoul.kr"},
        {"name": "튼튼종합병원", "homepage": "http://ttt.example"},
        {"name": "무명종합병원", "homepage": ""},
    ]
    annotate(catalog)
    assert catalog[0]["has_adapter"] is True   # amc 어댑터 있음
    assert catalog[1]["has_adapter"] is False
    s = summarize(catalog)
    assert s["total"] == 3
    assert s["with_homepage"] == 2
    assert s["with_adapter"] == 1
    assert s["adapter_hospitals"] == ["서울아산병원"]
