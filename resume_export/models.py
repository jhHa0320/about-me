from django.db import models

from portfolio.models import Activity, Career, Leadership, Project


class ResumeExportConfig(models.Model):
    """포트폴리오 PDF/DOCX 내보내기 시 제외할 항목을 관리하는 단일 설정 모델.

    Rationale:
        기본 내보내기는 사이트에 등록된 전체 콘텐츠를 포함하도록 동작합니다.
        특정 이력서 제출 상황에서 제외하고 싶은 프로젝트/경력/활동 항목이 있을 경우,
        admin에서 해당 항목들만 선택적으로 필터링하여 실시간 내보내기에 반영되도록 싱글톤 형태로 설계되었습니다.
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
