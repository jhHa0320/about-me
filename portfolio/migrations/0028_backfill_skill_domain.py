"""기존 기술 태그를 분야(Language/Data Science/AI/Security/Backend/기타)로 분류합니다.

`domain` 필드가 새로 생기면서 기존 행은 모두 기본값 'ETC' 로 채워졌습니다.
지금까지 등록된 언어·프레임워크·라이브러리를 실제 쓰임에 맞춰 한 번 분류해 둡니다.
"""

from django.db import migrations

DOMAIN_BY_NAME = {
    "Python": "LANGUAGE",
    "Javascript": "LANGUAGE",
    "C": "LANGUAGE",
    "C++": "LANGUAGE",
    "Data Analysis": "DATA_SCIENCE",
    "Data Visualization": "DATA_SCIENCE",
    "NetworkX": "DATA_SCIENCE",
    "Folium": "DATA_SCIENCE",
    "Machine Learning": "AI",
    "Deep Learning": "AI",
    "NLP": "AI",
    "HuggingFace": "AI",
    "PyTorch": "AI",
    "Multimodal": "AI",
    "Computer Vision": "AI",
    "Django": "BACKEND",
    "FastAPI": "BACKEND",
    "Flask": "BACKEND",
    "MongoDB": "BACKEND",
    "Supabase": "BACKEND",
    "pythonanywhere": "BACKEND",
    "HTML/CSS": "ETC",
    "Bootstrap": "ETC",
    "Netlify": "ETC",
    "Git/Github": "ETC",
    "기타": "ETC",
}


def backfill(apps, schema_editor):
    Skill = apps.get_model("portfolio", "Skill")
    for skill in Skill.objects.all():
        domain = DOMAIN_BY_NAME.get(skill.name)
        if domain:
            skill.domain = domain
            skill.save(update_fields=["domain"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0027_english_score_skill_domain_award_type"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
