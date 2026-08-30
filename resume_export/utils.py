import os
import re
import tempfile
from contextlib import contextmanager
from datetime import date
from io import BytesIO
from pathlib import Path

import docx
from docx.shared import Inches, Pt
from django.conf import settings
from django.template.loader import render_to_string
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

from portfolio.models import Activity, Career, Leadership, Profile, Project
from portfolio.templatetags.portfolio_extras import bullets

from .models import ResumeExportConfig

# 한글 PDF 텍스트용 폰트를 등록한다. reportlab 내장 CID 폰트(HYGothic-Medium)는
# 한글은 문제없지만 영문/숫자 글자폭이 어색하게 벌어져서, 한글·영문이 같이
# 자연스러운 나눔고딕 TTF 를 직접 번들링해서 쓴다 (resume_export/static/.../fonts/).
_FONT_DIR = Path(__file__).resolve().parent / "static" / "resume_export" / "fonts"
_KOREAN_FONT = "NanumGothic"
_KOREAN_FONT_BOLD = "NanumGothic-Bold"
pdfmetrics.registerFont(TTFont(_KOREAN_FONT, str(_FONT_DIR / "NanumGothic-Regular.ttf")))
pdfmetrics.registerFont(TTFont(_KOREAN_FONT_BOLD, str(_FONT_DIR / "NanumGothic-Bold.ttf")))
pdfmetrics.registerFontFamily(
    _KOREAN_FONT, normal=_KOREAN_FONT, bold=_KOREAN_FONT_BOLD,
    italic=_KOREAN_FONT, boldItalic=_KOREAN_FONT_BOLD,
)

SKILL_DOMAIN_ORDER = [
    ("LANGUAGE", "Language"),
    ("DATA_SCIENCE", "Data Science"),
    ("AI", "AI"),
    ("SECURITY", "Security"),
    ("BACKEND", "Backend"),
    ("ETC", "기타"),
]

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
    if not (uri.startswith(settings.MEDIA_URL) or uri.startswith(settings.STATIC_URL)):
        return uri  # http(s):// 등 절대 URI 는 그대로 xhtml2pdf 에 맡긴다.
    return _resolve_media_or_static_path(uri) or uri


def _skill_groups():
    from portfolio.models import Skill

    skills = Skill.objects.all().order_by("name")
    by_domain = {}
    for skill in skills:
        by_domain.setdefault(skill.domain, []).append(skill)

    return [
        {"key": key, "label": label, "skills": by_domain.get(key, [])}
        for key, label in SKILL_DOMAIN_ORDER
        if by_domain.get(key)
    ]


def build_resume_context():
    """사이트의 모든 내용에서, 내보내기 설정의 제외 목록만 뺀 컨텍스트.

    제외 목록이 비어있으면(기본 상태) 사이트에 있는 모든 활성 콘텐츠가 그대로
    반영된다 — 새 프로젝트/경력을 사이트에 추가하면 별도 작업 없이 바로
    다음 내보내기에 포함된다.
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
    """xhtml2pdf 가 @font-face 로 임베드한 TTF 를 임시파일로 복사한 뒤 reportlab 이
    그 파일을 다시 여는데, Windows 는 열려 있는 NamedTemporaryFile 을 재오픈하는 걸
    막아서(POSIX 는 허용) PermissionError 가 난다. Linux(PythonAnywhere)에는 없는
    문제라 Windows 에서만, xhtml2pdf 호출 구간에서만 좁게 우회한다.
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


def render_resume_pdf_bytes():
    html = render_to_string("resume_export/resume_pdf.html", build_resume_context())
    buffer = BytesIO()
    with _windows_tempfile_reopen_fix():
        result = pisa.CreatePDF(
            src=html, dest=buffer, link_callback=resume_pdf_link_callback, encoding="utf-8"
        )
    if result.err:
        raise RuntimeError(f"PDF 생성 실패 (xhtml2pdf err={result.err})")
    return buffer.getvalue()


def build_resume_filename(profile, ext, suffix="전체"):
    safe_name = _UNSAFE_FILENAME_CHARS.sub("", profile.name if profile else "").strip() or "포트폴리오"
    today = date.today().strftime("%Y%m%d")
    return f"{safe_name}_포트폴리오_{suffix}_{today}.{ext}"


def _add_heading(document, text):
    heading = document.add_heading(text, level=1)
    heading.runs[0].font.size = Pt(14)


def render_resume_docx_bytes():
    """admin 전용 DOCX 내보내기. PDF 와 같은 컨텍스트(제외 목록 반영)를 그대로 쓴다."""
    context = build_resume_context()
    profile = context["profile"]
    document = docx.Document()

    title = document.add_heading(profile.name if profile else "", level=0)
    title.runs[0].font.size = Pt(22)

    if profile and profile.headline:
        document.add_paragraph(profile.headline)

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
        document.add_paragraph(" | ".join(contact_bits))

    if profile and profile.introduction:
        document.add_paragraph(profile.introduction)

    if context["skill_groups"]:
        _add_heading(document, "기술 스택")
        for group in context["skill_groups"]:
            names = ", ".join(skill.name for skill in group["skills"])
            p = document.add_paragraph()
            p.add_run(f"{group['label']}: ").bold = True
            p.add_run(names)

    if context["projects"]:
        _add_heading(document, "프로젝트")
        for project in context["projects"]:
            p = document.add_paragraph()
            title_text = project.title
            if project.key_result:
                title_text += f" [{project.key_result}]"
            p.add_run(f"{title_text}  ").bold = True
            p.add_run(project.period)

            meta = f"역할: {project.role}"
            tech_names = ", ".join(t.name for t in project.tech_stacks.all())
            if tech_names:
                meta += f" | 기술: {tech_names}"
            document.add_paragraph(meta)

            document.add_paragraph(project.description)
            for point in bullets(project.outcome):
                document.add_paragraph(point, style="List Bullet")

    if context["careers"] or context["educations"]:
        _add_heading(document, "경력 / 학력")
        for career in context["careers"]:
            p = document.add_paragraph()
            p.add_run(f"{career.organization} - {career.role}").bold = True
            document.add_paragraph(career.period)
            document.add_paragraph(career.description)
        for edu in context["educations"]:
            p = document.add_paragraph()
            p.add_run(f"{edu.school} ({edu.status})").bold = True
            document.add_paragraph(edu.period)

    if context["leaderships"]:
        _add_heading(document, "리더십 및 활동")
        for lead in context["leaderships"]:
            p = document.add_paragraph()
            p.add_run(f"{lead.title} - {lead.organization} ({lead.role})").bold = True
            document.add_paragraph(lead.period)
            document.add_paragraph(lead.description)

    if context["certifications"] or context["awards"] or context["activities"]:
        _add_heading(document, "자격증 / 수상 / 대외활동")
        for item in context["certifications"]:
            document.add_paragraph(f"[자격증] {item.title} - {item.organization}")
        for item in context["awards"]:
            document.add_paragraph(f"[수상] {item.title} - {item.organization}")
        for item in context["activities"]:
            document.add_paragraph(f"[대외활동] {item.title} - {item.organization}")

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
