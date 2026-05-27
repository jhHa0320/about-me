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
    list_display = ('name', 'email')

    def has_add_permission(self, request):
        return not Profile.objects.exists()

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('school', 'period', 'status')
    list_filter = ('status',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ('organization', 'role', 'period')
    list_filter = ('role',)

@admin.register(Project)
class ProjectAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('order', 'title', 'period', 'start_date', 'type', 'scope', 'role', 'is_active')
    list_editable = ('order', 'is_active', 'type', 'scope', 'start_date')
    list_display_links = ('title',)
    list_filter = ('type', 'scope', 'categories', 'tech_stacks', 'is_active')
    filter_horizontal = ('categories', 'tech_stacks')
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'type', 'scope', 'period', 'start_date', 'categories', 'tech_stacks', 'role', 'order', 'is_active')
        }),
        ('상세 내용', {
            'fields': ('description', 'outcome', 'content', 'image')
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
