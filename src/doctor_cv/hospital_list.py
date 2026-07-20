from __future__ import annotations

from pathlib import Path

import yaml

from .models import Hospital


def load_hospitals(path: str | Path) -> list[Hospital]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [Hospital(**item) for item in data["hospitals"]]
