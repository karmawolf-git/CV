from doctor_cv import registry


def test_get_adapter_exact_and_partial():
    assert registry.get_adapter("서울아산병원") is not None
    assert registry.get_adapter("삼성서울병원") is not None
    assert registry.get_adapter("분당서울대학교병원") is not None


def test_has_adapter_false_for_unknown():
    assert registry.has_adapter("아무개병원") is False


def test_partial_match():
    # 카탈로그 표기가 살짝 달라도 부분일치로 잡힌다.
    assert registry.get_adapter("서울아산병원 본원") is not None
