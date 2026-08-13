from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin
from .models import Profile, Skill, Career, Project, Activity, Education, ProjectCategory, ProjectType, Leadership

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'description')
    list_editable = ('order',)

@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'headline', 'email')
    fieldsets = (
        ('첫 화면(Hero)에 보이는 내용', {
            'fields': ('name', 'headline', 'introduction', 'english_score', 'profile_image'),
            'description': (
                '한 줄 직군과 자기소개를 채우면 첫 화면 이름 아래에 바로 노출됩니다. '
                '학력은 등록된 학력 중 가장 최근 항목이 자동으로 표시됩니다. '
                '영어 성적은 채워두면 학력 아래에 노출되고, 비워두면 표시되지 않습니다.'
            ),
        }),
        ('연락처 / 링크', {
            'fields': ('email', 'show_email_address', 'github_url', 'resume_url'),
        }),
        ('비공개 정보', {
            'fields': ('birthdate', 'show_birthdate'),
            'description': '노출 체크를 끄면 사이트에 표시되지 않습니다. 값은 그대로 보존됩니다.',
        }),
    )

    def has_add_permission(self, request):
        return not Profile.objects.exists()

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('school', 'period', 'status')
    list_filter = ('status',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'category')
    list_editable = ('domain',)
    list_filter = ('domain', 'category')

@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ('organization', 'role', 'period')
    list_filter = ('role',)

@admin.register(Project)
class ProjectAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('order', 'title', 'period', 'is_featured', 'key_result', 'scope', 'role', 'is_active')
    list_editable = ('order', 'is_featured', 'is_active', 'scope')
    list_display_links = ('title',)
    list_filter = ('is_featured', 'type', 'scope', 'categories', 'tech_stacks', 'is_active')
    filter_horizontal = ('categories', 'tech_stacks')
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'type', 'scope', 'period', 'start_date', 'categories', 'tech_stacks', 'role', 'order')
        }),
        ('노출 설정', {
            'fields': ('is_active', 'is_featured'),
            'description': 'Featured 로 체크한 프로젝트는 첫 화면 상단에 크게 노출됩니다. 3개 내외를 권장합니다.',
        }),
        ('상세 내용', {
            'fields': ('description', 'key_result', 'outcome', 'content', 'image')
        }),
        ('링크', {
            'fields': ('github_url', 'demo_url')
        }),
    )

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('order', 'type', 'title', 'organization', 'period')
    list_editable = ('order', 'type')
    list_display_links = ('title',)
    list_filter = ('type',)

@admin.register(Leadership)
class LeadershipAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('order', 'title', 'organization', 'period', 'role')
    list_editable = ('order',)
    list_display_links = ('title',)
