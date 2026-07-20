# 의료진 경력 크롤러 + 웹 뷰어 — 설계 (Phase 1: 수직 슬라이스)

- 작성일: 2026-07-20
- 저장소: karmawolf-git/CV
- 상태: 승인됨 (사용자 확인 완료)

## 1. 목적

300병상 이상 종합병원 홈페이지에 **공개된** 의사들의 경력 정보를 크롤링하여 구조화된
데이터로 정리하고, 웹페이지에서 검색·필터·열람할 수 있게 한다.

Phase 1에서는 **샘플 병원(빅5)** 으로 전체 파이프라인을 끝까지 완성·검증한다.
전체 350여 곳으로의 확장, 정기 갱신, 맞춤 파서는 이후 별도 스펙으로 다룬다.

## 2. Phase 1 범위

### 대상 병원 (빅5, 샘플)
1. 서울아산병원
2. 삼성서울병원
3. 세브란스병원 (연세대학교)
4. 서울대학교병원
5. 분당서울대학교병원

> 참고: 빅5 의료진/교수진 페이지는 JavaScript 렌더링 비중이 높다.
> 따라서 `fetcher`의 Playwright 폴백이 실제로 자주 사용될 것으로 예상한다.

### 포함
- 손으로 작성한 병원 목록(`hospitals.yaml`)에서 시작
- 의료진 목록 페이지 → 개별 의사 프로필 링크 탐색
- 정적/동적 페이지 수집 + 원본 HTML 캐시
- Claude(LLM) 기반 구조화 추출
- 정규화 JSON 저장
- 정적 웹 뷰어(검색/필터/상세)

### 제외 (이후 단계)
- 공공데이터 API를 통한 전체 병원 목록 자동 수집
- 정기 자동 갱신 / 변경 감지 / 이력 관리
- 상위 병원 맞춤 파서(하이브리드)
- 인증/권한, 다중 사용자

## 3. 기술 스택

| 영역 | 선택 |
|------|------|
| 언어 | Python 3.11+ |
| 정적 수집 | `httpx` |
| 동적 수집(폴백) | `Playwright` (headless Chromium) |
| HTML 파싱/정제 | `BeautifulSoup4` |
| LLM 추출 | Anthropic Claude (`anthropic` SDK), 최신 모델 |
| 스키마 검증 | `pydantic` v2 |
| 설정 | `pyyaml` |
| 테스트 | `pytest` |
| 뷰어 | 정적 HTML/CSS/JS (프레임워크 없음), `doctors.json` 로드 |

- `ANTHROPIC_API_KEY`는 환경변수로 주입한다. 키 값을 코드/설정 파일/저장소에 넣지 않는다.
- 의존성 관리: `pyproject.toml` (uv 또는 pip).

## 4. 아키텍처 (모듈은 각각 독립·테스트 가능)

```
hospitals.yaml
      │
      ▼
[hospital_list] ──▶ [discovery] ──▶ [fetcher] ──▶ [extractor] ──▶ [store] ──▶ doctors.json
                                       │  ▲                                        │
                                    raw HTML 캐시                                   ▼
                                                                              [viewer] (정적 웹)
```

### 4.1 `hospital_list`
- 입력: `hospitals.yaml`
- 각 항목: `id`, `name`, `base_url`, `doctor_index_url`(의료진 목록 페이지), 선택적 `notes`
- 출력: `Hospital` 객체 리스트
- Phase 2에서 이 모듈만 공공 API 수집으로 교체 가능하도록 인터페이스 고정

### 4.2 `discovery`
- 입력: `Hospital`, 의료진 목록 페이지 HTML
- 개별 의사 프로필 URL 추출
- 휴리스틱: 링크 텍스트/href에 `의료진`, `교수`, `doctor`, `staff`, `profile` 등 포함; 페이지네이션 추적
- 실패/불완전 시: `hospitals.yaml`에 명시적 URL 패턴/목록으로 보완 가능
- 출력: 프로필 URL 리스트

### 4.3 `fetcher`
- 정적 요청(`httpx`) 우선 시도
- 응답이 비어 있거나 JS 렌더링으로 판단되면 Playwright로 폴백
- **robots.txt 확인 및 준수**, 요청 간 rate-limit(지연), 식별 가능한 User-Agent
- 원본 HTML을 디스크에 캐시(`cache/<hospital_id>/<hash>.html`) → 재실행 시 재수집 방지, 추출 반복 개발 용이
- 출력: 원본 HTML (+ 캐시 경로)

