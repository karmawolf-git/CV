# 의료진 경력 크롤러 + 웹 뷰어 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 빅5 병원 홈페이지의 공개 의료진 경력을 크롤링·LLM 추출하여 JSON으로 저장하고 정적 웹 뷰어로 검색·열람하는 파이프라인을 완성한다 (Phase 1 수직 슬라이스).

**Architecture:** `hospitals.yaml`에서 대상 병원을 읽어 → 의료진 목록 페이지에서 프로필 URL 탐색(discovery) → 정적/Playwright로 HTML 수집·캐시(fetcher) → Claude 도구호출로 구조화 추출(extractor) → pydantic 검증 후 정규화·중복제거하여 `data/doctors.json` 저장(store) → 정적 웹 뷰어가 이를 읽어 렌더링. 각 모듈은 독립·테스트 가능하며 CLI가 순서대로 오케스트레이션한다.

**Tech Stack:** Python 3.11+, httpx, Playwright(Chromium), BeautifulSoup4, anthropic SDK, pydantic v2, PyYAML, pytest. 뷰어는 프레임워크 없는 정적 HTML/CSS/JS.

**환경 참고 (Windows):** 기본 shell은 PowerShell. 이 머신에는 실제 Python이 없고 `python.exe`는 Microsoft Store 스텁이므로, Task 1에서 winget으로 실제 Python을 설치한다. 이후 모든 명령은 venv 파이썬(`.venv\Scripts\python.exe`)을 직접 호출한다.

---

### Task 1: 환경 부트스트랩 & 프로젝트 스캐폴드

**Files:**
- Create: `C:\Workspace\CV\pyproject.toml`
- Create: `C:\Workspace\CV\.gitignore`
- Create: `C:\Workspace\CV\src\doctor_cv\__init__.py`
- Create: `C:\Workspace\CV\tests\__init__.py`
- Create: `C:\Workspace\CV\tests\test_smoke.py`

- [ ] **Step 1: 실제 Python 설치 (winget, 사용자 범위)**

Run (PowerShell):
```powershell
winget install --id Python.Python.3.12 --source winget --scope user --accept-source-agreements --accept-package-agreements --silent
```
Expected: "설치 성공" / "Successfully installed". 이미 있으면 그 메시지.

- [ ] **Step 2: 새 셸에서 Python 확인**

Run (PowerShell, 새 세션):
```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"; & $py --version
```
Expected: `Python 3.12.x`
(경로가 다르면 `Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Directory` 로 확인)

- [ ] **Step 3: 가상환경 생성**

Run:
```powershell
cd C:\Workspace\CV; & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
```
Expected: `.venv\` 디렉터리 생성, 출력 없음.

- [ ] **Step 4: `.gitignore` 작성**

```
.venv/
__pycache__/
*.pyc
cache/
.env
.pytest_cache/
```

- [ ] **Step 5: `pyproject.toml` 작성**

```toml
[project]
name = "doctor-cv"
version = "0.1.0"
description = "의료진 경력 크롤러 + 웹 뷰어 (Phase 1)"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "anthropic>=0.40",
    "playwright>=1.44",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 6: 의존성 설치**

Run:
```powershell
cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pip install --upgrade pip; .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
Expected: `Successfully installed ... anthropic ... pydantic ... pytest ...`

- [ ] **Step 7: Playwright 브라우저 설치**

Run:
```powershell
cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m playwright install chromium
```
Expected: Chromium 다운로드 완료 메시지.

- [ ] **Step 8: 패키지 초기화 파일 작성**

`src\doctor_cv\__init__.py`:
```python
"""의료진 경력 크롤러 (Phase 1)."""
```
`tests\__init__.py`: (빈 파일)

- [ ] **Step 9: 스모크 테스트 작성**

`tests\test_smoke.py`:
```python
def test_package_imports():
    import doctor_cv
    assert doctor_cv is not None
```

- [ ] **Step 10: 테스트 실행 (통과 확인)**

Run:
```powershell
cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_smoke.py -v
```
Expected: `1 passed`

- [ ] **Step 11: 커밋**

```powershell
cd C:\Workspace\CV; git add pyproject.toml .gitignore src tests; git commit -m "chore: bootstrap python project scaffold"
```

---

### Task 2: 데이터 모델 (pydantic 스키마)

**Files:**
- Create: `src\doctor_cv\models.py`
- Test: `tests\test_models.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests\test_models.py`:
```python
from doctor_cv.models import Doctor, Hospital, EducationItem


