from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0026_alter_profile_headline_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="english_score",
            field=models.CharField(
                blank=True,
                default="",
                help_text="예: TOEIC 900, OPIc IH / 비워두면 표시되지 않습니다.",
                max_length=60,
                verbose_name="영어 성적 (Hero 학력 아래)",
            ),
        ),
        migrations.AddField(
            model_name="skill",
            name="domain",
            field=models.CharField(
                choices=[
                    ("LANGUAGE", "Language"),
                    ("DATA_SCIENCE", "Data Science"),
                    ("AI", "AI"),
                    ("SECURITY", "Security"),
                    ("BACKEND", "Backend"),
                    ("ETC", "기타"),
                ],
                default="ETC",
                help_text="첫 화면 '기술' 섹션에서 이 값 기준으로 묶입니다.",
                max_length=20,
                verbose_name="분야 (기술 섹션 그룹)",
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="type",
            field=models.CharField(
                choices=[
                    ("CERTIFICATION", "Certification"),
                    ("AWARD", "Award"),
                    ("ACTIVITY", "Activity"),
                ],
                default="ACTIVITY",
                max_length=20,
                verbose_name="구분",
            ),
        ),
    ]
