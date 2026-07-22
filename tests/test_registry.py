from doctor_cv import registry


def test_get_adapter_exact_and_partial():
    assert registry.get_adapter("서울아산병원") is not None
    assert registry.get_adapter("삼성서울병원") is not None
    assert registry.get_adapter("분당서울대학교병원") is not None


def test_has_adapter_false_for_unknown():
    assert registry.has_adapter("아무개병원") is False


def test_partial_match_longer_official_name():
    # 공공데이터 요양기관명은 표준명보다 길다 → 어댑터명이 포함되면 매칭.
    assert registry.get_adapter("재단법인아산사회복지재단 서울아산병원") is not None


def test_no_false_match_for_snuh():
    # '서울대학교병원'(SNUH, 제외 대상)이 '분당서울대학교병원' 어댑터에 오매칭되면 안 됨.
    assert registry.get_adapter("서울대학교병원") is None
