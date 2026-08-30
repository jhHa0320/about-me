from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.utils.http import content_disposition_header

from portfolio.models import Profile

from .utils import build_resume_filename, render_resume_docx_bytes, render_resume_pdf_bytes


def _file_response(content_bytes: bytes, content_type: str, filename: str) -> HttpResponse:
    """바이알 패킷 바이트 데이터로부터 파일 다운로드 HTTP 응답 객체를 생성합니다.

    Args:
        content_bytes (bytes): 생성된 파일의 바이너리 데이터.
        content_type (str): MIME 타입 (예: 'application/pdf').
        filename (str): 클라이언트 다운로드 파일명.

    Returns:
        HttpResponse: Content-Disposition attachment 헤더가 추가된 HTTP 응답.
    """
    response = HttpResponse(content_bytes, content_type=content_type)
    response.headers["Content-Disposition"] = content_disposition_header(
        as_attachment=True, filename=filename
    )
    return response


def full_resume_pdf(request):
    """사이트 포트폴리오의 실시간 PDF 다운로드 뷰.

    Args:
        request: HttpRequest 객체.

    Returns:
        HttpResponse: PDF 다운로드 바이너리 파일 응답.

    Raises:
        Http404: 등록된 프로필 데이터가 없을 경우 발생.

    Rationale:
        공개 사용자가 포트폴리오 웹 사이트 상에서 원클릭으로 최신 상태의 PDF 포트폴리오를 다운로드할 수 있도록 지원합니다.
        서버 디스크에 별도 PDF 파일로 동적 생성하여 저장하지 않으므로 데이터 동기화 이슈가 발생하지 않습니다.
    """
    profile = Profile.objects.first()
    if not profile:
        raise Http404("프로필 정보가 없습니다.")

    pdf_bytes = render_resume_pdf_bytes()
    filename = build_resume_filename(profile, "pdf")
    return _file_response(pdf_bytes, "application/pdf", filename)


@staff_member_required
def full_resume_docx(request):
    """관리자 전용 실시간 DOCX 다운로드 뷰.

    Args:
        request: HttpRequest 객체.

    Returns:
        HttpResponse: DOCX 다운로드 바이너리 파일 응답.

    Raises:
        Http404: 등록된 프로필 데이터가 없을 경우 발생.

    Rationale:
        NOTE: DOCX 문서는 수정이 용이하여 원본 훼손 우려가 있으므로 @staff_member_required를 통해
        공개 페이지가 아닌 Admin 관리자 계정에서만 내려받아 편집이 가능하도록 보안을 적용했습니다.
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
