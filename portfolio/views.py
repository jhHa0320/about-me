import re

from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import (
    Activity,
    Career,
    Leadership,
    Profile,
    Project,
    Skill,
)

SKILL_GROUPS = [
    ("LANGUAGE", "Language"),
    ("DATA_SCIENCE", "Data Science"),
    ("AI", "AI"),
    ("SECURITY", "Security"),
    ("BACKEND", "Backend"),
    ("ETC", "기타"),
]


def _project_queryset():
    return (
        Project.objects.filter(is_active=True)
        .select_related("type")
        .prefetch_related("categories", "tech_stacks")
    )


def _period_sort_key(period):
    """Sort free-text period strings ('2025.1-2025.9', '2024년 2학기 -') newest first.

    Returns (year, month, ongoing) — all ints so the tuple always compares.
    Anything unparseable sinks to the bottom rather than raising.
    """
    text = period or ""
    years = [int(y) for y in re.findall(r"(20\d{2})", text)]
    year = max(years) if years else 0

    # Only look at the part after the last year, so "2024년 2학기 - 2025년 1학기"
    # is sorted by its end (2025-1학기), not its start.
    tail = text[text.rfind(str(year)):] if year else text

    month = 0
    if "2학기" in tail or "겨울" in tail:
        month = 9
    elif "여름" in tail:
        month = 7
    elif "1학기" in tail:
        month = 3
    else:
        # `\b` does not fire between a digit and Hangul ("7월"), so match on
        # "not another digit" instead.
        m = re.search(r"[.\-/]\s*(\d{1,2})(?!\d)", tail)
        if m and 1 <= int(m.group(1)) <= 12:
            month = int(m.group(1))

    # "2024년 1학기 -" with no end date means it is still running.
    ongoing = 1 if re.search(r"[-~]\s*$", text.strip()) else 0
    return (year, month, ongoing)


def _dedupe_description(description, *against):
    """Hide a description that just restates the title or role.

    Several records were entered with the description copied from the title,
    which renders as the same sentence twice in a row.
    """
    text = re.sub(r"[\s()·,.]+", "", description or "")
    if not text:
        return ""
    for other in against:
        stripped = re.sub(r"[\s()·,.]+", "", other or "")
        if stripped and (text in stripped or stripped in text):
            return ""
    return description


def _norm(text):
    return re.sub(r"[\s()·,./&-]+", "", text or "")


def _timeline_entries():
    """Merge Leadership, Career and Activity into one reverse-chronological list.

    Career rows were previously unreachable — no template rendered them. Now
    that they surface, a Career row that the same organisation already covers
    as a Leadership entry would appear twice, so Leadership wins.
    """
    entries = []
    leadership_keys = set()

    for lead in Leadership.objects.all():
        leadership_keys.add(_norm(lead.title))
        leadership_keys.add(_norm(lead.organization))
        entries.append({
            "kind": "리더십",
            "title": lead.title,
            "organization": lead.organization,
            "period": lead.period,
            "role": lead.role,
            "description": _dedupe_description(lead.description, lead.title, lead.role),
            "url": lead.get_absolute_url(),
            "external": False,
        })

    for career in Career.objects.all():
        key = _norm(career.organization)
        if any(key and (key in k or k in key) for k in leadership_keys if k):
            continue    # 같은 조직이 리더십 항목으로 이미 있음
        entries.append({
            "kind": "경력",
            "title": career.organization,
            "organization": "",
            "period": career.period,
            "role": career.role,
            "description": _dedupe_description(career.description, career.organization, career.role),
            "url": "",
            "external": False,
        })

    for act in Activity.objects.filter(type="ACTIVITY"):
        entries.append({
            "kind": "대외활동",
            "title": act.title,
            "organization": act.organization,
            "period": act.period,
            "role": "",
            "description": _dedupe_description(act.description, act.title),
            "url": act.link or (act.attachment.url if act.attachment else ""),
            "external": True,
        })

    entries.sort(key=lambda e: _period_sort_key(e["period"]), reverse=True)
    return entries


def _skill_groups():
    """Skills grouped by domain (Language / Data Science / AI / Security / Backend / 기타)."""
    skills = (
        Skill.objects.annotate(
            project_count=Count("project", filter=Q(project__is_active=True), distinct=True)
        )
        .order_by("-project_count", "name")
    )
    by_domain = {}
    for skill in skills:
        by_domain.setdefault(skill.domain, []).append(skill)

    return [
        {"key": key, "label": label, "skills": by_domain.get(key, [])}
        for key, label in SKILL_GROUPS
        if by_domain.get(key)
    ]


def home(request):
    profile = Profile.objects.first()
    projects = list(_project_queryset())

    featured = [p for p in projects if p.is_featured]
    others = [p for p in projects if not p.is_featured]

    context = {
        "profile": profile,
        "educations": profile.educations.all() if profile else [],
        "featured_projects": featured,
        "other_projects": others,
        # Chronological — `order` (admin-editable "노출순서") is the primary
        # key so a specific project can still be promoted to the top; it no
        # longer groups featured projects apart from the rest.
        "all_projects": projects,
        "project_total": len(projects),
        "team_project_total": sum(1 for p in projects if p.scope == "TEAM"),
        "skill_groups": _skill_groups(),
        "timeline": _timeline_entries(),
        "cert_dev": Activity.objects.filter(type="CERTIFICATION", cert_category="DEV"),
        "cert_lang": Activity.objects.filter(type="CERTIFICATION", cert_category="LANG"),
        "cert_etc": Activity.objects.filter(type="CERTIFICATION", cert_category="ETC"),
        "cert_total": Activity.objects.filter(type="CERTIFICATION").count(),
        "awards": Activity.objects.filter(type="AWARD"),
    }
    return render(request, "portfolio/home.html", context)


def project_detail(request, project_id):
    project = get_object_or_404(
        Project.objects.select_related("type").prefetch_related("categories", "tech_stacks"),
        pk=project_id,
    )
    related = (
        _project_queryset()
        .filter(tech_stacks__in=project.tech_stacks.all())
        .exclude(pk=project.pk)
        .distinct()[:3]
    )
    return render(
        request,
        "portfolio/project_detail.html",
        {"project": project, "related_projects": related},
    )


def leadership_detail(request, leadership_id):
    leadership = get_object_or_404(Leadership, pk=leadership_id)
    return render(request, "portfolio/leadership_detail.html", {"leadership": leadership})


def skill_projects(request, skill_id):
    skill = get_object_or_404(Skill, pk=skill_id)
    projects = _project_queryset().filter(tech_stacks=skill)
    siblings = (
        Skill.objects.annotate(
            project_count=Count("project", filter=Q(project__is_active=True), distinct=True)
        )
        .filter(project_count__gt=0)
        .order_by("-project_count", "name")
    )
    return render(
        request,
        "portfolio/skill_projects.html",
        {"skill": skill, "projects": projects, "all_skills": siblings},
    )


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /summernote/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
