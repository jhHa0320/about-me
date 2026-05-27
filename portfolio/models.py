from django.db import models

class Profile(models.Model):
    name = models.CharField(max_length=100, verbose_name="이름")
    birthdate = models.DateField(verbose_name="생년월일")
    email = models.EmailField(verbose_name="이메일")
    github_url = models.URLField(blank=True, verbose_name="Github 주소")
    introduction = models.TextField(blank=True, verbose_name="자기소개")
    profile_image = models.ImageField(upload_to='profile/', blank=True, null=True, verbose_name="프로필 이미지")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "프로필"
        verbose_name_plural = "프로필"

class Education(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='educations', verbose_name="프로필")
    period = models.CharField(max_length=50, verbose_name="기간")
    school = models.CharField(max_length=100, verbose_name="학교명")
    status = models.CharField(max_length=20, verbose_name="상태 (졸업/재학/중퇴 등)")
    
    def __str__(self):
        return f"{self.school} ({self.status})"
    
    class Meta:
        verbose_name = "학력"
        verbose_name_plural = "학력"
        ordering = ['-id']

class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('USING', '사용 중 🔥'),
        ('MAINTAIN', '기능 유지 ✅'),
        ('EXPERIENCE', '경험 있음 🕰️'),
    ]
    name = models.CharField(max_length=50, verbose_name="기술명")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="카테고리")
    description = models.CharField(max_length=200, blank=True, verbose_name="설명")
    icon = models.ImageField(upload_to='skills/', blank=True, null=True, verbose_name="아이콘")

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    class Meta:
        verbose_name = "기술"
        verbose_name_plural = "기술"

class Career(models.Model):
    organization = models.CharField(max_length=100, verbose_name="조직/회사")
    role = models.CharField(max_length=100, verbose_name="역할")
    period = models.CharField(max_length=50, verbose_name="기간")
    description = models.TextField(verbose_name="설명")

    def __str__(self):
        return f"{self.organization} - {self.role}"

    class Meta:
        verbose_name = "경력"
        verbose_name_plural = "경력"
        ordering = ['-id']

class ProjectCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name="카테고리명")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "프로젝트 카테고리"
        verbose_name_plural = "프로젝트 카테고리"

class ProjectType(models.Model):
    name = models.CharField(max_length=50, verbose_name="유형명 (예: 핵심, 성장, 기록)")
    description = models.TextField(verbose_name="유형 설명 (버튼 호버 시 표시)")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "프로젝트 유형"
        verbose_name_plural = "프로젝트 유형"
        ordering = ['order', 'id']

class Project(models.Model):
    type = models.ForeignKey(ProjectType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="프로젝트 유형")
    title = models.CharField(max_length=100, verbose_name="프로젝트명")
    period = models.CharField(max_length=50, default='', verbose_name="기간")
    start_date = models.DateField(null=True, blank=True, verbose_name="시작일 (정렬용)")
    categories = models.ManyToManyField(ProjectCategory, verbose_name="분류 (복수선택 가능)")
    tech_stacks = models.ManyToManyField(Skill, verbose_name="사용 기술 (복수선택 가능)")
    role = models.CharField(max_length=100, default='', verbose_name="나의 역할")
    outcome = models.TextField(blank=True, default='', verbose_name="성과")
    description = models.TextField(verbose_name="설명 (요약)")
    content = models.TextField(blank=True, default='', verbose_name="상세 내용 (보고서)")
    github_url = models.URLField(blank=True, verbose_name="Github 링크")
    demo_url = models.URLField(blank=True, verbose_name="데모 링크")
    image = models.ImageField(upload_to='projects/', blank=True, null=True, verbose_name="대표 이미지")
    order = models.IntegerField(default=0, verbose_name="정렬 순서 (높을수록 먼저)")
    
    SCOPE_CHOICES = [
        ('INDIVIDUAL', '개인 프로젝트'),
        ('TEAM', '팀 프로젝트'),
    ]
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='INDIVIDUAL', verbose_name="프로젝트 범위 (개인/팀)")
    
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "프로젝트"
        verbose_name_plural = "프로젝트"
        ordering = ['-order', '-start_date', '-id']

class Activity(models.Model):
    TYPE_CHOICES = [
        ('CERTIFICATION', 'Certification'),
        ('ACTIVITY', 'Activity'),
    ]
    CERT_CATEGORY_CHOICES = [
        ('DEV', '개발'),
        ('LANG', '외국어'),
        ('ETC', '기타'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='ACTIVITY', verbose_name="구분")
    cert_category = models.CharField(
        max_length=10, choices=CERT_CATEGORY_CHOICES, blank=True, default='',
        verbose_name="자격증 분류 (Certification일 때만)"
    )
    title = models.CharField(max_length=100, verbose_name="활동/자격증명")
    organization = models.CharField(max_length=100, blank=True, verbose_name="주최/시행 기관")
    description = models.TextField(blank=True, verbose_name="설명")
    period = models.CharField(max_length=50, blank=True, verbose_name="기간")
    link = models.URLField(blank=True, verbose_name="관련 링크")
    attachment = models.FileField(upload_to='activities/', blank=True, null=True, verbose_name="첨부 파일")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title}"

    class Meta:
        verbose_name = "활동/자격증"
        verbose_name_plural = "활동/자격증"
        ordering = ['-order', '-id']

class Leadership(models.Model):
    title = models.CharField(max_length=100, verbose_name="활동명")
    organization = models.CharField(max_length=100, verbose_name="단체/조직명")
    period = models.CharField(max_length=50, verbose_name="기간")
    role = models.CharField(max_length=100, verbose_name="역할")
    description = models.TextField(verbose_name="설명")
    content = models.TextField(blank=True, default='', verbose_name="상세 내용 (보고서)")
    outcome = models.TextField(blank=True, default='', verbose_name="성과")
    image = models.ImageField(upload_to='leadership/', blank=True, null=True, verbose_name="대표 이미지")
    link = models.URLField(blank=True, verbose_name="관련 링크")
    order = models.IntegerField(default=0, verbose_name="정렬 순서 (높을수록 먼저)")

    class Meta:
        verbose_name = "리더십 및 경험"
        verbose_name_plural = "리더십 및 경험"
        ordering = ['-order', '-id']

    def __str__(self):
        return f"{self.title} - {self.organization}"