### 4.4 `extractor`
- 입력: 원본 HTML
- HTML 정제(스크립트/스타일/네비 제거) → 텍스트/축약 DOM
- Claude에 **고정 JSON 스키마**로 구조화 추출 요청
- 결과를 `pydantic`으로 검증; 검증 실패 시 로그 + 원본 보관(수동 검토용)
- 출력: `Doctor` 객체 (또는 실패 기록)

### 4.5 `store`
- `Doctor` 객체 정규화 및 저장
- 병원별 JSON + 통합 `doctors.json`
- 병원 내 중복 제거(이름 + 프로필 URL 기준)

### 4.6 `viewer`
- 정적 `viewer/index.html` + JS
- `doctors.json` 로드 후:
  - 이름 검색
  - 병원 / 진료과 필터
  - 목록 + 의사별 상세 카드(학력·경력·학회·논문)
  - 출처 링크(`source_url`) 표시

## 5. 데이터 스키마

```python
class EducationItem:   # 학력
    institution: str
    degree: str | None
    year: str | None

class LicenseItem:     # 면허/자격
    name: str
    year: str | None

class CareerItem:      # 경력
    org: str
    role: str | None
    period: str | None

class Doctor:
    hospital: str
    hospital_url: str
    name: str
    position: str | None          # 직위
    department: str | None        # 진료과
    specialty: list[str]          # 전문분야
    profile_url: str | None
    photo_url: str | None
    education: list[EducationItem]
    licenses: list[LicenseItem]
    career: list[CareerItem]
    societies: list[str]          # 학회
    publications: list[str]       # 논문/저서
    source_url: str
    crawled_at: str               # ISO8601
```

- 결측 필드는 빈 리스트/`None` 허용 (병원마다 공개 범위 다름)

## 6. 오류 처리

- **병원별 격리**: 한 병원 실패가 전체 파이프라인을 멈추지 않음
- **단계 분리**: 원본 HTML 캐시 후 추출을 별도로 재시도 가능
- LLM 추출 검증 실패 → 로그 + 원본 보관, 해당 의사만 건너뜀
- 네트워크 타임아웃 / rate-limit / robots 차단 → 기록하고 계속
- 실행 요약 리포트: 병원별 수집 성공/실패 건수

## 7. 테스트 전략

- **단위 테스트**
  - `discovery`: 저장된 목록 HTML → 기대 프로필 URL 집합
  - `fetcher`: 정적/동적 폴백 판단 로직 (네트워크 모킹)
  - 스키마: 정상/결측/이상 입력에 대한 `pydantic` 검증
- **골든파일 테스트**
  - 저장된 의사 페이지 HTML 픽스처 → 기대 추출 결과 (LLM 호출은 모킹/기록 재생)
- **뷰어**: 샘플 `doctors.json`으로 수동 확인 (검색/필터/상세)

## 8. 법적·윤리 고려

- 공개된 전문 경력 페이지만 대상
- robots.txt 준수, rate-limit, 식별 가능한 User-Agent
- 출처(`source_url`)와 수집 시각(`crawled_at`) 기록
- 개인 연락처 등 민감정보는 수집 대상에서 제외

## 9. 디렉터리 구조(안)

```
CV/
├─ pyproject.toml
├─ hospitals.yaml
├─ src/
│  └─ doctor_cv/
│     ├─ models.py        # pydantic 스키마
│     ├─ hospital_list.py
│     ├─ discovery.py
│     ├─ fetcher.py
│     ├─ extractor.py
│     ├─ store.py
│     └─ cli.py           # 파이프라인 실행 진입점
├─ viewer/
│  ├─ index.html
│  └─ app.js
├─ cache/                 # 원본 HTML 캐시 (gitignore)
├─ data/
│  └─ doctors.json        # 산출물
├─ tests/
│  └─ fixtures/           # HTML 픽스처
└─ docs/superpowers/specs/2026-07-20-doctor-cv-crawler-design.md
```

## 10. 이후 단계 (별도 스펙)

1. 공공데이터(심평원/공공데이터포털) API로 300병상 이상 종합병원 전체 목록 자동 수집 + 확장 실행
2. 정기 자동 갱신, 변경 감지, 수집 이력 관리
3. 상위/중요 병원 맞춤 파서(하이브리드)로 정밀도 향상
