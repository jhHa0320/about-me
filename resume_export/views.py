from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.utils.http import content_disposition_header

from portfolio.models import Profile

from .utils import build_resume_filename, render_resume_docx_bytes, render_resume_pdf_bytes


def _file_response(content_bytes, content_type, filename):
    response = HttpResponse(content_bytes, content_type=content_type)
    response.headers["Content-Disposition"] = content_disposition_header(
        as_attachment=True, filename=filename
    )
    return response


def full_resume_pdf(request):
    """공개 사이트의 '포트폴리오 PDF 추출' 버튼용. 로그인 없이 누구나 접근 가능.

    사이트에 있는 프로젝트/경력/자격증·수상·대외활동/리더십을 (관리자가 뺀
    항목만 제외하고) 그 자리에서 실시간으로 PDF 로 만들어 바로 내려준다.
    DB 에 파일을 저장하지 않는다 — 항상 그 순간의 사이트 내용 그대로.
    """
    profile = Profile.objects.first()
    if not profile:
        raise Http404("프로필 정보가 없습니다.")

    pdf_bytes = render_resume_pdf_bytes()
    filename = build_resume_filename(profile, "pdf")
    return _file_response(pdf_bytes, "application/pdf", filename)


@staff_member_required
def full_resume_docx(request):
    """admin 전용 DOCX 다운로드. 공개 PDF 와 같은(제외 목록 반영) 내용을 담는다.

    DOCX 는 다운로드한 사람이 내용을 자유롭게 고칠 수 있어 조작 가능성이
    있으므로 공개 페이지에는 노출하지 않고 admin 에서만 받을 수 있게 한다.
    """
    profile = Profile.objects.first()
    if not profile:
        raise Http404("프로필 정보가 없습니다.")

    docx_bytes = render_resume_docx_bytes()
    filename = build_resume_filename(profile, "docx")
    return _file_response(
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename,
    )