def test_doctor_minimal_valid():
    d = Doctor(
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        name="홍길동",
        source_url="https://www.amc.seoul.kr/doctor/1",
        crawled_at="2026-07-20T00:00:00+00:00",
    )
    assert d.name == "홍길동"
    assert d.specialty == []
    assert d.education == []


def test_doctor_with_nested_items():
    d = Doctor(
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        name="홍길동",
        education=[{"institution": "서울대학교 의과대학", "degree": "의학박사", "year": "2005"}],
        source_url="https://www.amc.seoul.kr/doctor/1",
        crawled_at="2026-07-20T00:00:00+00:00",
    )
    assert isinstance(d.education[0], EducationItem)
    assert d.education[0].institution == "서울대학교 의과대학"


def test_hospital_model():
    h = Hospital(
        id="amc",
        name="서울아산병원",
        base_url="https://www.amc.seoul.kr",
        doctor_index_url="https://www.amc.seoul.kr/asan/depts/doctor.do",
    )
    assert h.id == "amc"
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.models'`

- [ ] **Step 3: 모델 구현**

`src\doctor_cv\models.py`:
```python
from __future__ import annotations

from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    institution: str
    degree: str | None = None
    year: str | None = None


class LicenseItem(BaseModel):
    name: str
    year: str | None = None


class CareerItem(BaseModel):
    org: str
    role: str | None = None
    period: str | None = None


class Doctor(BaseModel):
    hospital: str
    hospital_url: str
    name: str
    position: str | None = None
    department: str | None = None
    specialty: list[str] = Field(default_factory=list)
    profile_url: str | None = None
    photo_url: str | None = None
    education: list[EducationItem] = Field(default_factory=list)
    licenses: list[LicenseItem] = Field(default_factory=list)
    career: list[CareerItem] = Field(default_factory=list)
    societies: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    source_url: str
    crawled_at: str


class Hospital(BaseModel):
    id: str
    name: str
    base_url: str
    doctor_index_url: str
    notes: str | None = None
```

- [ ] **Step 4: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_models.py -v`
Expected: `3 passed`

- [ ] **Step 5: 커밋**

```powershell
cd C:\Workspace\CV; git add src\doctor_cv\models.py tests\test_models.py; git commit -m "feat: add pydantic data models"
```

---

### Task 3: 병원 목록 로더 + hospitals.yaml (빅5)

**Files:**
- Create: `hospitals.yaml`
- Create: `src\doctor_cv\hospital_list.py`
- Test: `tests\test_hospital_list.py`

- [ ] **Step 1: `hospitals.yaml` 작성 (빅5)**

> `doctor_index_url`은 각 병원의 의료진 목록 진입 페이지다. 실제 값은 Task 8 통합 실행 시
> 브라우저로 확인·보정한다. 아래는 초기 시드값이며, 잘못되면 `notes`에 실제 경로를 기록한다.

`hospitals.yaml`:
```yaml
hospitals:
  - id: amc
    name: 서울아산병원
    base_url: https://www.amc.seoul.kr
    doctor_index_url: https://www.amc.seoul.kr/asan/depts/deptSearch.do?menuId=110
    notes: JS 렌더링 가능성 높음
  - id: smc
    name: 삼성서울병원
    base_url: https://www.samsunghospital.com
    doctor_index_url: https://www.samsunghospital.com/home/reservation/doctorList.do
    notes: JS 렌더링 가능성 높음
  - id: severance
    name: 세브란스병원
    base_url: https://sev.severance.healthcare
    doctor_index_url: https://sev.severance.healthcare/sev/doctor/doctor-list.do
    notes: JS 렌더링 가능성 높음
  - id: snuh
    name: 서울대학교병원
    base_url: https://www.snuh.org
    doctor_index_url: https://www.snuh.org/reservation/reservDoctor.do
    notes: JS 렌더링 가능성 높음
  - id: snubh
    name: 분당서울대학교병원
    base_url: https://www.snubh.org
    doctor_index_url: https://www.snubh.org/medical/drIntroList.do
    notes: JS 렌더링 가능성 높음
```

- [ ] **Step 2: 실패 테스트 작성**

`tests\test_hospital_list.py`:
```python
from pathlib import Path

from doctor_cv.hospital_list import load_hospitals


def test_load_hospitals(tmp_path):
    yaml_text = """
hospitals:
  - id: amc
    name: 서울아산병원
    base_url: https://www.amc.seoul.kr
    doctor_index_url: https://www.amc.seoul.kr/list
"""
    p = tmp_path / "hospitals.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    hospitals = load_hospitals(p)
    assert len(hospitals) == 1
    assert hospitals[0].id == "amc"
    assert hospitals[0].name == "서울아산병원"


