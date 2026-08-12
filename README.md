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

## 콘텐츠 동기화

콘텐츠(DB·이미지)는 git 으로 추적하지 않습니다. **운영 서버의 `/admin` 이
유일한 원본**이고, 로컬은 내려받아 쓰기만 합니다.

> ⚠️ 로컬 `/admin` 에서는 글을 쓰지 마세요. 다음 `--apply` 때 덮어써집니다.
> (덮어쓰기 전 `_pa_backup/` 에 백업되므로 복구는 가능합니다.)

### 준비 — 처음 한 번만

```bash
pip install -r requirements-dev.txt
```

그리고 `.env` 에 아래 두 줄을 추가합니다. 토큰은
[계정 페이지](https://www.pythonanywhere.com/account/#api_token)에서 발급합니다.
`.env` 는 `.gitignore` 에 있어 커밋되지 않습니다.

```bash
PA_USERNAME=hjh0320
PA_TOKEN=여기에_발급받은_토큰
```

제대로 붙었는지 확인:

```bash
python scripts/fetch_pythonanywhere.py --list
```

서버의 홈 디렉터리 목록이 나오면 성공입니다. `PA_USERNAME / PA_TOKEN 이
설정되지 않았습니다` 가 나오면 `.env` 를 다시 확인하세요.

---

### 도구 1 — 운영과 로컬 비교 `--check`

**언제**: 로컬에서 코드 작업을 시작하기 전. 그리고 `--apply` 하기 직전에 항상.

```bash
python scripts/fetch_pythonanywhere.py --check
```

운영 DB 를 임시 폴더로 내려받아 비교만 하고 끝냅니다.
**로컬 파일도 서버도 건드리지 않습니다.**

출력 예시:

```
마이그레이션   로컬: 0025_seed_featured_and_key_results
               운영: 0025_seed_featured_and_key_results

테이블                 로컬      운영   차이
  ────────────────────────────────────────────
  프로젝트                14      15   운영에 +1
  활동·자격증               6       6

■ 프로젝트
    + 운영에만  #15  새로 추가한 프로젝트
    ~ 내용 다름  #12  픽합주(실시간 합주실 예약 보조 서비스)
        key_result
          로컬: 서울 25개 구 합주실 데이터 통합
          운영: 응답 2.0s → 70ms

요약: 운영에만 1건 · 로컬에만 0건 · 내용 다름 1건

로컬에만 있는 데이터는 없습니다. 안전하게 받아올 수 있습니다:
  python scripts/fetch_pythonanywhere.py --apply
```

읽는 법:

| 표시 | 뜻 | 해야 할 일 |
| --- | --- | --- |
| `+ 운영에만` | 서버에서 새로 쓴 내용 | `--apply` 로 받아오면 됨 |
| `- 로컬에만` | **로컬에서만 있는 내용** | `--apply` 하면 사라짐. 운영 `/admin` 에 다시 입력하거나 포기 |
| `~ 내용 다름` | 양쪽에 있으나 값이 다름 | 운영 값으로 덮어써짐 |
| `두 DB 의 내용이 같습니다` | 동일 | 받아올 것 없음 |

마이그레이션 줄이 서로 다르면 스키마가 어긋난 상태라 경고가 뜹니다.
그때는 `--apply` 후 `python manage.py migrate` 를 실행하세요.

**받아오기**

```bash
python scripts/fetch_pythonanywhere.py --apply
python manage.py migrate        # 새 마이그레이션이 있을 때만
```

기존 로컬 `db.sqlite3` 와 `media/` 는 `_pa_backup/<시각>/` 에 백업된 뒤
교체됩니다. 잘못 받았으면 그 폴더에서 되돌리면 됩니다.

---

### 도구 2 — 콘텐츠 백업 `backup_content.py`

**언제**: `/admin` 에서 글을 여러 개 쓰거나 고친 다음. 주 1회 정도면 충분합니다.

모든 콘텐츠가 서버의 SQLite 파일 하나에 들어 있습니다. 그 파일이 사라지면
프로젝트 설명과 상세 보고서가 전부 사라지므로 스냅샷을 남겨 둡니다.

```bash
python scripts/backup_content.py
```

출력:

```
운영 DB 내려받는 중… (/home/hjh0320/about_me/db.sqlite3)
  512.0 KB
dumpdata 실행 중…
  activity 6 · career 1 · education 3 · leadership 4 · profile 1
  · project 14 · projectcategory 7 · projecttype 3 · skill 26

저장: backups\portfolio-20260812-230818.json  (140.1 KB)
```

운영 DB 를 받아 **로컬에서** `dumpdata` 를 돌리므로 서버 콘솔이 필요
없습니다. 결과는 JSON 이라 `git diff` 로 무엇이 언제 바뀌었는지 보입니다.
직전 스냅샷과 내용이 같으면 저장하지 않습니다.

자주 쓰는 조합:

```bash
# 백업하고 git 커밋까지 한 번에 (가장 실용적)
python scripts/backup_content.py --git-commit

# 이미지까지 (용량이 커서 git 밖 _pa_backup/media-snapshots/ 에 저장)
python scripts/backup_content.py --with-media

# 최근 20개만 남기고 오래된 스냅샷 정리
python scripts/backup_content.py --prune 20

# 내용이 같아도 강제로 새로 저장
python scripts/backup_content.py --force
```

**복원**

```bash
python scripts/backup_content.py --restore backups/portfolio-20260812-230818.json
```

로컬 DB 를 대상으로 동작합니다. 실행 전 현재 로컬 DB 를 `_pa_backup/` 에
백업하고 확인 프롬프트를 띄웁니다. `loaddata` 는 같은 pk 의 행을
덮어쓰며, 스냅샷에 없는 행은 그대로 남습니다(완전 초기화가 아닙니다).

운영에 되돌릴 때는 스냅샷 파일을 서버로 올린 뒤 콘솔에서:

```bash
python scripts/deploy_pythonanywhere.py --push backups/portfolio-....json
# 그다음 서버 Bash 콘솔에서
cd /home/hjh0320/about_me
python manage.py loaddata backups/portfolio-....json
```

---

### 한눈에 보기

| 하고 싶은 것 | 명령 |
| --- | --- |
| 서버에 뭐가 있는지 보기 | `python scripts/fetch_pythonanywhere.py --list` |
| 운영과 로컬 차이 확인 | `python scripts/fetch_pythonanywhere.py --check` |
| 운영 콘텐츠 받아오기 | `python scripts/fetch_pythonanywhere.py --apply` |
| 콘텐츠 백업 + 커밋 | `python scripts/backup_content.py --git-commit` |
| 백업 복원 (로컬) | `python scripts/backup_content.py --restore <파일>` |
| 코드 배포 | `python scripts/deploy_pythonanywhere.py` |
| 올릴 목록만 미리 보기 | `python scripts/deploy_pythonanywhere.py --dry-run` |

`--help` 를 붙이면 각 스크립트의 전체 옵션을 볼 수 있습니다.

### 잘 안 될 때

| 증상 | 원인과 해결 |
| --- | --- |
| `PA_USERNAME / PA_TOKEN 이 설정되지 않았습니다` | `.env` 에 두 값을 넣었는지 확인 |
| `토큰이 거부되었습니다 (401)` | 토큰이 만료·재발급됨. 새로 발급해 `.env` 갱신 |
| `rate limit — N초 대기 후 재시도` | 정상입니다. API 분당 제한에 걸려 자동으로 기다립니다 |
| `requests 가 필요합니다` | `pip install -r requirements-dev.txt` |
| `원격 프로젝트 폴더를 찾지 못했습니다` | `.env` 에 `PA_REMOTE_DIR=/home/hjh0320/about_me` 추가 |
| 배포 후 화면이 옛날 그대로 | 정적 파일을 바꿨다면 서버 콘솔에서 `DEBUG=False python manage.py collectstatic --noinput` 후 리로드 |

### 외부 DB 는 왜 안 쓰나

로컬과 운영이 같은 DB 를 보면 동기화 문제 자체가 사라지지만,
**PythonAnywhere 무료 계정은 외부 아웃바운드가 프록시 화이트리스트로
제한**되어 Postgres/MySQL 같은 일반 TCP 연결이 나가지 않습니다.
자체 MySQL 은 서버에서만 접근 가능하고, 로컬에서 붙으려면 SSH 터널이
필요한데 SSH 는 유료 전용입니다. 유료 전환 시에는 외부 Postgres 공유가
정답이며, 그때는 이미지도 오브젝트 스토리지로 옮겨야 합니다.

## 접근성 · 성능 기준

이 저장소에서 지키려는 선입니다.

- JavaScript 없이도 모든 콘텐츠가 보입니다. 스크롤 애니메이션은
  `prefers-reduced-motion` 과 JS 가용 여부를 확인한 뒤에만 켜집니다
- 키보드만으로 전체 탐색이 가능하고, 모든 포커스에 링이 보입니다
- 본문 대비 4.5:1 이상 (라이트 · 다크 모두)
- 가로 스크롤 없음 (320px 까지)
- 프로필 이미지는 원본을 보존한 채 축소본을 따로 생성해 사용합니다
- 웹폰트는 비동기 로드 — 폰트 응답이 느려도 첫 페인트를 막지 않습니다
