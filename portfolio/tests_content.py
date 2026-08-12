"""Tests for the content-normalisation layer added in the UX refactor.

The portfolio's admin content was authored in Summernote and largely pasted
from Word/Notion, so it arrives with hardcoded typography, Office namespace
tags and inconsistent structure. These tests pin the behaviour that keeps it
rendering as clean, themeable, accessible markup.
"""

from django.test import TestCase
from django.urls import reverse

from .models import Career, Profile, Project, Skill
from .templatetags.portfolio_extras import (
    bullets,
    emphasise,
    first_line,
    lead_text,
    richtext,
)
from .views import _dedupe_description, _period_sort_key


class RichTextFilterTest(TestCase):
    def test_strips_hardcoded_typography_and_colour(self):
        html = ('<p><span style="font-family: Helvetica; font-size: 11pt; '
                'color: rgb(0,0,0);">본문</span></p>')
        out = str(richtext(html))
        self.assertNotIn("font-family", out)
        self.assertNotIn("font-size", out)
        self.assertNotIn("color:", out)
        self.assertIn("본문", out)

    def test_keeps_emphasis(self):
        out = str(richtext('<p><span style="font-weight: bold">굵게</span></p>'))
        self.assertIn("font-weight: bold", out)

    def test_drops_word_junk_attributes(self):
        out = str(richtext('<p data-path-to-node="10,0" class="0" lang="EN-US">x</p>'))
        self.assertNotIn("data-path-to-node", out)
        self.assertNotIn('class="0"', out)
        self.assertNotIn("lang=", out)

    def test_heading_wrapping_blocks_is_demoted(self):
        """A whole report stored inside one <h4> must not render as a heading."""
        out = str(richtext("<h4><p>문단 하나</p><p>문단 둘</p></h4>"))
        self.assertNotIn("<h4", out)
        self.assertIn("문단 하나", out)
        self.assertIn("문단 둘", out)

    def test_heading_levels_compressed_without_gaps(self):
        """Author used only <h4>; under the page's <h2> it must become <h3>."""
        out = str(richtext("<h4>제목</h4><p>본문</p>"))
        self.assertIn("<h3>", out)
        self.assertNotIn("<h4>", out)

    def test_orphan_list_items_get_a_list_parent(self):
        out = str(richtext("<li><p>하나</p></li><li><p>둘</p></li>"))
        self.assertTrue(out.startswith("<ul>"))
        self.assertEqual(out.count("<ul>"), 1)
        self.assertEqual(out.count("</ul>"), 1)
        self.assertIn("하나", out)
        self.assertIn("둘", out)

    def test_preserves_all_visible_text(self):
        html = "<h4><p>가</p></h4><li><p>나</p></li><table><tr><td>다</td></tr></table>"
        out = str(richtext(html))
        for ch in "가나다":
            self.assertIn(ch, out)

    def test_external_links_get_safe_rel(self):
        out = str(richtext('<p><a href="https://example.com">링크</a></p>'))
        self.assertIn('rel="noopener noreferrer"', out)
        self.assertIn('target="_blank"', out)

    def test_script_is_removed(self):
        out = str(richtext("<p>안전</p><script>alert(1)</script>"))
        self.assertNotIn("<script", out)
        self.assertIn("안전", out)

    def test_javascript_href_is_dropped(self):
        out = str(richtext('<p><a href="javascript:alert(1)">x</a></p>'))
        self.assertNotIn("javascript:", out)

    def test_empty_input(self):
        self.assertEqual(richtext(""), "")
        self.assertEqual(richtext(None), "")


