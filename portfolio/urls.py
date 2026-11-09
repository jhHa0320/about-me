from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('leadership/<int:leadership_id>/', views.leadership_detail, name='leadership_detail'),
    path('archive/', views.archive, name='archive'),
    path('career/<int:career_id>/archive/', views.archive, name='career_archive'),
    path('skill/<int:skill_id>/projects/', views.skill_projects, name='skill_projects'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
]