def test_real_hospitals_yaml_has_big5():
    hospitals = load_hospitals(Path("hospitals.yaml"))
    ids = {h.id for h in hospitals}
    assert ids == {"amc", "smc", "severance", "snuh", "snubh"}
```

- [ ] **Step 3: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_hospital_list.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.hospital_list'`

- [ ] **Step 4: 구현**

`src\doctor_cv\hospital_list.py`:
```python
from __future__ import annotations

from pathlib import Path

import yaml

from .models import Hospital


def load_hospitals(path: str | Path) -> list[Hospital]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [Hospital(**item) for item in data["hospitals"]]
```

- [ ] **Step 5: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_hospital_list.py -v`
Expected: `2 passed`

- [ ] **Step 6: 커밋**

```powershell
cd C:\Workspace\CV; git add hospitals.yaml src\doctor_cv\hospital_list.py tests\test_hospital_list.py; git commit -m "feat: add hospital list loader and big5 seed"
```

---

### Task 4: 프로필 URL 탐색 (discovery)

**Files:**
- Create: `src\doctor_cv\discovery.py`
- Create: `tests\fixtures\doctor_index_sample.html`
- Test: `tests\test_discovery.py`

- [ ] **Step 1: 픽스처 HTML 작성**

`tests\fixtures\doctor_index_sample.html`:
```html
<html><body>
  <nav><a href="/home">홈</a></nav>
  <ul class="doctor-list">
    <li><a href="/doctor/view.do?id=1">홍길동 교수</a></li>
    <li><a href="/doctor/view.do?id=2">김철수 의료진</a></li>
    <li><a href="doctor/view.do?id=2">김철수 중복</a></li>
  </ul>
  <a href="/notice/list">공지사항</a>
</body></html>
```

- [ ] **Step 2: 실패 테스트 작성**

`tests\test_discovery.py`:
```python
from pathlib import Path

from doctor_cv.discovery import find_profile_urls

FIXTURE = Path("tests/fixtures/doctor_index_sample.html").read_text(encoding="utf-8")


def test_finds_profile_links_absolute():
    urls = find_profile_urls(FIXTURE, base_url="https://ex.com")
    assert "https://ex.com/doctor/view.do?id=1" in urls
    assert "https://ex.com/doctor/view.do?id=2" in urls


def test_excludes_non_profile_links():
    urls = find_profile_urls(FIXTURE, base_url="https://ex.com")
    assert all("notice" not in u for u in urls)
    assert all(u != "https://ex.com/home" for u in urls)


def test_dedups_preserving_order():
    urls = find_profile_urls(FIXTURE, base_url="https://ex.com")
    assert len(urls) == len(set(urls))
```

- [ ] **Step 3: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.discovery'`

- [ ] **Step 4: 구현**

`src\doctor_cv\discovery.py`:
```python
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

PROFILE_HINTS = ("의료진", "교수", "전문의", "doctor", "staff", "profile", "physician")


def find_profile_urls(html: str, base_url: str) -> list[str]:
    """의료진 목록 HTML에서 개별 프로필 링크를 휴리스틱으로 추출한다."""
    soup = BeautifulSoup(html, "html.parser")
    result: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        haystack = f"{href} {text}".lower()
        if not any(hint.lower() in haystack for hint in PROFILE_HINTS):
            continue
        absolute = urljoin(base_url + "/", href)
        if absolute not in seen:
            seen.add(absolute)
            result.append(absolute)
    return result
```

- [ ] **Step 5: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_discovery.py -v`
Expected: `3 passed`

- [ ] **Step 6: 커밋**

```powershell
cd C:\Workspace\CV; git add src\doctor_cv\discovery.py tests\test_discovery.py tests\fixtures\doctor_index_sample.html; git commit -m "feat: add profile URL discovery heuristic"
```

---

### Task 5: 페이지 수집기 (fetcher) — 정적/Playwright 폴백 + robots + 캐시

**Files:**
- Create: `src\doctor_cv\fetcher.py`
- Test: `tests\test_fetcher.py`

- [ ] **Step 1: 실패 테스트 작성 (캐시 + 폴백 판단 로직)**

`tests\test_fetcher.py`:
```python
from doctor_cv.fetcher import Fetcher, looks_unrendered


def test_looks_unrendered_detects_empty_body():
    assert looks_unrendered("<html><body></body></html>") is True


