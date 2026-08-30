from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ResumeExportConfig


@admin.register(ResumeExportConfig)
class ResumeExportConfigAdmin(admin.ModelAdmin):
    filter_horizontal = (
        "excluded_projects", "excluded_careers", "excluded_leaderships", "excluded_activities",
    )
    readonly_fields = ("export_actions",)
    fieldsets = (
        (None, {
            "fields": ("export_actions",),
            "description": (
                "기본은 전체 포함입니다. 아래에서 고른 항목만 PDF/DOCX 내보내기에서 빠지고, "
                "나머지(새로 추가한 프로젝트/경력 포함)는 실시간으로 그대로 반영됩니다."
            ),
        }),
        ("프로젝트 제외", {"fields": ("excluded_projects",)}),
        ("경력 제외", {"fields": ("excluded_careers",)}),
        ("리더십/활동 제외", {"fields": ("excluded_leaderships",)}),
        ("자격증/수상/대외활동 제외", {"fields": ("excluded_activities",)}),
    )

    def has_add_permission(self, request):
        return not ResumeExportConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="내보내기")
    def export_actions(self, obj):
        pdf_url = reverse("resume_generate_full")
        docx_url = reverse("resume_generate_docx")
        return format_html(
            '<a class="button" href="{}" target="_blank">지금 PDF 다운로드</a> '
            '<a class="button" href="{}" target="_blank">지금 DOCX 다운로드</a> '
            '<p style="margin-top:6px;color:#666;">현재 제외 목록 기준으로 그 자리에서 새로 만들어 '
            '바로 내려받습니다. PDF는 사이트에도 공개 버튼이 있고, DOCX는 편집 가능한 파일이라 '
            "관리자만 받을 수 있습니다.</p>",
            pdf_url, docx_url,
        )