class PlainTextFilterTest(TestCase):
    def test_emphasise_promotes_leftover_markdown(self):
        self.assertIn("<strong>중요</strong>", str(emphasise("이건 **중요** 합니다")))

    def test_emphasise_escapes_before_promoting(self):
        self.assertNotIn("<script>", str(emphasise("<script>alert(1)</script>")))

    def test_bullets_splits_dashed_lines(self):
        self.assertEqual(bullets("- 하나\r\n- 둘"), ["하나", "둘"])

    def test_bullets_falls_back_to_paragraphs(self):
        self.assertEqual(bullets("첫 문단\n\n둘째 문단"), ["첫 문단", "둘째 문단"])

    def test_first_line_returns_opening_summary(self):
        self.assertEqual(first_line("요약 한 줄\r\n이어지는 상세 설명"), "요약 한 줄")

    def test_first_line_on_empty(self):
        self.assertEqual(first_line(""), "")

    def test_lead_text_keeps_short_summaries_whole(self):
        text = "파편화된 합주실 데이터를 통합하여 뮤지션의 탐색 비용을 해결하는 실시간 예약 보조 서비스"
        self.assertEqual(lead_text(text), text)

    def test_lead_text_cuts_long_summaries_at_first_sentence(self):
        text = ("뒤섞인 비디오 프레임 4장과 캡션으로 원본 시간 순서를 복원하는 대회 과제. "
                "CLIP 기반 파이프라인의 성능 한계를 6개의 통제 실험으로 진단해 병목을 규명했고, "
                "QLoRA로 8GB GPU에서 3B 모델 파인튜닝을 성립시켜 정확도를 34.98%로 끌어올렸다.")
        self.assertEqual(lead_text(text),
                         "뒤섞인 비디오 프레임 4장과 캡션으로 원본 시간 순서를 복원하는 대회 과제.")

    def test_lead_text_does_not_split_on_decimals(self):
        """0.51308 의 마침표에서 끊기면 안 됩니다."""
        text = ("리더보드 Exact Match 0.51308 을 달성한 파이프라인으로, 검증 정확도 33.25%를 "
                "34.98%까지 끌어올린 과정을 6개의 통제 실험으로 정리한 프로젝트입니다")
        self.assertIn("0.51308", lead_text(text))


class PeriodSortTest(TestCase):
    """Timeline periods are free text; newest must still come first."""

    def test_orders_newest_first(self):
        periods = ["2024년 1학기 -", "2026.7월 - 12월", "2025.1-2025.9",
                   "2026-1학기", "2025 여름방학"]
        ordered = sorted(periods, key=_period_sort_key, reverse=True)
        self.assertEqual(ordered[0], "2026.7월 - 12월")
        self.assertEqual(ordered[1], "2026-1학기")
        self.assertEqual(ordered[2], "2025.1-2025.9")

    def test_month_parsed_next_to_hangul_suffix(self):
        """`\\b` does not fire between a digit and Hangul ("7월")."""
        self.assertEqual(_period_sort_key("2026.7월")[1], 7)

    def test_range_sorts_by_its_end(self):
        self.assertEqual(_period_sort_key("2024년 2학기 - 2025년 1학기"), (2025, 3, 0))

    def test_open_ended_period_marked_ongoing(self):
        self.assertEqual(_period_sort_key("2024년 1학기 -")[2], 1)

    def test_unparseable_sinks_to_the_bottom(self):
        self.assertEqual(_period_sort_key("")[0], 0)
        self.assertEqual(_period_sort_key("미정")[0], 0)


class TimelineTest(TestCase):
    def test_career_rows_appear(self):
        """Career had no template before this refactor and was invisible."""
        Career.objects.create(organization="데이터사이언스 소모임", role="대표자",
                              period="2025.1-2025.9", description="설명")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "데이터사이언스 소모임")
        self.assertContains(response, "대표자")

    def test_description_repeating_the_title_is_hidden(self):
        self.assertEqual(_dedupe_description("개발 동아리 멘토링", "개발 동아리 멘토링"), "")

    def test_distinct_description_is_kept(self):
        self.assertEqual(_dedupe_description("전혀 다른 설명", "제목"), "전혀 다른 설명")

    def test_career_hidden_when_leadership_covers_the_same_org(self):
        """운영 데이터에서 같은 소모임이 Career 와 Leadership 양쪽에 들어왔습니다."""
        from .models import Leadership
        from .views import _timeline_entries

        Leadership.objects.create(
            title="데이터사이언스 소모임",
            organization="숭실대학교 AI소프트웨어학부(AI융합학부)",
            period="2024 여름방학 - 2025 1학기", role="1기 부원, 2기 대표자",
            description="",
        )
        Career.objects.create(
            organization="숭실대학교 AI융합학부 데이터사이언스 소모임",
            role="대표자", period="2025.1-2025.9", description="설명",
        )
        kinds = [e["kind"] for e in _timeline_entries()]
        self.assertEqual(kinds.count("리더십"), 1)
        self.assertEqual(kinds.count("경력"), 0)

    def test_unrelated_career_still_shows(self):
        from .models import Leadership
        from .views import _timeline_entries

        Leadership.objects.create(title="밴드 소모임", organization="숭실대 밴드",
                                  period="2024", role="팀장", description="")
        Career.objects.create(organization="전혀 다른 회사", role="인턴",
                              period="2025", description="설명")
        kinds = [e["kind"] for e in _timeline_entries()]
        self.assertEqual(kinds.count("경력"), 1)