def test_looks_unrendered_false_for_rich_content():
    html = "<html><body>" + ("<p>내용</p>" * 50) + "</body></html>"
    assert looks_unrendered(html) is False


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
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.fetcher'`

- [ ] **Step 3: 구현**

`src\doctor_cv\fetcher.py`:
```python
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_UA = "DoctorCV-Research-Crawler/0.1 (+공개 의료진 정보 수집; 연구용)"


def looks_unrendered(html: str) -> bool:
    """본문이 비어 있거나 지나치게 짧으면 JS 렌더링이 필요하다고 판단."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    text = body.get_text(strip=True) if body else ""
    return len(text) < 100


class Fetcher:
    def __init__(self, cache_dir: str | Path, user_agent: str = DEFAULT_UA, min_delay: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent
        self.min_delay = min_delay
        self._robots: dict[str, RobotFileParser] = {}
        self._last_request = 0.0

    def cache_path(self, url: str) -> Path:
        host = urlparse(url).netloc
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / host / f"{digest}.html"

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._robots:
            rp = RobotFileParser()
            rp.set_url(urljoin(root, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                # robots.txt 접근 불가 시 보수적으로 허용하지 않음이 안전하나,
                # 공개 페이지 대상이므로 여기서는 허용으로 처리하고 로그는 호출측에서.
                self._robots[root] = None  # type: ignore[assignment]
                return True
            self._robots[root] = rp
        rp = self._robots[root]
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request = time.monotonic()

    def _default_static(self, url: str) -> str:
        self._throttle()
        resp = httpx.get(url, headers={"User-Agent": self.user_agent}, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    def _default_dynamic(self, url: str) -> str:
        from playwright.sync_api import sync_playwright

        self._throttle()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=self.user_agent)
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
        return html

    def fetch(self, url: str, static_getter=None, dynamic_getter=None, check_robots: bool = True) -> str:
        cache = self.cache_path(url)
        if cache.exists():
            return cache.read_text(encoding="utf-8")

        if check_robots and not self.allowed(url):
            raise PermissionError(f"robots.txt disallows: {url}")

        static_getter = static_getter or self._default_static
        html = static_getter(url)

        if looks_unrendered(html):
            dyn = dynamic_getter if dynamic_getter is not None else self._default_dynamic
            if dyn is not None:
                html = dyn(url)

        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(html, encoding="utf-8")
        return html
```

- [ ] **Step 4: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_fetcher.py -v`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```powershell
cd C:\Workspace\CV; git add src\doctor_cv\fetcher.py tests\test_fetcher.py; git commit -m "feat: add fetcher with cache, robots, playwright fallback"
```

---

### Task 6: LLM 추출기 (extractor) — Claude 도구호출

**Files:**
- Create: `src\doctor_cv\extractor.py`
- Test: `tests\test_extractor.py`

- [ ] **Step 1: 실패 테스트 작성 (client 주입 모킹)**

`tests\test_extractor.py`:
```python
from types import SimpleNamespace

from doctor_cv.extractor import clean_html, extract_doctor
from doctor_cv.models import Doctor


def test_clean_html_strips_script_and_style():
    html = "<html><head><style>x{}</style></head><body><script>var a=1</script><p>홍길동</p></body></html>"
    cleaned = clean_html(html)
    assert "홍길동" in cleaned
    assert "var a" not in cleaned
    assert "x{}" not in cleaned


class FakeClient:
    """anthropic.Anthropic 대체 — tool_use 블록을 가진 메시지를 반환."""

    def __init__(self, tool_input):
        self._tool_input = tool_input
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        block = SimpleNamespace(type="tool_use", name="record_doctor", input=self._tool_input)
        return SimpleNamespace(content=[block])


def test_extract_doctor_returns_validated_model():
    fake = FakeClient(
        {
            "name": "홍길동",
            "position": "교수",
            "department": "정형외과",
            "specialty": ["척추"],
            "education": [{"institution": "서울대 의대", "degree": "의학박사", "year": "2005"}],
            "licenses": [],
            "career": [{"org": "서울아산병원", "role": "전임의", "period": "2006-2008"}],
            "societies": ["대한정형외과학회"],
            "publications": [],
            "photo_url": None,
        }
    )
    doctor = extract_doctor(
        html="<html><body><p>홍길동 교수 정형외과</p></body></html>",
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        source_url="https://www.amc.seoul.kr/doctor/1",
        crawled_at="2026-07-20T00:00:00+00:00",
        client=fake,
        model="claude-sonnet-5",
    )
    assert isinstance(doctor, Doctor)
    assert doctor.name == "홍길동"
    assert doctor.department == "정형외과"
    assert doctor.career[0].org == "서울아산병원"
    assert doctor.source_url == "https://www.amc.seoul.kr/doctor/1"
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.extractor'`

