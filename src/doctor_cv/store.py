from __future__ import annotations

import json
from pathlib import Path

from .models import Doctor


def dedup(doctors: list[Doctor]) -> list[Doctor]:
    seen: set[tuple[str, str | None]] = set()
    result: list[Doctor] = []
    for d in doctors:
        key = (d.name, d.profile_url)
        if key not in seen:
            seen.add(key)
            result.append(d)
    return result


def save_doctors(doctors: list[Doctor], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [d.model_dump() for d in doctors]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
