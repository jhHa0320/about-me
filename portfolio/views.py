from django.shortcuts import render, get_object_or_404
from .models import Profile, Skill, Project, Activity, Education, ProjectType, Leadership


def home(request):
    profile = Profile.objects.first()
    all_skills = list(Skill.objects.all())
    skills_using = [s for s in all_skills if s.category == 'USING']
    skills_maintain = [s for s in all_skills if s.category == 'MAINTAIN']
    skills_experience = [s for s in all_skills if s.category == 'EXPERIENCE']
    educations = profile.educations.all() if profile else []
    projects = Project.objects.filter(is_active=True).select_related('type').prefetch_related('categories', 'tech_stacks')
    project_types = ProjectType.objects.all()
    project_skills = Skill.objects.filter(project__isnull=False).distinct()
    cert_dev = Activity.objects.filter(type='CERTIFICATION', cert_category='DEV').order_by('-order', '-id')
    cert_lang = Activity.objects.filter(type='CERTIFICATION', cert_category='LANG').order_by('-order', '-id')
    activities = Activity.objects.filter(type='ACTIVITY').order_by('-order', '-id')
    leaderships = Leadership.objects.all()

    context = {
        'profile': profile,
        'skills_using': skills_using,
        'skills_maintain': skills_maintain,
        'skills_experience': skills_experience,
        'educations': educations,
        'projects': projects,
        'project_types': project_types,
        'project_skills': project_skills,
        'cert_dev': cert_dev,
        'cert_lang': cert_lang,
        'activities': activities,
        'leaderships': leaderships,
    }
    return render(request, 'portfolio/home.html', context)


def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return render(request, 'portfolio/project_detail.html', {'project': project})


def leadership_detail(request, leadership_id):
    leadership = get_object_or_404(Leadership, pk=leadership_id)
    return render(request, 'portfolio/leadership_detail.html', {'leadership': leadership})


def skill_projects(request, skill_id):
    skill = get_object_or_404(Skill, pk=skill_id)
    projects = Project.objects.filter(
        tech_stacks=skill, is_active=True
    ).select_related('type').prefetch_related('categories', 'tech_stacks')
    all_skills = Skill.objects.filter(project__isnull=False).distinct()
    return render(request, 'portfolio/skill_projects.html', {
        'skill': skill,
        'projects': projects,
        'all_skills': all_skills,
    })