- [ ] **Step 3: 구현**

`src\doctor_cv\extractor.py`:
```python
from __future__ import annotations

import os

from bs4 import BeautifulSoup

from .models import Doctor

DEFAULT_MODEL = os.environ.get("DOCTOR_CV_MODEL", "claude-sonnet-5")

EXTRACT_TOOL = {
    "name": "record_doctor",
    "description": "의료진 소개 페이지에서 한 명의 의사 경력 정보를 구조화하여 기록한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "의사 이름"},
            "position": {"type": ["string", "null"], "description": "직위 (예: 교수, 전문의)"},
            "department": {"type": ["string", "null"], "description": "진료과"},
            "specialty": {"type": "array", "items": {"type": "string"}, "description": "전문분야"},
            "photo_url": {"type": ["string", "null"]},
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string"},
                        "degree": {"type": ["string", "null"]},
                        "year": {"type": ["string", "null"]},
                    },
                    "required": ["institution"],
                },
            },
            "licenses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "year": {"type": ["string", "null"]},
                    },
                    "required": ["name"],
                },
            },
            "career": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "org": {"type": "string"},
                        "role": {"type": ["string", "null"]},
                        "period": {"type": ["string", "null"]},
                    },
                    "required": ["org"],
                },
            },
            "societies": {"type": "array", "items": {"type": "string"}},
            "publications": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name"],
    },
}

PROMPT = (
    "다음은 한 병원의 의료진 소개 페이지 텍스트다. 여기서 의사 1명의 경력 정보를 "
    "record_doctor 도구 스키마에 맞춰 추출하라. 페이지에 없는 항목은 빈 배열이나 null로 두고, "
    "지어내지 마라. 개인 연락처는 수집하지 마라.\n\n---\n"
)


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def extract_doctor(
    html: str,
    *,
    hospital: str,
    hospital_url: str,
    source_url: str,
    crawled_at: str,
    client=None,
    model: str | None = None,
) -> Doctor:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    model = model or DEFAULT_MODEL

    content = clean_html(html)
    message = client.messages.create(
        model=model,
        max_tokens=2000,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_doctor"},
        messages=[{"role": "user", "content": PROMPT + content}],
    )
    tool_use = next(b for b in message.content if getattr(b, "type", None) == "tool_use")
    data = dict(tool_use.input)
    data.update(
        hospital=hospital,
        hospital_url=hospital_url,
        source_url=source_url,
        crawled_at=crawled_at,
    )
    return Doctor(**data)
```

- [ ] **Step 4: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_extractor.py -v`
Expected: `2 passed`

- [ ] **Step 5: 커밋**

```powershell
cd C:\Workspace\CV; git add src\doctor_cv\extractor.py tests\test_extractor.py; git commit -m "feat: add Claude tool-use extractor"
```

---

### Task 7: 저장·중복제거 (store)

**Files:**
- Create: `src\doctor_cv\store.py`
- Test: `tests\test_store.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests\test_store.py`:
```python
import json

from doctor_cv.models import Doctor
from doctor_cv.store import dedup, save_doctors


def _doc(name, url):
    return Doctor(
        hospital="서울아산병원",
        hospital_url="https://www.amc.seoul.kr",
        name=name,
        profile_url=url,
        source_url=url,
        crawled_at="2026-07-20T00:00:00+00:00",
    )


def test_dedup_by_name_and_profile_url():
    docs = [_doc("홍길동", "u1"), _doc("홍길동", "u1"), _doc("김철수", "u2")]
    result = dedup(docs)
    assert len(result) == 2


