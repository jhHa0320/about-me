# 🎭 Jeonghun Ha's Portfolio

본 프로젝트는 단순한 이력서를 넘어, 저만의 브랜드 컬러(Amber/Gold/Black)와 극장 같은 몰입감을 주는 반응형 포트폴리오 웹사이트입니다.

---

## 🛠 Tech Stack

- **Backend:** ![Django](https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white) 
- **Frontend:** ![Bootstrap 5](https://img.shields.io/badge/Bootstrap_5-7952B3?style=flat-square&logo=bootstrap&logoColor=white) ![Vanilla JS](https://img.shields.io/badge/Vanilla_JS-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
- **Data:** `JSON` / `SQLite3` (데이터 기반 동적 랜더링)
- **Design:** CSS Grid, CSS `clamp()` (Fluid Typography)

---

## ✨ Core Features

1. **Fluid Typography & Grid System (극한의 반응형 최적화)**
   - CSS 함수 `clamp()`를 활용하여 디바이스 크기(Mobile -> Tablet -> PC)에 맞춰 폰트 크기와 여백이 물 흐르듯 유연하게 변합니다.
   - 텍스트 줄바꿈 현상을 방지하기 위해 **CSS Grid**를 도입하였으며, 모바일에서는 스크롤 피로도를 낮추기 위해 **Tab UI(Pills)**를 동적으로 제공합니다.

2. **Dynamic Project Filtering & Micro-Animations**
   - JavaScript 비동기(`async/await`) 패턴을 활용해 카테고리 필터링 시 부드러운 전환을 제공합니다.
   - **Skeleton UI** 및 순차적인(Staggered) **Fade-in 효과**를 적용하여 App과 같은 고급스러운 사용자 경험(UX)을 연출합니다.

3. **SEO & Performance Optimization**
   - 불필요한 이미지 렌더링 부하를 줄이기 위해 `loading="lazy"` 속성을 네이티브 수준에서 전면 적용했습니다.
   - Semantic HTML 구조 설계 및 Open Graph(OG), Meta 태그를 적재적소에 배치하여 검색 엔진 크롤러 가시성을 극대화했습니다.

---

## 🚀 How to Run (Local Development)

본 프로젝트는 Python 환경에서 실행할 수 있습니다.

```bash
# 1. 저장소 클론
git clone https://github.com/jhHa0320/about_me.git
cd about_me

# 2. 가상환경 생성 및 활성화 (선택)
python -m venv .venv
source .venv/Scripts/activate  # Windows

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 데이터베이스 마이그레이션 및 실행
python manage.py migrate
python manage.py runserver
```
접속 URL: `http://localhost:8000`

---

## 🗺 Future Roadmap (Phase 2)
다음과 같은 고도화를 계획 중입니다.

- **Frontend Modernization:** Next.js(React) + Tailwind CSS로 마이그레이션하여 컴포넌트 재사용성 증대.
- **BaaS Integration:** Supabase를 연동하여 실시간 데이터베이스 관리 및 관리자 대시보드 구축.
- **CI/CD Pipeline:** GitHub Actions를 활용한 자동 배포 파이프라인 구축.
