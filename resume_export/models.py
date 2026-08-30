from django.db import models

from portfolio.models import Activity, Career, Leadership, Project


class ResumeExportConfig(models.Model):
    """포트폴리오 PDF/DOCX 추출에서 뺄 항목을 관리하는 싱글톤 설정.

    기본은 전체 포함이다 — 여기 추가된(=제외된) 항목만 내보내기에서 빠지고,
    나머지는 사이트에 있는 그대로 실시간으로 반영된다. 새 프로젝트/경력을
    사이트에 추가하면 이 목록에 넣지 않는 한 자동으로 내보내기에 포함된다.
    """

    excluded_projects = models.ManyToManyField(
        Project, related_name="+", blank=True, verbose_name="내보내기에서 제외할 프로젝트",
    )
    excluded_careers = models.ManyToManyField(
        Career, related_name="+", blank=True, verbose_name="내보내기에서 제외할 경력",
    )
    excluded_leaderships = models.ManyToManyField(
        Leadership, related_name="+", blank=True, verbose_name="내보내기에서 제외할 리더십/활동",
    )
    excluded_activities = models.ManyToManyField(
        Activity, related_name="+", blank=True, verbose_name="내보내기에서 제외할 자격증/수상/대외활동",
    )

    def __str__(self):
        return "포트폴리오 PDF 추출 설정"

    class Meta:
        verbose_name = "포트폴리오 PDF 추출 설정"
        verbose_name_plural = "포트폴리오 PDF 추출 설정"