def test_save_doctors_writes_json(tmp_path):
    out = tmp_path / "doctors.json"
    save_doctors([_doc("홍길동", "u1")], out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["name"] == "홍길동"
    assert data[0]["hospital"] == "서울아산병원"
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.store'`

- [ ] **Step 3: 구현**

`src\doctor_cv\store.py`:
```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_store.py -v`
Expected: `2 passed`

- [ ] **Step 5: 커밋**

```powershell
cd C:\Workspace\CV; git add src\doctor_cv\store.py tests\test_store.py; git commit -m "feat: add store with dedup and json output"
```

---

### Task 8: 파이프라인 CLI (오케스트레이션)

**Files:**
- Create: `src\doctor_cv\cli.py`
- Test: `tests\test_cli.py`

- [ ] **Step 1: 실패 테스트 작성 (병원별 격리 + 요약)**

`tests\test_cli.py`:
```python
from doctor_cv.cli import run_pipeline
from doctor_cv.models import Doctor, Hospital


def test_run_pipeline_isolates_hospital_failures(tmp_path):
    hospitals = [
        Hospital(id="ok", name="정상병원", base_url="https://ok.com", doctor_index_url="https://ok.com/list"),
        Hospital(id="bad", name="실패병원", base_url="https://bad.com", doctor_index_url="https://bad.com/list"),
    ]

    def fake_fetch(url, **kwargs):
        if "bad.com" in url:
            raise RuntimeError("network down")
        return "<html>index</html>"

    def fake_discover(html, base_url):
        return [base_url + "/doctor/1"]

    def fake_extract(html, *, hospital, hospital_url, source_url, crawled_at, **kwargs):
        return Doctor(
            hospital=hospital,
            hospital_url=hospital_url,
            name="홍길동",
            source_url=source_url,
            crawled_at=crawled_at,
        )

    out = tmp_path / "doctors.json"
    summary = run_pipeline(
        hospitals,
        out_path=out,
        fetch=fake_fetch,
        discover=fake_discover,
        extract=fake_extract,
        now="2026-07-20T00:00:00+00:00",
    )
    assert summary["ok"]["doctors"] == 1
    assert summary["bad"]["error"] is not None
    assert out.exists()
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'doctor_cv.cli'`

- [ ] **Step 3: 구현**

`src\doctor_cv\cli.py`:
```python
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .discovery import find_profile_urls
from .extractor import extract_doctor
from .fetcher import Fetcher
from .hospital_list import load_hospitals
from .models import Doctor, Hospital
from .store import dedup, save_doctors


def run_pipeline(
    hospitals: list[Hospital],
    *,
    out_path: str | Path,
    fetch,
    discover,
    extract,
    now: str,
) -> dict:
    all_doctors: list[Doctor] = []
    summary: dict = {}
    for h in hospitals:
        try:
            index_html = fetch(h.doctor_index_url)
            profile_urls = discover(index_html, base_url=h.base_url)
            docs: list[Doctor] = []
            for url in profile_urls:
                try:
                    html = fetch(url)
                    doc = extract(
                        html,
                        hospital=h.name,
                        hospital_url=h.base_url,
                        source_url=url,
                        crawled_at=now,
                    )
                    docs.append(doc)
                except Exception as exc:  # noqa: BLE001 - 의사 단위 격리
                    print(f"[WARN] {h.id} 프로필 실패 {url}: {exc}")
            all_doctors.extend(docs)
            summary[h.id] = {"doctors": len(docs), "error": None}
        except Exception as exc:  # noqa: BLE001 - 병원 단위 격리
            summary[h.id] = {"doctors": 0, "error": str(exc)}
            print(f"[ERROR] {h.id} 병원 실패: {exc}")

    save_doctors(dedup(all_doctors), out_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="의료진 경력 크롤러 (Phase 1)")
    parser.add_argument("--hospitals", default="hospitals.yaml")
    parser.add_argument("--out", default="data/doctors.json")
    parser.add_argument("--cache", default="cache")
    parser.add_argument("--min-delay", type=float, default=1.0)
    args = parser.parse_args()

    hospitals = load_hospitals(args.hospitals)
    fetcher = Fetcher(cache_dir=args.cache, min_delay=args.min_delay)
    now = datetime.now(timezone.utc).isoformat()

    summary = run_pipeline(
        hospitals,
        out_path=args.out,
        fetch=lambda url, **kw: fetcher.fetch(url),
        discover=find_profile_urls,
        extract=extract_doctor,
        now=now,
    )
    print("=== 수집 요약 ===")
    for hid, info in summary.items():
        print(f"{hid}: 의사 {info['doctors']}명, 오류={info['error']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest tests\test_cli.py -v`
Expected: `1 passed`

- [ ] **Step 5: 전체 테스트 실행**

Run: `cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m pytest -v`
Expected: 모든 테스트 통과 (13개 내외)

- [ ] **Step 6: 커밋**

```powershell
cd C:\Workspace\CV; git add src\doctor_cv\cli.py tests\test_cli.py; git commit -m "feat: add pipeline CLI with per-hospital isolation"
```

---

### Task 9: 실 사이트 검증 & URL 보정 (수동 통합)

> 이 태스크는 자동 테스트가 아니라 실제 병원 사이트로 파이프라인을 돌려 `hospitals.yaml`의
> `doctor_index_url`과 discovery 휴리스틱을 보정하는 단계다. LLM 호출이 발생하므로
> `ANTHROPIC_API_KEY`가 필요하다.

- [ ] **Step 1: API 키 설정 (셸 세션 한정, 저장소에 저장 금지)**

Run (PowerShell):
```powershell
$env:ANTHROPIC_API_KEY = "<사용자 본인이 직접 입력>"
```
> 키 값은 코드/파일/커밋에 절대 넣지 않는다. 세션 환경변수로만 사용한다.

- [ ] **Step 2: 병원 1곳(분당서울대, snubh)만 우선 실행**

`hospitals.yaml`을 임시로 snubh 1개만 남기거나, 아래로 한 곳만 대상으로 실행:
```powershell
cd C:\Workspace\CV; .\.venv\Scripts\python.exe -m doctor_cv.cli --min-delay 2.0
```
Expected: `data\doctors.json` 생성. 요약에 snubh 의사 수 출력.

- [ ] **Step 3: 결과 점검 및 URL 보정**

- 의사 수가 0이면: `cache\<host>\` 의 캐시 HTML을 열어 목록 페이지가 제대로 왔는지 확인.
- 목록이 비어 있으면 → `doctor_index_url`이 틀렸거나 JS 목록 → 브라우저(개발자도구)로 실제 목록 페이지 URL/구조 확인 후 `hospitals.yaml` 수정.
- discovery가 엉뚱한 링크를 잡으면 → `PROFILE_HINTS` 조정 또는 병원별 `notes`에 정확한 링크 패턴 기록.
- 각 보정 후 `cache\` 를 지우고 재실행하여 확인.

- [ ] **Step 4: 나머지 빅5로 확대 실행**

`hospitals.yaml`을 빅5 전체로 되돌리고 실행:
```powershell
cd C:\Workspace\CV; Remove-Item -Recurse -Force cache -ErrorAction SilentlyContinue; .\.venv\Scripts\python.exe -m doctor_cv.cli --min-delay 2.0
```
Expected: 병원별 요약 출력, `data\doctors.json`에 여러 병원 의사 누적.

- [ ] **Step 5: 커밋 (보정된 설정)**

```powershell
cd C:\Workspace\CV; git add hospitals.yaml src\doctor_cv\discovery.py; git commit -m "chore: calibrate hospital URLs and discovery for big5"
```
> `data\doctors.json`은 산출물이며 커밋 여부는 사용자 판단. 개인정보 포함 가능하므로 기본은 커밋하지 않음(필요 시 `.gitignore`에 `data/` 추가 검토).

---

### Task 10: 정적 웹 뷰어

**Files:**
- Create: `viewer\index.html`
- Create: `viewer\app.js`
- Create: `viewer\sample-doctors.json` (뷰어 단독 확인용 샘플)

- [ ] **Step 1: 샘플 데이터 작성**

`viewer\sample-doctors.json`:
```json
[
  {
    "hospital": "서울아산병원",
    "hospital_url": "https://www.amc.seoul.kr",
    "name": "홍길동",
    "position": "교수",
    "department": "정형외과",
    "specialty": ["척추"],
    "profile_url": "https://www.amc.seoul.kr/doctor/1",
    "photo_url": null,
    "education": [{"institution": "서울대 의대", "degree": "의학박사", "year": "2005"}],
    "licenses": [],
    "career": [{"org": "서울아산병원", "role": "전임의", "period": "2006-2008"}],
    "societies": ["대한정형외과학회"],
    "publications": [],
    "source_url": "https://www.amc.seoul.kr/doctor/1",
    "crawled_at": "2026-07-20T00:00:00+00:00"
  }
]
```

- [ ] **Step 2: `viewer\index.html` 작성**

```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>의료진 경력 뷰어</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #f7f7f8; color: #1a1a1a; }
    h1 { font-size: 1.25rem; }
    .controls { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; }
    input, select { padding: .5rem; font-size: 1rem; border: 1px solid #ccc; border-radius: 6px; }
    .card { background: #fff; border: 1px solid #e2e2e2; border-radius: 10px; padding: 1rem; margin-bottom: .75rem; }
    .card h2 { font-size: 1.05rem; margin: 0 0 .25rem; }
    .meta { color: #555; font-size: .9rem; margin-bottom: .5rem; }
    .section { margin-top: .5rem; }
    .section b { display: block; font-size: .85rem; color: #333; }
    ul { margin: .25rem 0; padding-left: 1.1rem; }
    a { color: #2563eb; }
    .count { color: #666; font-size: .9rem; }
  </style>
</head>
<body>
  <h1>의료진 경력 뷰어</h1>
  <div class="controls">
    <input id="search" type="search" placeholder="이름 검색" />
    <select id="hospital"><option value="">전체 병원</option></select>
    <select id="dept"><option value="">전체 진료과</option></select>
  </div>
  <div class="count" id="count"></div>
  <div id="list"></div>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: `viewer\app.js` 작성**

```javascript
const DATA_URL = new URLSearchParams(location.search).get("data") || "sample-doctors.json";

let doctors = [];

async function load() {
  const res = await fetch(DATA_URL);
  doctors = await res.json();
  initFilters();
  render();
}

function initFilters() {
  const hospitals = [...new Set(doctors.map((d) => d.hospital).filter(Boolean))].sort();
  const depts = [...new Set(doctors.map((d) => d.department).filter(Boolean))].sort();
  fill("hospital", hospitals);
  fill("dept", depts);
  document.getElementById("search").addEventListener("input", render);
  document.getElementById("hospital").addEventListener("change", render);
  document.getElementById("dept").addEventListener("change", render);
}

function fill(id, values) {
  const sel = document.getElementById(id);
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }
}

function render() {
  const q = document.getElementById("search").value.trim();
  const hospital = document.getElementById("hospital").value;
  const dept = document.getElementById("dept").value;
  const filtered = doctors.filter(
    (d) =>
      (!q || (d.name || "").includes(q)) &&
      (!hospital || d.hospital === hospital) &&
      (!dept || d.department === dept)
  );
  document.getElementById("count").textContent = `${filtered.length}명`;
  document.getElementById("list").innerHTML = filtered.map(card).join("");
}

function listBlock(title, items) {
  if (!items || !items.length) return "";
  const lis = items
    .map((it) =>
      typeof it === "string"
        ? `<li>${escapeHtml(it)}</li>`
        : `<li>${escapeHtml([it.institution || it.org || it.name, it.degree || it.role, it.period || it.year].filter(Boolean).join(" · "))}</li>`
    )
    .join("");
  return `<div class="section"><b>${title}</b><ul>${lis}</ul></div>`;
}

function card(d) {
  return `<div class="card">
    <h2>${escapeHtml(d.name || "")}</h2>
    <div class="meta">${escapeHtml([d.hospital, d.department, d.position].filter(Boolean).join(" · "))}
      ${d.source_url ? `· <a href="${d.source_url}" target="_blank" rel="noopener">출처</a>` : ""}</div>
    ${d.specialty && d.specialty.length ? `<div class="meta">전문분야: ${escapeHtml(d.specialty.join(", "))}</div>` : ""}
    ${listBlock("학력", d.education)}
    ${listBlock("면허·자격", d.licenses)}
    ${listBlock("경력", d.career)}
    ${listBlock("학회", d.societies)}
    ${listBlock("논문·저서", d.publications)}
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

load();
```

- [ ] **Step 4: 뷰어 수동 확인**

Run (로컬 정적 서버):
```powershell
cd C:\Workspace\CV\viewer; ..\.venv\Scripts\python.exe -m http.server 8080
```
브라우저에서 `http://localhost:8080/` 열기.
Expected: 샘플 의사 카드 1개 표시. 이름 검색·병원/진료과 필터 동작.
실제 데이터 확인: `http://localhost:8080/?data=../data/doctors.json` (경로는 서버 루트 기준으로 조정).

- [ ] **Step 5: 커밋**

```powershell
cd C:\Workspace\CV; git add viewer; git commit -m "feat: add static doctor viewer"
```

---

## 완료 기준 (Phase 1)

- [ ] `pytest` 전체 통과
- [ ] 빅5 중 최소 1곳에서 실제 의사 데이터가 `data/doctors.json`에 수집됨
- [ ] 뷰어에서 수집 데이터가 검색·필터·상세로 열람됨
- [ ] robots.txt 준수 및 rate-limit 적용 확인

## 이후 단계 (별도 스펙)

1. 공공데이터 API로 300병상 이상 종합병원 전체 목록 자동 수집 + 확장
2. 정기 갱신·변경 감지·이력 관리
3. 상위 병원 맞춤 파서(하이브리드)로 정밀도 향상
