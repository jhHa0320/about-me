"""resume_export 앱의 뷰 및 내보내기 유틸리티 함수 단위 테스트."""

from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portfolio.models import Profile
from resume_export.utils import (
    build_resume_context,
    build_resume_filename,
    render_resume_docx_bytes,
    render_resume_pdf_bytes,
)


class ResumeExportViewsTest(TestCase):
    """PDF 및 DOCX 내보내기 뷰에 대한 응답 및 접근 권한 테스트."""

    def setUp(self):
        """테스트 데이터(프로필 및 계정)를 설정합니다."""
        self.profile = Profile.objects.create(
            name="홍길동",
            headline="Backend Developer",
            birthdate=date(1995, 1, 1),
            email="hong@example.com",
            introduction="안녕하세요. 백엔드 개발자입니다.",
        )
        self.user = User.objects.create_user(
            username="normaluser", password="password123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="password123", is_staff=True
        )

    def test_full_resume_pdf_success(self):
        """공개 PDF 내보내기 뷰가 정상적으로 200 OK와 PDF 응답을 반환하는지 테스트합니다.

        Rationale:
            PDF 내보내기는 비로그인 방문자도 접근 가능한 공개 기능이어야 합니다.
        """
        response = self.client.get(reverse("resume_generate_full"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_full_resume_pdf_no_profile(self):
        """프로필이 없는 환경에서 PDF 뷰 접근 시 404를 반환하는지 테스트합니다."""
        Profile.objects.all().delete()
        response = self.client.get(reverse("resume_generate_full"))
        self.assertEqual(response.status_code, 404)

    def test_full_resume_docx_requires_staff(self):
        """일반 사용자나 비로그인 사용자가 DOCX 내보내기 뷰 접근 시 로그인 페이지로 리다이렉트되는지 테스트합니다.

        Rationale:
            NOTE: DOCX 내보내기는 어드민 스태프 전용 기능이므로 보안 통제가 유효한지 확인합니다.
        """
        response = self.client.get(reverse("resume_generate_docx"))
        self.assertEqual(response.status_code, 302)

        self.client.login(username="normaluser", password="password123")
        response = self.client.get(reverse("resume_generate_docx"))
        self.assertEqual(response.status_code, 302)

    def test_full_resume_docx_staff_success(self):
        """스태프 로그인 유저가 DOCX 내보내기 뷰 접근 시 200 OK와 DOCX 파일 응답을 반환하는지 테스트합니다."""
        self.client.login(username="staffuser", password="password123")
        response = self.client.get(reverse("resume_generate_docx"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"PK"))


class ResumeExportUtilsTest(TestCase):
    """resume_export.utils 모듈의 헬퍼 함수 단위 테스트."""

    def setUp(self):
        self.profile = Profile.objects.create(
            name="홍길동",
            headline="Data Engineer",
            birthdate=date(1998, 5, 20),
            email="test@example.com",
        )

    def test_build_resume_filename(self):
        """파일명 생성 유틸리티가 특수문자를 올바르게 제거하고 정형화된 파일명을 돌려주는지 테스트합니다."""
        filename = build_resume_filename(self.profile, "pdf")
        today_str = date.today().strftime("%Y%m%d")
        expected = f"홍길동_포트폴리오_전체_{today_str}.pdf"
        self.assertEqual(filename, expected)

    def test_build_resume_context(self):
        """이력서 컨텍스트 생성 시 프로필 정보가 정상적으로 매핑되는지 테스트합니다."""
        context = build_resume_context()
        self.assertEqual(context["profile"], self.profile)
        self.assertEqual(context["generated_on"], date.today())

    def test_render_resume_pdf_bytes(self):
        """PDF 바이너리 바이트 생성 함수가 정상 작동하는지 테스트합니다."""
        pdf_bytes = render_resume_pdf_bytes()
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_render_resume_docx_bytes(self):
        """DOCX 바이너리 바이트 생성 함수가 정상 작동하는지 테스트합니다."""
        docx_bytes = render_resume_docx_bytes()
        self.assertIsInstance(docx_bytes, bytes)
        self.assertTrue(docx_bytes.startswith(b"PK"))
