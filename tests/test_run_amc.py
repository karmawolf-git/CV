from doctor_cv.adapters import amc
from doctor_cv.models import Doctor
from doctor_cv.run_amc import crawl_amc

INDEX_HTML = "<a onclick=\"fnSelectDeptPopup('D001');\">가정의학과</a>"
LIST_HTML = (
    "<a onclick=\"fnDrDetail('EMP_A','D001');\"></a>"
    "<a onclick=\"fnDrDetail('EMP_B','D001');\"></a>"
)


def _make_fetch(fail_urls=()):
    def fetch(url):
        if url in fail_urls:
            raise RuntimeError("boom")
        if url == amc.dept_index_url():
            return INDEX_HTML
        if amc.LIST_PATH in url and "drEmpId=&" in url + "&":
            return LIST_HTML
        return LIST_HTML if url == amc.list_url("D001") else "<html>detail</html>"

    return fetch


def _fake_extract(html, *, hospital, hospital_url, source_url, crawled_at):
    return Doctor(
        hospital=hospital,
        hospital_url=hospital_url,
        name="의사",
        profile_url=source_url,
        source_url=source_url,
        crawled_at=crawled_at,
    )


def test_crawl_amc_collects_doctors():
    doctors, errors = crawl_amc(
        _make_fetch(), _fake_extract, now="2026-07-21T00:00:00+00:00"
    )
    assert len(doctors) == 2
    assert errors == []


def test_crawl_amc_isolates_detail_failure():
    # EMP_A의 탭 하나라도 실패하면 그 의사만 건너뛴다.
    fail = {amc.detail_tab_urls("EMP_A", "D001")[0]}
    doctors, errors = crawl_amc(
        _make_fetch(fail_urls=fail), _fake_extract, now="2026-07-21T00:00:00+00:00"
    )
    assert len(doctors) == 1  # EMP_B만 성공
    assert len(errors) == 1
