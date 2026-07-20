from doctor_cv.cli import run_pipeline
from doctor_cv.models import Doctor, Hospital


def test_run_pipeline_isolates_hospital_failures(tmp_path):
    hospitals = [
        Hospital(id="ok", name="정상병원", base_url="https://ok.com", doctor_index_url="https://ok.com/list"),
        Hospital(id="bad", name="실패병원", base_url="https://bad.com", doctor_index_url="https://bad.com/list"),
    ]

    def fake_fetch(url, **kwargs):
        if "bad.com" in url:
            raise RuntimeError("network down")
        return "<html>index</html>"

    def fake_discover(html, base_url):
        return [base_url + "/doctor/1"]

    def fake_extract(html, *, hospital, hospital_url, source_url, crawled_at, **kwargs):
        return Doctor(
            hospital=hospital,
            hospital_url=hospital_url,
            name="홍길동",
            source_url=source_url,
            crawled_at=crawled_at,
        )

    out = tmp_path / "doctors.json"
    summary = run_pipeline(
        hospitals,
        out_path=out,
        fetch=fake_fetch,
        discover=fake_discover,
        extract=fake_extract,
        now="2026-07-20T00:00:00+00:00",
    )
    assert summary["ok"]["doctors"] == 1
    assert summary["bad"]["error"] is not None
    assert out.exists()
