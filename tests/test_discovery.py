from pathlib import Path

from doctor_cv.discovery import find_profile_urls

FIXTURE = Path("tests/fixtures/doctor_index_sample.html").read_text(encoding="utf-8")


def test_finds_profile_links_absolute():
    urls = find_profile_urls(FIXTURE, base_url="https://ex.com")
    assert "https://ex.com/doctor/view.do?id=1" in urls
    assert "https://ex.com/doctor/view.do?id=2" in urls


def test_excludes_non_profile_links():
    urls = find_profile_urls(FIXTURE, base_url="https://ex.com")
    assert all("notice" not in u for u in urls)
    assert all(u != "https://ex.com/home" for u in urls)


def test_dedups_preserving_order():
    urls = find_profile_urls(FIXTURE, base_url="https://ex.com")
    assert len(urls) == len(set(urls))
