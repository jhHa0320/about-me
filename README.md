# Jeonghun Ha — Portfolio & Resume Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-092E20.svg)](https://www.djangoproject.com/)
[![Deployment](https://img.shields.io/badge/Live-PythonAnywhere-brightgreen.svg)](https://hjh0320.pythonanywhere.com/)

> **"30초 안에 어떤 개발자이고, 무엇을 해결했는지 전달한다."**  
> 채용담당자 및 면접관이 핵심 역량(**Data · AI · Backend · Security**)과 주요 프로젝트 성과를 신속하고 명확하게 파악할 수 있도록 설계된 **Django 기반 고성능·고접근성 포트폴리오 웹 서비스**입니다.

- **라이브 사이트**: [https://hjh0320.pythonanywhere.com/](https://hjh0320.pythonanywhere.com/)

---

## 💡 주요 특징 및 핵심 기능

### 1. Dynamic Content Management (Admin Single Source of Truth)
- 문구 및 데이터를 프론트엔드 코드에 하드코딩하지 않고 **Django Admin에서 100% 제어**합니다.
- 프로젝트 우선순위(`order`), 핵심 한 줄 성과(`key_result`), 기술 분야(`domain`), 자격증/수상 구분을 관리자에서 실시간으로 정렬하고 제어합니다.

### 2. Dynamic Resume & Portfolio Exporter (`resume_export` 앱)
- 포트폴리오 사이트 데이터를 바탕으로 **표준 규격 이력서/포트폴리오 문서(PDF, DOCX)를 즉시 동적 생성**합니다.
- **Dynamic Exclusion Filter**: 특정 회사/직군 지원 시 비공개 프로젝트나 불필요한 항목을 선택 제외(`ResumeExportConfig`)하여 맞춤형 서류를 생성할 수 있습니다.
- **Cross-Platform PDF Rendering**: ReportLab 및 `xhtml2pdf` 기반으로 나눔고딕 TTF 폰트를 번들링하여 한글/영문 글자폭 균일화 및 깨짐 현상을 완벽 방지했습니다.

### 3. Custom Rich-Text Normalization Filter (`portfolio_extras.py`)
- Notion, Word 등 외부 오피스 소프트웨어에서 복사/붙여넣기 시 유입되는 인라인 스타일(`font-family`, `font-size`, `color`), MS Office 전용 태그(`<o:p>`), 비표준 속성을 **DB 원본을 건드리지 않고 렌더링 시점에 정규화**합니다.
- 다크 모드 시 글자가 보이지 않는 문제(검은 배경에 검은 글자)를 예방하고 타이포그래피 일관성을 유지합니다.

### 4. Serverless Sync & Backup Tooling (`scripts/`)
- 외부 DB 연결이 제한된 PythonAnywhere 무료 플랜 환경을 극복하기 위해 **REST API 기반 자동 동기화 CLI**를 직접 개발했습니다.
- 운영-로컬 데이터 차이 사전 분석(`--check`), 지능형 백업 및 스냅샷 복원(`backup_content.py`), zero-downtime 자동 배포(`deploy_pythonanywhere.py`)를 제공합니다.

---

## 🛠 Tech Stack & Architecture

| 영역 | 기술 스택 | 설계 의도 및 선택 이유 |
| --- | --- | --- |
| **Backend** | Django 5.1 (MVT), SQLite | 빠른 트랜잭션과 독립 실행이 가능한 경량 MVT 아키텍처 구축 |
| **Document Export** | xhtml2pdf, python-docx, ReportLab | 웹 기반 이력서를 스타일을 유지한 채 PDF/DOCX 표준 문서로 인메모리 파이프라인 생성 |
| **Frontend** | Pure HTML5, Vanilla CSS3, Vanilla JS | 외부 CSS 프레임워크를 제거하고 **Zero Render-Blocking CSS**로 렌더링 속도 최적화 |
| **Sanitization** | Custom HTML Parser (`_RichTextCleaner`), django-bleach | 외부 HTML 유입에 대한 보안 검증 및 디자인 시스템 토큰 강제 적용 |
| **Deployment** | PythonAnywhere, WhiteNoise, PythonAnywhere REST API | WSGI 및 정적 파일 서버 최적화 + 커스텀 배포 파이프라인 |

---

## 🏗 시스템 설계 의도 (Architecture Rationale)

```
[ Django Admin (Single Source of Truth) ]
           │
           ├───────────────────────────────┐
           ▼                               ▼
[ Web Portfolio View ]          [ Resume Exporter Engine ]
  │                               │
  ├─ Custom Rich-Text Sanitizer   ├─ Exclusion Filter (ResumeExportConfig)
  ├─ Zero-Framework CSS Tokens    ├─ Custom Font Link Callback Scheme
  └─ Progressive Enhancement      └─ PDF (xhtml2pdf) & DOCX (python-docx)
```

1. **Zero-Framework Frontend Design**:
   - 기존 220KB+ 크기의 Bootstrap CSS 프레임워크를 완전 제거하고, CSS 커스텀 프로퍼티(Design Tokens) 기반의 가벼운 Vanilla CSS 스타일시트로 전환했습니다.
   - First Contentful Paint (FCP) 시간을 최소화하고 라이트/다크 테마 전환 시 불필요한 스타일 재계산 부하를 차단했습니다.
2. **DB 원본 보존형 렌더타임 정규화 (Render-Time Normalization)**:
   - 관리자가 외부 작성 도구에서 HTML을 붙여넣었을 때 DB 내 원문 데이터는 보존하되, 뷰 렌더링 시 커스텀 HTML 파서(`_RichTextCleaner`)가 디자인 시스템을 위반하는 CSS 속성만 선택적으로 제거합니다.
3. **독립형 문맥 기반 서류 추출 엔진 (Context-Aware Document Engine)**:
   - 별도의 헤드리스 브라우저(Puppeteer/Playwright) 설치 없이 경량 파이프라인(`xhtml2pdf` + `python-docx`)을 탑재하여 서버 메모리 사용량을 최소화하면서 초고속으로 동적 서류를 출력합니다.

---

## 🛠️ 핵심 트러블슈팅 (Troubleshooting)

### 1. PythonAnywhere 타사 pyHanko 모듈 버전 충돌 및 실행 붕괴 우회
- **문제**: `xhtml2pdf` 패키지가 사용하지 않는 PDF 디지털 서명 모듈 로직을 파싱하는 과정에서, PythonAnywhere 전역 환경의 구버전 `pyhanko`와 충돌하여 `ModuleNotFoundError: No module named 'pyhanko_certvalidator._asyncio_compat'` 오류가 발생하며 이력서 추출 기능이 중단됨.
- **원인 분석**: 충돌이 발생하는 `_asyncio_compat` 서브모듈의 실제 역할은 Python 표준 라이브러리의 `asyncio.to_thread` 호출을 래핑하는 단순 도우미 함수에 불과함.
- **해결 방안**: `xhtml2pdf` 뷰/유틸리티가 로드되기 직전, `sys.modules` 딕셔너리에 `asyncio.to_thread`를 가진 가짜 Shim 모듈을 동적 주입하여 서명 기능을 사용하지 않는 환경에서 외부 모듈 충돌을 완벽 우회함.
  ```python
  if "pyhanko_certvalidator._asyncio_compat" not in sys.modules:
      _asyncio_compat_shim = types.ModuleType("pyhanko_certvalidator._asyncio_compat")
      _asyncio_compat_shim.to_thread = asyncio.to_thread
      sys.modules["pyhanko_certvalidator._asyncio_compat"] = _asyncio_compat_shim
  ```

### 2. Linux/운영 환경 PDF 한글 깨짐 및 UTF-8 / Path 인코딩 이슈
- **문제**: Linux 운영 환경에서 생성된 PDF 서류의 한글 텍스트가 깨지거나 네모 상자(Square)로 출력되는 문제 발생.
- **원인 분석**:
  1) Django의 `ManifestStaticFilesStorage`가 빌드 시 정적 파일명에 핑거프린트 해시를 부여하여 `link_callback`의 정적 파일 탐색 실패.
  2) ReportLab 기본 CID 폰트(`HYGothic-Medium`) 사용 시 영문/숫자 타이포그래피 자간이 불균일해짐.
  3) 로컬 Windows 환경에서 사용자 폴더 경로에 한글/비-ASCII 문자(예: `C:\Users\하정훈\...`)가 포함되어 있으면 `xhtml2pdf` CSS 파서가 바이트 단위 파싱 중 인코딩 에러 발생.
