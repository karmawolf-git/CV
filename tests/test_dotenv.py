from doctor_cv.dotenv import load_env_file


def test_loads_key_value_and_skips_comments(tmp_path, monkeypatch):
    monkeypatch.delenv("DOCTOR_CV_TESTKEY", raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\nDOCTOR_CV_TESTKEY=abc123\nBAD LINE NO EQUALS\n",
        encoding="utf-8",
    )
    loaded = load_env_file(env)
    assert "DOCTOR_CV_TESTKEY" in loaded
    import os

    assert os.environ["DOCTOR_CV_TESTKEY"] == "abc123"


def test_does_not_overwrite_existing_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCTOR_CV_TESTKEY", "already")
    env = tmp_path / ".env"
    env.write_text("DOCTOR_CV_TESTKEY=fromfile\n", encoding="utf-8")
    loaded = load_env_file(env)
    import os

    assert os.environ["DOCTOR_CV_TESTKEY"] == "already"
    assert "DOCTOR_CV_TESTKEY" not in loaded


def test_strips_surrounding_quotes(tmp_path, monkeypatch):
    monkeypatch.delenv("DOCTOR_CV_TESTKEY", raising=False)
    env = tmp_path / ".env"
    env.write_text('DOCTOR_CV_TESTKEY="q u o t e d"\n', encoding="utf-8")
    load_env_file(env)
    import os

    assert os.environ["DOCTOR_CV_TESTKEY"] == "q u o t e d"


def test_missing_file_returns_empty(tmp_path):
    assert load_env_file(tmp_path / "nope.env") == []