class FeaturedProjectTest(TestCase):
    def setUp(self):
        Profile.objects.create(name="테스트", birthdate="2000-01-01", email="t@t.com")
        self.featured = Project.objects.create(
            title="대표 프로젝트", description="설명", period="2025",
            is_active=True, is_featured=True,
        )
        self.other = Project.objects.create(
            title="일반 프로젝트", description="설명", period="2024", is_active=True,
        )

    def test_featured_and_archive_are_disjoint(self):
        response = self.client.get(reverse("home"))
        self.assertIn(self.featured, response.context["featured_projects"])
        self.assertNotIn(self.featured, response.context["other_projects"])
        self.assertIn(self.other, response.context["other_projects"])

    def test_inactive_project_never_renders_even_if_featured(self):
        Project.objects.create(title="숨김프로젝트", description="설명", period="2025",
                               is_active=False, is_featured=True)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "숨김프로젝트")

    def test_card_shows_only_a_few_technologies(self):
        for i in range(7):
            self.other.tech_stacks.add(
                Skill.objects.create(name=f"Tech{i}", category="USING")
            )
        self.assertEqual(len(self.other.primary_tech), 4)
        self.assertEqual(self.other.extra_tech_count, 3)


class SeoTest(TestCase):
    def setUp(self):
        Profile.objects.create(name="테스트", birthdate="2000-01-01", email="t@t.com")

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sitemap:", response.content.decode())

    def test_sitemap_lists_projects(self):
        Project.objects.create(title="p", description="d", period="2025", is_active=True)
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/project/", response.content.decode())

    def test_home_has_canonical_og_and_structured_data(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('rel="canonical"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn("application/ld+json", html)


class TemplateSyntaxLeakTest(TestCase):
    """`{# … #}` is single-line only in Django; a multi-line one renders as text."""

    def setUp(self):
        Profile.objects.create(name="테스트", birthdate="2000-01-01", email="t@t.com")
        self.project = Project.objects.create(
            title="p", description="d", period="2025", is_active=True
        )

    def test_no_unrendered_template_syntax(self):
        urls = [
            reverse("home"),
            reverse("project_detail", args=[self.project.pk]),
        ]
        for url in urls:
            html = self.client.get(url).content.decode()
            for marker in ("{#", "#}", "{%", "{{"):
                self.assertNotIn(marker, html, f"{marker} leaked into {url}")


class PrivacyTest(TestCase):
    """Birthdate and the raw email address are opt-in, not default."""

    def test_birthdate_hidden_by_default(self):
        Profile.objects.create(name="테스트", birthdate="2000-01-01", email="t@t.com")
        html = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("2000.01.01", html)

    def test_birthdate_shown_when_opted_in(self):
        Profile.objects.create(name="테스트", birthdate="2000-01-01",
                               email="t@t.com", show_birthdate=True)
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("2000.01.01", html)

    def test_email_masked_but_link_still_works(self):
        Profile.objects.create(name="테스트", birthdate="2000-01-01", email="secret@t.com")
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("mailto:secret@t.com", html)
        self.assertNotIn(">secret@t.com<", html)
