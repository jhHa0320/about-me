from django.test import TestCase
from django.urls import reverse
from .models import Profile, Skill, Career, Project, ProjectType, Activity, Leadership


class HomeViewTest(TestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            name='테스트', birthdate='2000-01-01', email='test@test.com'
        )
        project_type = ProjectType.objects.create(name='핵심', description='핵심 프로젝트', order=1)
        self.project = Project.objects.create(
            title='테스트 프로젝트', description='설명', period='2024',
            type=project_type, is_active=True
        )
        self.inactive_project = Project.objects.create(
            title='비활성 프로젝트', description='설명', period='2023', is_active=False
        )
        self.leadership = Leadership.objects.create(
            title='테스트 활동', organization='테스트 조직',
            period='2024', role='리더', description='활동 설명'
        )

    def test_home_returns_200(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_uses_correct_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'portfolio/home.html')

    def test_home_shows_active_project(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, '테스트 프로젝트')

    def test_home_hides_inactive_project(self):
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, '비활성 프로젝트')

    def test_home_shows_profile(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, '테스트')

    def test_home_without_profile(self):
        Profile.objects.all().delete()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)


class ProjectDetailViewTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            title='상세 프로젝트', description='설명', period='2024', is_active=True
        )

    def test_project_detail_returns_200(self):
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

    def test_project_detail_uses_correct_template(self):
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertTemplateUsed(response, 'portfolio/project_detail.html')

    def test_project_detail_shows_title(self):
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertContains(response, '상세 프로젝트')

    def test_project_detail_404_on_invalid_id(self):
        response = self.client.get(reverse('project_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)


class LeadershipDetailViewTest(TestCase):
    def setUp(self):
        self.leadership = Leadership.objects.create(
            title='상세 활동', organization='조직명',
            period='2024', role='팀장', description='활동 설명'
        )

    def test_leadership_detail_returns_200(self):
        response = self.client.get(reverse('leadership_detail', args=[self.leadership.id]))
        self.assertEqual(response.status_code, 200)

    def test_leadership_detail_uses_correct_template(self):
        response = self.client.get(reverse('leadership_detail', args=[self.leadership.id]))
        self.assertTemplateUsed(response, 'portfolio/leadership_detail.html')

    def test_leadership_detail_shows_title(self):
        response = self.client.get(reverse('leadership_detail', args=[self.leadership.id]))
        self.assertContains(response, '상세 활동')

    def test_leadership_detail_404_on_invalid_id(self):
        response = self.client.get(reverse('leadership_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)


class ProfileSingletonTest(TestCase):
    def test_profile_admin_blocks_second_profile(self):
        Profile.objects.create(
            name='첫 번째', birthdate='2000-01-01', email='first@test.com'
        )
        # has_add_permission은 Profile이 이미 존재하면 False를 반환해야 함
        from django.contrib.admin.sites import AdminSite
        from portfolio.admin import ProfileAdmin
        admin_instance = ProfileAdmin(Profile, AdminSite())
        # 프로필이 1개 있으면 추가 불가
        self.assertFalse(admin_instance.has_add_permission(request=None))

    def test_profile_admin_allows_first_profile(self):
        from django.contrib.admin.sites import AdminSite
        from portfolio.admin import ProfileAdmin
        admin_instance = ProfileAdmin(Profile, AdminSite())
        # 프로필이 없으면 추가 가능
        self.assertTrue(admin_instance.has_add_permission(request=None))


class ModelStrTest(TestCase):
    def test_project_str(self):
        project = Project.objects.create(
            title='str 테스트', description='설명', period='2024'
        )
        self.assertEqual(str(project), 'str 테스트')

    def test_skill_str(self):
        skill = Skill.objects.create(name='Python', category='USING')
        self.assertEqual(str(skill), 'Python (사용 중 🔥)')

    def test_leadership_str(self):
        leadership = Leadership.objects.create(
            title='활동명', organization='조직', period='2024',
            role='팀장', description='설명'
        )
        self.assertEqual(str(leadership), '활동명 - 조직')
