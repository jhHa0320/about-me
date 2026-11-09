from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from . import paper_sources as ps
from .models import Career, Paper

ARXIV_XML = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry><title>Attention Is All
  You Need</title><published>2017-06-12T17:57:34Z</published>
<author><name>Ashish Vaswani</name></author><author><name>Noam Shazeer</name></author>
<arxiv:journal_ref>NeurIPS 2017</arxiv:journal_ref></entry></feed>"""

CROSSREF = '{"message": {"title": ["BERT"], "author": [{"given": "Jacob", "family": "Devlin"}],' \
           ' "container-title": ["NAACL"], "issued": {"date-parts": [[2019, 6]]}}}'

PAGE = ('<meta name="citation_title" content="Some Paper"><meta name="citation_author" content="A One">'
        '<meta name="citation_author" content="B Two"><meta name="citation_conference_title" content="ACL">'
        '<meta name="citation_publication_date" content="2020/07/05">')


class MetadataTest(TestCase):
    def fetch(self, source, body):
        with mock.patch.object(ps, "_get", return_value=body) as get:
            return ps.fetch_metadata(source), get.call_args[0][0]

    def test_arxiv_url_variants_use_arxiv_api(self):
        for src in ("https://arxiv.org/abs/1706.03762v5", "https://arxiv.org/pdf/1706.03762.pdf", "arXiv:1706.03762"):
            meta, called = self.fetch(src, ARXIV_XML)
            self.assertIn("id_list=1706.03762", called)
        self.assertEqual(meta, {"title": "Attention Is All You Need", "authors": "Ashish Vaswani, Noam Shazeer",
                                "venue": "NeurIPS 2017", "year": 2017})

    def test_doi_uses_crossref(self):
        meta, called = self.fetch("https://doi.org/10.18653/v1/N19-1423", CROSSREF)
        self.assertIn("api.crossref.org/works/10.18653", called)
        self.assertEqual((meta["title"], meta["authors"], meta["venue"], meta["year"]),
                         ("BERT", "Jacob Devlin", "NAACL", 2019))

    def test_generic_page_uses_citation_meta(self):
        meta, _ = self.fetch("https://aclanthology.org/2020.acl-main.1/", PAGE)
        self.assertEqual(meta, {"title": "Some Paper", "authors": "A One, B Two", "venue": "ACL", "year": 2020})

    def test_page_without_citation_meta_raises(self):
        with self.assertRaises(ps.MetaError):
            self.fetch("https://example.com/x", "<html></html>")

    def test_non_http_scheme_rejected(self):
        with self.assertRaises(ps.MetaError):
            ps._get("file:///etc/passwd")


class DriveLinksTest(TestCase):
    def test_drive_file_and_slides(self):
        d = ps.drive_links("https://drive.google.com/file/d/AbC_123-x/view?usp=sharing")
        self.assertEqual(d["embed"], "https://drive.google.com/file/d/AbC_123-x/preview")
        self.assertIn("id=AbC_123-x", d["download"])
        s = ps.drive_links("https://docs.google.com/presentation/d/SLIDE9/edit#slide=id.p")
        self.assertEqual(s["embed"], "https://docs.google.com/presentation/d/SLIDE9/embed")
        self.assertTrue(ps.drive_links("https://drive.google.com/open?id=ZZZ"))

    def test_other_urls_are_not_drive(self):
        self.assertIsNone(ps.drive_links("https://example.com/slides.pdf"))
        self.assertIsNone(ps.drive_links(""))


class PaperModelAndViewTest(TestCase):
    def test_clean_autofills_blank_fields_from_source(self):
        p = Paper(source_url="https://arxiv.org/abs/1706.03762", venue="내가 쓴 학회")
        with mock.patch.object(ps, "_get", return_value=ARXIV_XML):
            p.clean()
        self.assertEqual((p.title, p.year, p.venue), ("Attention Is All You Need", 2017, "내가 쓴 학회"))

    def test_clean_fetch_failure_without_title_is_form_error(self):
        with mock.patch.object(ps, "_get", side_effect=ps.MetaError("down")):
            with self.assertRaises(ValidationError):
                Paper(source_url="https://arxiv.org/abs/1706.03762").clean()

    def test_clean_requires_title_or_source(self):
        with self.assertRaises(ValidationError):
            Paper().clean()

    def test_papers_page_lists_only_active(self):
        Paper.objects.create(title="공개 논문", slides_url="https://drive.google.com/file/d/ID1/view")
        Paper.objects.create(title="숨김 논문", is_active=False)
        res = self.client.get(reverse("papers"))
        self.assertContains(res, "공개 논문")
        self.assertContains(res, "drive.google.com/file/d/ID1/preview")
        self.assertNotContains(res, "숨김 논문")

    def test_career_page_filters_and_timeline_links_only_when_papers_exist(self):
        lab = Career.objects.create(organization="AI 연구실", role="학부연구생", period="2026.1-", description="d")
        empty = Career.objects.create(organization="다른 곳", role="r", period="2025", description="d")
        Paper.objects.create(title="연구실 논문", career=lab)
        Paper.objects.create(title="무소속 논문")

        res = self.client.get(reverse("career_papers", args=[lab.pk]))
        self.assertContains(res, "연구실 논문")
        self.assertNotContains(res, "무소속 논문")
        self.assertEqual(self.client.get(reverse("career_papers", args=[9999])).status_code, 404)

        home = self.client.get(reverse("home")).content.decode()
        self.assertIn(reverse("career_papers", args=[lab.pk]), home)
        self.assertNotIn(reverse("career_papers", args=[empty.pk]), home)
