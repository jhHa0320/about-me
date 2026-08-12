# Jeonghun Ha — Portfolio

취업 · 인턴 · 학부연구생 지원에 사용하는 개인 포트폴리오 사이트입니다.
방문자가 30초 안에 **"어떤 개발자이고, 무엇을 만들었고, 무엇을 해결했는지"** 를
파악할 수 있도록 정보 구조를 구성했습니다.

배포: https://hjh0320.pythonanywhere.com/

---

## Tech Stack

| 영역 | 사용 기술 |
| --- | --- |
| Backend | Django 5.1 (MVT), SQLite |
| Frontend | 프레임워크 없는 CSS + Vanilla JS |
| 콘텐츠 | Django Admin + Summernote (django-bleach 로 sanitize) |
| 배포 | PythonAnywhere, WhiteNoise |

CSS 프레임워크는 사용하지 않습니다. 리팩토링 과정에서 Bootstrap 클래스를
전부 자체 컴포넌트로 대체한 뒤, 227 KB 의 렌더링 차단 CSS 가 실제로는 한 개의
셀렉터도 쓰이지 않고 있어 제거했습니다. 테마 저장 값과의 호환을 위해
`data-bs-theme` 속성 이름만 그대로 유지합니다.

---

## 정보 구조

```
Hero              이름 · 직군 · 연락 수단 · 핵심 수치
  ↓
Featured Projects 대표 프로젝트 3건 (역할 / 기간 / 스택 / 결과)
  ↓
All Projects      나머지 프로젝트 + 기술 필터 + 더 보기
  ↓
Experience        리더십 · 경력 · 대외활동 통합 타임라인 (최신순)
  ↓
Skills            주력 / 활용 가능 / 경험 보유 + 실제 사용 프로젝트 수
  ↓
About             학력 · 자격증
  ↓
Contact (footer)
```

---

## 콘텐츠는 코드가 아니라 관리자 페이지에서 고칩니다

문구를 템플릿에 하드코딩하지 않았습니다. `/admin/` 에서 바꿀 수 있는 항목:

| 위치 | 필드 | 설명 |
| --- | --- | --- |
| 프로필 | `headline` | Hero 이름 위 한 줄 직군. 비우면 기본 요약 문구가 표시됩니다 |
| 프로필 | `introduction` | Hero 소개 문장. 비우면 최신 학력이 대신 표시됩니다 |
| 프로필 | `show_birthdate` | 생년월일 노출 여부 (기본 꺼짐, 데이터는 보존) |
| 프로필 | `show_email_address` | 이메일 원문 노출 여부 (기본 꺼짐, mailto 링크는 항상 동작) |
| 프로필 | `resume_url` | 이력서 링크. 채우면 Hero/Footer 에 버튼이 생깁니다 |
| 프로젝트 | `is_featured` | 첫 화면 상단 대표 프로젝트. 3개 내외 권장 |
| 프로젝트 | `key_result` | 카드에 뱃지로 보이는 한 줄 성과. 비우면 뱃지가 사라집니다 |

대표 프로젝트가 보이는 순서는 프로젝트의 `order` 값(높을수록 먼저)을 따릅니다.

---

## 관리자 글의 서식 처리

프로젝트 상세 본문은 Word / Notion 에서 붙여넣은 HTML 이 많아
`font-family: Helvetica; font-size: 11pt; color: #000` 같은 인라인 스타일과
Office 네임스페이스 태그가 섞여 있습니다. 이 값들은 사이트 타이포그래피를
덮어쓰고 다크 모드에서 글자를 보이지 않게 만듭니다.

**DB 원문은 그대로 두고** 렌더링 시점에 `richtext` 필터가 정리합니다
(`portfolio/templatetags/portfolio_extras.py`).

- 인라인 `font-family` / `font-size` / `color` 제거 — 강조(`font-weight`)는 보존
- `data-path-to-node`, `class="0"`, `<o:p>` 등 편집기 잔재 제거
- 본문 전체를 감싼 `<h4>` 같은 래퍼 헤딩을 `<div>` 로 강등
- 작성자가 쓴 헤딩 레벨을 `h3 → h4 …` 로 재배열해 문서 개요를 유지
- `<ul>` 밖에 떠 있는 `<li>` 를 리스트로 감쌈
- 외부 링크에 `rel="noopener noreferrer"` 부여

---

## 실행

```bash
git clone https://github.com/jhHa0320/about_me.git
cd about_me

python -m venv .venv
source .venv/Scripts/activate    # Windows

pip install -r requirements.txt
cp .env.example .env             # SECRET_KEY 등을 채웁니다

python manage.py migrate
python manage.py runserver
```

http://localhost:8000

### 테스트

```bash
python manage.py test portfolio
```

뷰 · 모델 · 관리자 설정과 함께, 리팩토링에서 추가한 콘텐츠 정규화 로직
(리치 텍스트 정리, 자유 형식 기간 정렬, 개인정보 노출 기본값)을 검증합니다.

---

## 접근성 · 성능 기준

이 저장소에서 지키려는 선입니다.

- JavaScript 없이도 모든 콘텐츠가 보입니다. 스크롤 애니메이션은
  `prefers-reduced-motion` 과 JS 가용 여부를 확인한 뒤에만 켜집니다
- 키보드만으로 전체 탐색이 가능하고, 모든 포커스에 링이 보입니다
- 본문 대비 4.5:1 이상 (라이트 · 다크 모두)
- 가로 스크롤 없음 (320px 까지)
- 프로필 이미지는 원본을 보존한 채 축소본을 따로 생성해 사용합니다
- 웹폰트는 비동기 로드 — 폰트 응답이 느려도 첫 페인트를 막지 않습니다
