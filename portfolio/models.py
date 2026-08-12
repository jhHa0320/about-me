from django.db import models

class Profile(models.Model):
    name = models.CharField(max_length=100, verbose_name="이름")
    headline = models.CharField(
        max_length=120, blank=True, default='',
        verbose_name="한 줄 직군 (Hero 이름 위)",
        help_text="예: Data · AI · Backend / 비워두면 표시되지 않습니다.",
    )
    birthdate = models.DateField(verbose_name="생년월일")
    show_birthdate = models.BooleanField(
        default=False, verbose_name="생년월일 화면 노출",
        help_text="끄면 사이트에 표시되지 않습니다. 데이터는 그대로 보존됩니다.",
    )
    email = models.EmailField(verbose_name="이메일")
    show_email_address = models.BooleanField(
        default=False, verbose_name="이메일 주소 원문 노출",
        help_text="끄면 'Email' 버튼으로만 표시됩니다(스팸 수집 방지). 링크는 그대로 동작합니다.",
    )
    github_url = models.URLField(blank=True, verbose_name="Github 주소")
    resume_url = models.URLField(blank=True, default='', verbose_name="이력서 링크 (선택)")
    introduction = models.TextField(
        blank=True, verbose_name="자기소개 (Hero 소개 문장)",
        help_text="2~3문장 이내를 권장합니다. 비워두면 표시되지 않습니다.",
    )
    profile_image = models.ImageField(upload_to='profile/', blank=True, null=True, verbose_name="프로필 이미지")

    #: Longest edge of the generated avatar. The hero renders it at 200 CSS px,
    #: so this covers 2x displays with room to spare.
    AVATAR_MAX_PX = 480

    def __str__(self):
        return self.name

    @property
    def avatar_url(self):
        """URL of a small derived copy of `profile_image`.

        The uploaded original is never modified or deleted — the thumbnail is
        written alongside it and reused on later requests. Falls back to the
        original if Pillow cannot process the file.
        """
        if not self.profile_image:
            return ""

        from pathlib import Path

        try:
            source = Path(self.profile_image.path)
        except (NotImplementedError, ValueError):
            return self.profile_image.url

        thumb = source.with_name(f"{source.stem}_sm.jpg")
        url = f"{self.profile_image.url.rsplit('/', 1)[0]}/{thumb.name}"

        if thumb.exists() and thumb.stat().st_mtime >= source.stat().st_mtime:
            return url

        try:
            from PIL import Image, ImageOps

            with Image.open(source) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((self.AVATAR_MAX_PX, self.AVATAR_MAX_PX), Image.LANCZOS)
                im.save(thumb, "JPEG", quality=82, optimize=True, progressive=True)
        except Exception:      # noqa: BLE001 — never break the page over a thumbnail
            return self.profile_image.url

        return url

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
    key_result = models.CharField(
        max_length=80, blank=True, default='',
        verbose_name="핵심 성과 한 줄 (카드 노출용)",
        help_text="카드에 뱃지로 보이는 짧은 한 줄. 예: '3점 리뷰 89% 재분류', '우수상'. 비워두면 뱃지가 표시되지 않습니다.",
    )
    outcome = models.TextField(blank=True, default='', verbose_name="성과 / 배운 점 (상세 페이지)")
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
    is_featured = models.BooleanField(
        default=False, verbose_name="대표 프로젝트 (Featured)",
        help_text="첫 화면 상단에 크게 노출됩니다. 3개 내외를 권장합니다.",
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('project_detail', args=[self.pk])

    @property
    def primary_tech(self):
        """The handful of technologies worth showing on a card."""
        return list(self.tech_stacks.all())[:4]

    @property
    def extra_tech_count(self):
        return max(0, self.tech_stacks.count() - 4)

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

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('leadership_detail', args=[self.pk])
