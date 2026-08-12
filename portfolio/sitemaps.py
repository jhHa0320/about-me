from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Leadership, Project


class StaticSitemap(Sitemap):
    priority = 1.0
    changefreq = "weekly"

    def items(self):
        return ["home"]

    def location(self, item):
        return reverse(item)


class ProjectSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return Project.objects.filter(is_active=True)


class LeadershipSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return Leadership.objects.all()


SITEMAPS = {
    "static": StaticSitemap,
    "projects": ProjectSitemap,
    "leadership": LeadershipSitemap,
}
