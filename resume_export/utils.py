import asyncio
import os
import re
import sys
import tempfile
import types
from contextlib import contextmanager
from datetime import date
from io import BytesIO
from pathlib import Path

import docx
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from django.conf import settings
from django.template.loader import render_to_string
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from portfolio.models import Activity, Career, Leadership, Profile, Project
from portfolio.templatetags.portfolio_extras import bullets

from .models import ResumeExportConfig

# 한글 PDF 텍스트용 폰트. reportlab 내장 CID 폰트(HYGothic-Medium)는 한글은
# 문제없지만 영문/숫자 글자폭이 어색하게 벌어져서, 한글·영문이 같이 자연스러운
# 나눔고딕 TTF 를 직접 번들링해서 쓴다 (resume_export/static/.../fonts/).
_FONT_DIR = Path(__file__).resolve().parent / "static" / "resume_export" / "fonts"
_KOREAN_FONT = "NanumGothic"
_KOREAN_FONT_BOLD = "NanumGothic-Bold"
_pdf_engine_ready = False


def _ensure_pdf_engine_ready():
    """pyHanko 셔밍 + 폰트 등록을 최초 PDF 생성 시점까지 늦춘다.

    Returns:
        module: xhtml2pdf.pisa 모듈.

    Rationale:
        둘 다 원래 모듈 import 시점에 실행되는 전역 부작용이었다. PDF를 만들
        일이 없는 테스트/셸/다른 management command 가 이 모듈을 import 하는
        것만으로 reportlab 전역 상태를 건드리거나 sys.modules 를 셔밍하지
        않도록, 실제로 PDF를 만들 때만 1회 실행되게 옮겼다.
    """
    global _pdf_engine_ready
    if _pdf_engine_ready:
        from xhtml2pdf import pisa
        return pisa

    # xhtml2pdf 는 (쓰지도 않는) PDF 서명 기능 때문에 pyHanko 를 끌어오는데, 일부
    # 배포 환경(PythonAnywhere 등)에 이미 깔려 있는 다른 버전의 pyHanko 가 잡히면서
    # `pyhanko_certvalidator._asyncio_compat` 서브모듈이 없다고 죽는 경우가 있다.
    # 이 서브모듈이 제공하는 건 표준 라이브러리 asyncio.to_thread 와 동일한
    # 기능이라, xhtml2pdf 를 불러오기 전에 미리 채워 넣어 어떤 pyHanko 사본이
    # 잡히든 서명 기능을 실제로 쓰지 않는 우리 입장에서는 안전하게 우회된다.
    if "pyhanko_certvalidator._asyncio_compat" not in sys.modules:
        _asyncio_compat_shim = types.ModuleType("pyhanko_certvalidator._asyncio_compat")
        _asyncio_compat_shim.to_thread = asyncio.to_thread
        sys.modules["pyhanko_certvalidator._asyncio_compat"] = _asyncio_compat_shim

    from xhtml2pdf import pisa

    pdfmetrics.registerFont(TTFont(_KOREAN_FONT, str(_FONT_DIR / "NanumGothic-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(_KOREAN_FONT_BOLD, str(_FONT_DIR / "NanumGothic-Bold.ttf")))
    pdfmetrics.registerFontFamily(
        _KOREAN_FONT, normal=_KOREAN_FONT, bold=_KOREAN_FONT_BOLD,
        italic=_KOREAN_FONT, boldItalic=_KOREAN_FONT_BOLD,
    )

    _pdf_engine_ready = True
    return pisa

# PDF 템플릿의 @font-face 는 {% static %} 대신 이 전용 스킴을 참조한다.
# {% static %} 을 쓰면 운영에서 ManifestStaticFilesStorage 가 파일명에 해시를
# 붙이는데, link_callback 의 finders.find() 는 원본(해시 없는) 이름만 찾을 수
# 있어 폰트 임베드가 조용히 실패해 한글이 다시 깨진다. 그렇다고 실제 절대
# 경로를 템플릿 문자열에 그대로 박아 넣으면, 경로에 비-ASCII 문자(예: 한글
# 사용자 폴더명)가 섞였을 때 xhtml2pdf 의 CSS 파서가 그 바이트를 그대로
# 토큰화하다 깨진다. 그래서 CSS 에는 ASCII 전용 placeholder 만 남기고,
# 실제 파일 경로는 (한글이 섞여 있어도 안전한) link_callback 안에서만 다룬다.
_FONT_URI_SCHEME = "resume-font:"
_FONT_PATHS_BY_NAME = {
    "regular": str(_FONT_DIR / "NanumGothic-Regular.ttf"),
    "bold": str(_FONT_DIR / "NanumGothic-Bold.ttf"),
}

# 파일명에 쓰면 안 되는 문자들을 걷어낸다 (Windows/Linux 공통 금지 문자 기준).
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]+')


def get_export_config():
    """제외 목록 싱글톤을 가져온다 (admin 에서 아직 안 만졌으면 자동으로 하나 만든다)."""
    config, _ = ResumeExportConfig.objects.get_or_create(pk=1)
    return config


def _media_path(url_path):
    relative = url_path[len(settings.MEDIA_URL):].lstrip("/")
    candidate = os.path.join(str(settings.MEDIA_ROOT), relative)
    return candidate if os.path.isfile(candidate) else None


def _resolve_media_or_static_path(uri):
    """/static/ 또는 /media/ 로 시작하는 URL 을 실제 디스크 경로로 바꾼다.

    PDF/DOCX 생성 모두 HTTP 요청 없이 로컬에서 바로 이뤄지므로, 이미지·폰트를
    넣으려면 URL 이 아니라 실제 파일 경로가 필요하다. static 쪽은 Django 의
    staticfiles finder 를 그대로 써서 collectstatic 을 아직 안 돌린 로컬
    개발 환경에서도, 운영(collectstatic 이후)에서도 똑같이 동작하게 한다.
    """
    if uri.startswith(settings.MEDIA_URL):
        return _media_path(uri)
    if uri.startswith(settings.STATIC_URL):
        from django.contrib.staticfiles import finders

        relative = uri[len(settings.STATIC_URL):].lstrip("/")
        return finders.find(relative)
    return None


def resume_pdf_link_callback(uri, rel):
    """xhtml2pdf 가 <img src="..."> 등을 실제 파일 경로로 바꿀 때 쓰는 콜백."""
    if uri.startswith(_FONT_URI_SCHEME):
        return _FONT_PATHS_BY_NAME[uri[len(_FONT_URI_SCHEME):]]
    if not (uri.startswith(settings.MEDIA_URL) or uri.startswith(settings.STATIC_URL)):
        return uri  # http(s):// 등 절대 URI 는 그대로 xhtml2pdf 에 맡긴다.
    return _resolve_media_or_static_path(uri) or uri


def _skill_groups():
    from portfolio.models import Skill

    return Skill.group_by_domain(Skill.objects.all().order_by("name"))


def build_resume_context() -> dict:
    """내보내기 설정의 제외 목록을 제외한 전체 이력서/포트폴리오 데이터 템플릿 컨텍스트를 구성합니다.

    Returns:
        dict: PDF 및 DOCX 렌더링에 사용될 모델 객체 및 메타 데이터 딕셔너리.

    Rationale:
        관리자가 제외 목록(ResumeExportConfig)을 빈 값으로 둘 경우 사이트의 최신 전체 데이터가 자동으로 내보내기에 반영되며,
        특정 데이터(예: 비공개 프로젝트)만 제외하도록 세밀히 제어할 수 있는 동적 템플릿 구조를 구축했습니다.
    """
    config = get_export_config()
    profile = Profile.objects.first()

    return {
        "profile": profile,
        "educations": profile.educations.all() if profile else [],
        "skill_groups": _skill_groups(),
        "projects": (
            Project.objects.filter(is_active=True)
            .exclude(pk__in=config.excluded_projects.all())
            .prefetch_related("tech_stacks")
        ),
        "careers": Career.objects.exclude(pk__in=config.excluded_careers.all()),
        "leaderships": Leadership.objects.exclude(pk__in=config.excluded_leaderships.all()),
        "certifications": Activity.objects.filter(type="CERTIFICATION")
            .exclude(pk__in=config.excluded_activities.all()),
        "awards": Activity.objects.filter(type="AWARD")
            .exclude(pk__in=config.excluded_activities.all()),
        "activities": Activity.objects.filter(type="ACTIVITY")
            .exclude(pk__in=config.excluded_activities.all()),
        "generated_on": date.today(),
    }


@contextmanager
def _windows_tempfile_reopen_fix():
    """Windows 환경에서 xhtml2pdf의 TTF 폰트 임시 파일 권한 에러를 우회하는 컨텍스트 매니저.

    Rationale:
        NOTE: xhtml2pdf가 @font-face로 임베드한 TTF 폰트를 임시 파일로 복사한 뒤 reportlab이 해당 파일을 재열 때,
        Windows OS에서는 열려 있는 NamedTemporaryFile의 재오픈을 차단하여 PermissionError가 발생하는 이슈가 존재합니다.
        Linux(PythonAnywhere)에는 해당 문제가 없으므로 os.name == 'nt' 일 때만 파일 delete=False로 패치하여 우회하도록 설계했습니다.
    """
    if os.name != "nt":
        yield
        return

    original = tempfile.NamedTemporaryFile

    def patched(*args, **kwargs):
        kwargs["delete"] = False
        return original(*args, **kwargs)

    tempfile.NamedTemporaryFile = patched
    try:
        yield
    finally:
        tempfile.NamedTemporaryFile = original


def render_resume_pdf_bytes() -> bytes:
    """포트폴리오 HTML 템플릿을 xhtml2pdf 엔진을 이용해 PDF 바이너리 바이트로 렌더링합니다.

    Returns:
        bytes: 생성된 PDF 파일 바이너리 데이터.

    Raises:
        RuntimeError: xhtml2pdf 변환 과정 중 에러 발생 시 예외 throw.

    Rationale:
        ReportLab의 낮은 수준 API로 PDF 레이아웃을 직접 하드코딩하는 대신 HTML/CSS 템플릿 기반으로 xhtml2pdf를 사용함으로써
        스타일 수정이 용이하고 유지보수성이 뛰어난 PDF 내보내기 구조를 달성했습니다.
    """
    pisa = _ensure_pdf_engine_ready()
    html = render_to_string("resume_export/resume_pdf.html", build_resume_context())
    buffer = BytesIO()
    with _windows_tempfile_reopen_fix():
        result = pisa.CreatePDF(
            src=html, dest=buffer, link_callback=resume_pdf_link_callback, encoding="utf-8"
        )
    if result.err:
        raise RuntimeError(f"PDF 생성 실패 (xhtml2pdf err={result.err})")
    return buffer.getvalue()


def build_resume_filename(profile, ext: str, suffix: str = "전체") -> str:
    """안전한 이력서 다운로드 파일명을 생성합니다.

    Args:
        profile (Profile): 프로필 모델 객체.
        ext (str): 확장자 ('pdf' 또는 'docx').
        suffix (str, optional): 파일명 접미사. Defaults to "전체".

    Returns:
        str: 정형화된 다운로드 파일명 문자열 (예: '홍길동_포트폴리오_전체_20260830.pdf').
    """
    safe_name = _UNSAFE_FILENAME_CHARS.sub("", profile.name if profile else "").strip() or "포트폴리오"
    today = date.today().strftime("%Y%m%d")
    return f"{safe_name}_포트폴리오_{suffix}_{today}.{ext}"


#: PDF(resume_pdf.html)와 같은 amber accent — 두 포맷의 톤앤매너를 맞춘다.
_ACCENT_RGB = RGBColor(0x92, 0x40, 0x0E)
_MUTED_RGB = RGBColor(0x66, 0x66, 0x66)


def _add_heading(document, text):
    """섹션 제목을 Heading 1 스타일로 추가한다(문서 아웃라인에도 계층이 드러남)."""
    heading = document.add_heading(text, level=1)
    run = heading.runs[0]
    run.font.size = Pt(13)
    run.font.color.rgb = _ACCENT_RGB
    heading.paragraph_format.space_before = Pt(16)
    heading.paragraph_format.space_after = Pt(6)
    return heading


def _add_entry_title_line(document, title, period=None):
    """제목(왼쪽 정렬)과 기간(오른쪽 정렬)을 탭 정지로 한 줄에 배치한다.

    Rationale:
        PDF 카드의 "제목 ... 기간" 배치와 동일한 정보 구조를 docx 표 없이
        재현한다. python-docx 문단은 flex/float 이 없어 오른쪽 정렬 탭
        정지(tab stop)로 같은 효과를 낸다.
    """
    p = document.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(1)
    if period:
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.3), WD_TAB_ALIGNMENT.RIGHT)
    title_run = p.add_run(title)
    title_run.bold = True
    title_run.font.size = Pt(11)
    if period:
        period_run = p.add_run(f"\t{period}")
        period_run.font.size = Pt(9)
        period_run.font.color.rgb = _MUTED_RGB
    return p


