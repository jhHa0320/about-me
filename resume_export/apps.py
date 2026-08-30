from django.apps import AppConfig


class ResumeExportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "resume_export"
    verbose_name = "포트폴리오 PDF 추출"
