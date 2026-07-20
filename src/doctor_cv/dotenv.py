"""아주 작은 .env 로더 (외부 의존성 없음).

`KEY=VALUE` 형식의 줄을 읽어 os.environ에 채운다. **기존 환경변수는 덮어쓰지 않는다.**
빈 줄과 `#` 주석은 무시하고, 값의 양쪽 따옴표는 벗겨낸다. `.env`는 gitignore 되어 있어
비밀 값이 저장소에 커밋되지 않는다.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> list[str]:
    """.env 파일을 os.environ에 로드하고, 새로 설정한 키 목록을 반환한다."""
    p = Path(path)
    if not p.exists():
        return []
    loaded: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return loaded
