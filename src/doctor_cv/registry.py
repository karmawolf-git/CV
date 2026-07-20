"""구현된 병원 어댑터 레지스트리.

카탈로그(전체 병원 목록) 중 실제로 수집 가능한 병원은 어댑터가 구현된 곳뿐이다.
병원명으로 어댑터를 조회한다.
"""
from __future__ import annotations

from .adapters import amc, smc, snubh

# 병원명 -> 어댑터 모듈. 카탈로그의 요양기관명과 매칭한다.
ADAPTERS = {
    amc.HOSPITAL_NAME: amc,      # 서울아산병원
    smc.HOSPITAL_NAME: smc,      # 삼성서울병원
    snubh.HOSPITAL_NAME: snubh,  # 분당서울대학교병원
}


def get_adapter(hospital_name: str):
    """정확 일치 우선, 없으면 부분일치로 어댑터를 찾는다. 없으면 None."""
    if hospital_name in ADAPTERS:
        return ADAPTERS[hospital_name]
    for name, mod in ADAPTERS.items():
        if name in hospital_name or hospital_name in name:
            return mod
    return None


def has_adapter(hospital_name: str) -> bool:
    return get_adapter(hospital_name) is not None
