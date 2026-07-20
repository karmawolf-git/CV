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
    """정확 일치 우선, 없으면 '어댑터 표준명이 카탈로그명에 포함'될 때만 매칭한다.

    공공데이터 요양기관명은 표준명보다 긴 경우가 많다(예: '재단법인아산사회복지재단
    서울아산병원'). 반대 방향(카탈로그명 ⊂ 표준명)은 오매칭을 부르므로 쓰지 않는다
    (예: '서울대학교병원'이 '분당서울대학교병원'의 부분문자열).
    """
    if hospital_name in ADAPTERS:
        return ADAPTERS[hospital_name]
    for name, mod in ADAPTERS.items():
        if name in hospital_name:
            return mod
    return None


def has_adapter(hospital_name: str) -> bool:
    return get_adapter(hospital_name) is not None
