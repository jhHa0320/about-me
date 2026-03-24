from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0020_project_scope'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='start_date',
            field=models.DateField(blank=True, null=True, verbose_name='시작일 (정렬용)'),
        ),
        migrations.AlterModelOptions(
            name='project',
            options={
                'ordering': ['-order', '-start_date', '-id'],
                'verbose_name': '프로젝트',
                'verbose_name_plural': '프로젝트',
            },
        ),
    ]
