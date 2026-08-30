from django.urls import path

from . import views

urlpatterns = [
    path("full/", views.full_resume_pdf, name="resume_generate_full"),
    path("full.docx/", views.full_resume_docx, name="resume_generate_docx"),
]