def _add_meta_line(document, text, accent=False):
    """역할/기술 스택처럼 본문보다 한 단계 작은 메타 정보 한 줄."""
    p = document.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.size = Pt(9)
    run.font.color.rgb = _ACCENT_RGB if accent else _MUTED_RGB
    return p


def _add_badge_line(document, text):
    """key_result 처럼 카드 뱃지에 해당하는 강조 한 줄."""
    p = document.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = _ACCENT_RGB
    return p


def _add_body_paragraph(document, text):
    p = document.add_paragraph(text)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(4)
    for run in p.runs:
        run.font.size = Pt(9.5)
    return p


def _add_bullet(document, text):
    p = document.add_paragraph(text, style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.25)
    for run in p.runs:
        run.font.size = Pt(9.5)
    return p


def render_resume_docx_bytes() -> bytes:
    """python-docx 라이브러리를 이용하여 포트폴리오 데이터를 워드 DOCX 바이너리로 생성합니다.

    Returns:
        bytes: 생성된 DOCX 문서 바이너리 바이트.

    Rationale:
        Admin 사용자가 자유롭게 이력서 내용을 편집할 수 있도록 docx 객체를 구성하여 제공합니다.
    """
    context = build_resume_context()
    document = docx.Document()
    document.styles["Normal"].font.name = "맑은 고딕"
    document.styles["Normal"].font.size = Pt(10)

    _add_docx_profile(document, context["profile"])
    _add_docx_skills(document, context["skill_groups"])
    _add_docx_projects(document, context["projects"])
    _add_docx_career_and_education(document, context["careers"], context["educations"])
    _add_docx_leaderships(document, context["leaderships"])
    _add_docx_activities(document, context["certifications"], context["awards"], context["activities"])

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _add_docx_profile(document, profile):
    title = document.add_heading(profile.name if profile else "", level=0)
    title.runs[0].font.size = Pt(24)
    title.paragraph_format.space_after = Pt(2)

    if profile and profile.headline:
        p = document.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(profile.headline)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = _ACCENT_RGB

    if profile and profile.avatar_url:
        image_path = _resolve_media_or_static_path(profile.avatar_url)
        if image_path:
            document.add_picture(image_path, width=Inches(1))

    contact_bits = []
    if profile and profile.show_email_address:
        contact_bits.append(f"Email: {profile.email}")
    if profile and profile.github_url:
        contact_bits.append(f"GitHub: {profile.github_url}")
    if profile and profile.show_birthdate:
        contact_bits.append(f"생년월일: {profile.birthdate:%Y.%m.%d}")
    if profile and profile.english_score:
        contact_bits.append(profile.english_score)
    if contact_bits:
        p = document.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(" | ".join(contact_bits))
        run.font.size = Pt(9)
        run.font.color.rgb = _MUTED_RGB

    if profile and profile.introduction:
        _add_body_paragraph(document, profile.introduction)


