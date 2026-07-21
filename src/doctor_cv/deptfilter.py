"""진료과 이름 필터 (부분일치). 병원마다 표기가 달라도 부분문자열로 매칭한다."""
from __future__ import annotations


def dept_matches(name: str | None, filters: list[str] | None) -> bool:
    """filters가 비어 있으면 전체 허용. 아니면 name에 필터 문자열이 하나라도 포함되면 True."""
    if not filters:
        return True
    n = name or ""
    return any(f in n for f in filters)


def parse_depts_arg(arg: str | None) -> list[str] | None:
    """CLI --depts "가정의학과,내과" 를 리스트로. 비면 None(전체)."""
    if not arg:
        return None
    items = [x.strip() for x in arg.split(",") if x.strip()]
    return items or None
