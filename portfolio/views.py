from django.shortcuts import render, get_object_or_404
from .models import Profile, Skill, Career, Project, Activity, Education, ProjectType, Leadership



def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return render(request, 'portfolio/project_detail.html', {'project': project})

def home(request):
    profile = Profile.objects.first()
    all_skills = list(Skill.objects.all())
    skills_using = [s for s in all_skills if s.category == 'USING']
    skills_maintain = [s for s in all_skills if s.category == 'MAINTAIN']
    skills_experience = [s for s in all_skills if s.category == 'EXPERIENCE']
    educations = profile.educations.all() if profile else []
    careers = Career.objects.all()
    projects = Project.objects.filter(is_active=True).select_related('type').prefetch_related('categories', 'tech_stacks')
    project_types = ProjectType.objects.all()
    project_skills = Skill.objects.filter(project__isnull=False).distinct()
    activities = Activity.objects.all()
    leaderships = Leadership.objects.all()

    context = {
        'profile': profile,
        'skills_using': skills_using,
        'skills_maintain': skills_maintain,
        'skills_experience': skills_experience,
        'educations': educations,
        'careers': careers,
        'projects': projects,
        'project_types': project_types,
        'project_skills': project_skills,
        'activities': activities,
        'leaderships': leaderships,
    }
    return render(request, 'portfolio/home.html', context)


def leadership_detail(request, leadership_id):
    leadership = get_object_or_404(Leadership, pk=leadership_id)
    return render(request, 'portfolio/leadership_detail.html', {'leadership': leadership})
