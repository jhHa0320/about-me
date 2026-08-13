# Generated manually — help_text-only change (정보보호 문구 추가), no schema impact.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0025_seed_featured_and_key_results"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="headline",
            field=models.CharField(
                blank=True,
                default="",
                help_text="예: Data · AI · Backend · Security / 비워두면 표시되지 않습니다.",
                max_length=120,
                verbose_name="한 줄 직군 (Hero 이름 위)",
            ),
        ),
    ]