- **해결 방안**:
  1) 나눔고딕(`NanumGothic-Regular`, `NanumGothic-Bold`) TTF 폰트 파일 2종을 패키지 내부에 직접 번들링하여 표준 폰트 패밀리로 등록.
  2) PDF 템플릿 전용 커스텀 URI 스킴(`resume-font:`)을 도입하고, `link_callback`에서 해시 없는 원본 파일 경로로 1:1 매핑 변환하여 인코딩 오류 및 해시 미스 문제를 근본적으로 결합 해결함.

### 3. PythonAnywhere 아웃바운드 REST 제약 극복 및 데이터 동기화 파이프라인
- **문제**: PythonAnywhere 무료 플랜 특성상 외부 데이터베이스(Postgres/MySQL) 직통 TCP 연결 및 SSH 터널링이 제한되어, 운영 DB와 로컬 개발 데이터 간 무분별한 덮어쓰기 위험이 존재함.
- **해결 방안**:
  1) PythonAnywhere REST API 연동 도구(`scripts/pa_api.py`) 구축.
  2) `fetch_pythonanywhere.py --check` 커맨드로 양방향 테이블 레코드 및 필드 차이(Delta)를 사전에 터미널에 시각화.
  3) `backup_content.py`를 통해 운영 DB 덤프 데이터를 스냅샷 JSON 형태로 저장하고 Git 연동 관리.
  4) 배포 스크립트(`deploy_pythonanywhere.py`) 실행 시 서버의 HTTP 409 (Reloading in progress) 응답에 대응하는 지수 백오프(Exponential Backoff) 재시도 로직 구현.

