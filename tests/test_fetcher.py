from doctor_cv.fetcher import DEFAULT_UA, Fetcher, looks_unrendered


def test_default_user_agent_is_ascii():
    # httpx는 헤더 값이 ASCII로 인코딩 가능해야 한다(비ASCII면 UnicodeEncodeError).
    DEFAULT_UA.encode("ascii")


def test_looks_unrendered_detects_empty_body():
    assert looks_unrendered("<html><body></body></html>") is True


def test_looks_unrendered_false_for_rich_content():
    html = "<html><body>" + ("<p>내용</p>" * 50) + "</body></html>"
    assert looks_unrendered(html) is False


def test_looks_unrendered_false_for_xml_without_body():
    # XML/JSON ajax 응답(<body> 없음)은 렌더 대상이 아님 → 폴백하지 않는다.
    xml = "<data><DEPT><TP>H</TP><DPCD>CCC</DPCD></DEPT></data>"
    assert looks_unrendered(xml) is False


def test_fetch_uses_cache_when_present(tmp_path):
    f = Fetcher(cache_dir=tmp_path, min_delay=0.0)
    url = "https://ex.com/doctor/1"
    # 캐시를 미리 채운다
    cache_path = f.cache_path(url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("<html>CACHED</html>", encoding="utf-8")

    calls = {"static": 0}

    def fake_static(u):
        calls["static"] += 1
        return "<html>NETWORK</html>"

    html = f.fetch(url, static_getter=fake_static, dynamic_getter=None, check_robots=False)
    assert "CACHED" in html
    assert calls["static"] == 0  # 네트워크 미접근


def test_fetch_falls_back_to_dynamic(tmp_path):
    f = Fetcher(cache_dir=tmp_path, min_delay=0.0)
    calls = {"dynamic": 0}

    def fake_static(u):
        return "<html><body></body></html>"  # 비어 보임 → 폴백 유발

    def fake_dynamic(u):
        calls["dynamic"] += 1
        return "<html><body>" + ("<p>x</p>" * 50) + "</body></html>"

    html = f.fetch(
        "https://ex.com/2",
        static_getter=fake_static,
        dynamic_getter=fake_dynamic,
        check_robots=False,
    )
    assert calls["dynamic"] == 1
    assert "<p>x</p>" in html