def _add_docx_skills(document, skill_groups):
    if not skill_groups:
        return
    _add_heading(document, "기술 스택")
    for group in skill_groups:
        names = ", ".join(skill.name for skill in group["skills"])
        p = document.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        label_run = p.add_run(f"{group['label']}  ")
        label_run.bold = True
        label_run.font.size = Pt(9.5)
        names_run = p.add_run(names)
        names_run.font.size = Pt(9.5)


def _add_docx_projects(document, projects):
    if not projects:
        return
    _add_heading(document, "프로젝트")
    for project in projects:
        _add_entry_title_line(document, project.title, project.period)
        if project.key_result:
            _add_badge_line(document, project.key_result)
        _add_meta_line(document, f"역할: {project.role}")
        tech_names = " · ".join(t.name for t in project.tech_stacks.all())
        if tech_names:
            _add_meta_line(document, f"기술  {tech_names}", accent=True)
        _add_body_paragraph(document, project.description)
        for point in bullets(project.outcome):
            _add_bullet(document, point)


def _add_docx_career_and_education(document, careers, educations):
    if not careers and not educations:
        return
    _add_heading(document, "경력 / 학력")
    for career in careers:
        _add_entry_title_line(document, f"{career.organization} · {career.role}", career.period)
        _add_body_paragraph(document, career.description)
    for edu in educations:
        _add_entry_title_line(document, f"{edu.school} ({edu.status})", edu.period)


def _add_docx_leaderships(document, leaderships):
    if not leaderships:
        return
    _add_heading(document, "리더십 및 활동")
    for lead in leaderships:
        _add_entry_title_line(document, f"{lead.title} · {lead.organization}", lead.period)
        _add_meta_line(document, f"역할: {lead.role}")
        _add_body_paragraph(document, lead.description)


def _add_docx_activities(document, certifications, awards, activities):
    if not certifications and not awards and not activities:
        return
    _add_heading(document, "자격증 / 수상 / 대외활동")
    for item in certifications:
        label = f"[자격증] {item.title}" + (f" · {item.organization}" if item.organization else "")
        _add_entry_title_line(document, label, item.period)
    for item in awards:
        label = f"[수상] {item.title}" + (f" · {item.organization}" if item.organization else "")
        _add_entry_title_line(document, label, item.period)
    for item in activities:
        label = f"[대외활동] {item.title}" + (f" · {item.organization}" if item.organization else "")
        _add_entry_title_line(document, label, item.period)
        if item.description:
            _add_body_paragraph(document, item.description)