---

## 🗺️ 정보 구조 (Information Architecture)

```
Hero              성명 · 직군 필터 · 대표 학력 · 영어 성적 · 핵심 수치 뱃지 · 서류 다운로드
  ↓
About             학력 상세 / 자격증 및 수상 실적 (2단 그리드)
  ↓
Skills            분야별 기술 스택 (Language / Data Science / AI / Security / Backend / 기타)
                  - 각 스택별 관련 프로젝트 카운트 표시 및 클릭 시 프로젝트 필터링 이동
  ↓
Projects          대표 및 전체 프로젝트 카드 목록 (수동 우선순위 `order` → 시간순 정렬)
                  - 핵심 성과(`key_result`) 뱃지, 사용 기술 태그, 더보기 점진적 노출
  ↓
Experience        리더십 · 경력 · 대외활동 통합 타임라인 (최신순)
  ↓
Contact           Contact 정보 및 이력서/포트폴리오 PDF·DOCX 내보내기 링크
```

---

## ⚙️ 로컬 실행 및 가이드 (Getting Started)

### 1. 프로젝트 복제 및 환경 설정

```bash
# 저장소 클론
git clone https://github.com/jhHa0320/about_me.git
cd about_me

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/Scripts/activate    # Windows (Bash)
# source .venv/bin/activate      # macOS / Linux

# 의존성 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
```

### 2. 마이그레이션 및 개발 서버 실행

```bash
python manage.py migrate
python manage.py runserver
```
- 접속 주소: `http://localhost:8000`

### 3. 단위 테스트 검증

```bash
python manage.py test portfolio resume_export
```
- 뷰/모델 검증, 리치텍스트 정규화 필터, 이력서 PDF/DOCX 내보내기 파이프라인 테스트를 검증합니다.

---

## 🔄 콘텐츠 동기화 및 백업 툴셋 (`scripts/`)

운영 환경의 `/admin`이 **데이터 원본(Single Source of Truth)**입니다.

| 실행 목적 | CLI 명령어 | 설명 |
| --- | --- | --- |
| **서버 파일 확인** | `python scripts/fetch_pythonanywhere.py --list` | 운영 서버의 파일 목록 및 상태 조회 |
| **운영-로컬 비교** | `python scripts/fetch_pythonanywhere.py --check` | 로컬 DB 변경 없이 운영 DB와 비교/차이 분석 |
| **운영 데이터 동기화** | `python scripts/fetch_pythonanywhere.py --apply` | 운영 DB 및 미디어 파일을 로컬로 동기화 (자동 백업 지원) |
| **콘텐츠 백업 & 커밋** | `python scripts/backup_content.py --git-commit` | 운영 DB 덤프 스냅샷 생성 및 Git 자동 커밋 |
| **로컬 데이터 복원** | `python scripts/backup_content.py --restore <JSON파일>` | 지정된 스냅샷 JSON 파일로 로컬 DB 복구 |
| **원격 자동 배포** | `python scripts/deploy_pythonanywhere.py` | Git Pull, Static 집계 및 Webapp 자동 리로드 배포 |
| **배포 시뮬레이션** | `python scripts/deploy_pythonanywhere.py --dry-run` | 실제 변경사항 변경 없이 배포 실행 계획 미리보기 |

---

## ♿ 성능 및 웹 접근성 (Accessibility & Performance)

- **Progressive Enhancement**: JavaScript가 비활성화된 환경에서도 포트폴리오의 모든 본문과 성과 데이터가 정상적으로 열람됩니다.
- **Accessibility & Contrast**: WCAG 2.1 AA 기준을 준수하여 라이트/다크 테마 모두 4.5:1 이상의 텍스트 대조비를 유지합니다.
- **Reduced Motion Support**: `prefers-reduced-motion` 미디어 쿼리를 감지하여 시각적 불편함이 있는 사용자에게는 인터랙션 애니메이션이 자동으로 축소됩니다.
- **Keyboard Navigation**: 전체 인터페이스에 대한 키보드 Tab 탐색 및 포커스 링이 선명하게 표시됩니다.
