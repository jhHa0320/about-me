from django.contrib import admin, messages
from django_summernote.admin import SummernoteModelAdmin
from . import paper_sources
from .models import Profile, Skill, Career, Project, Activity, Education, ProjectCategory, ProjectType, Leadership, Paper

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
            'fields': ('title', 'type', 'report_type', 'scope', 'period', 'start_date', 'categories', 'tech_stacks', 'role', 'order')
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

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'year', 'presented_at', 'career', 'is_active')
    list_filter = ('is_active', 'year', 'career')
    search_fields = ('title', 'authors', 'venue')
    fieldsets = (
        ('논문 정보 (주소만 넣으면 자동 입력)', {'fields': ('source_url', 'title', 'authors', 'venue', 'year')}),
        ('발표', {'fields': ('presented_at', 'career', 'summary', 'is_active')}),
        ('발표자료', {'fields': ('slides_file', 'slides_url')}),
    )
    actions = ['refetch_metadata']

    @admin.action(description="논문 주소에서 제목·저자·학회·연도 다시 불러오기 (덮어쓰기)")
    def refetch_metadata(self, request, queryset):
        done = 0
        for paper in queryset.exclude(source_url=''):
            try:
                paper.apply_metadata(paper_sources.fetch_metadata(paper.source_url), overwrite=True)
            except paper_sources.MetaError as exc:
                self.message_user(request, f"{paper}: {exc}", messages.WARNING)
                continue
            paper.save()
            done += 1
        self.message_user(request, f"{done}건 갱신했습니다.")


@admin.register(Leadership)
class LeadershipAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('order', 'title', 'organization', 'period', 'role')
    list_editable = ('order',)
    list_display_links = ('title',)
