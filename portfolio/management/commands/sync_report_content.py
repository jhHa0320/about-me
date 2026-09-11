import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from portfolio.models import Project

DEFAULT_FIXTURE = Path(settings.BASE_DIR) / "portfolio" / "fixtures" / "report_template_sync.json"
SYNCED_FIELDS = ("report_type", "content", "key_result", "outcome")


class Command(BaseCommand):
    """Apply the report-template restructure (done in the report-template-restructure
    branch) to an environment whose Project row IDs may differ from the source
    (e.g. production, which is edited directly via /admin and was never in sync
    with the dev sqlite db). Matches rows by exact `title`, never by pk, so it is
    safe to run against a database with different primary keys.

    Dry-run by default so you can review the diff before writing anything.
    """

    help = "Sync report_type/content/key_result/outcome from a title-keyed JSON fixture. Dry-run unless --apply is passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default=str(DEFAULT_FIXTURE),
            help="Path to the title-keyed JSON fixture (default: portfolio/fixtures/report_template_sync.json)",
        )
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually write the changes. Without this flag, only a preview is printed.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fixture not found: {path}"))
            return

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        changed, skipped, unchanged = 0, 0, 0

        for title, fields in data.items():
            matches = Project.objects.filter(title=title)
            count = matches.count()
            if count != 1:
                self.stderr.write(self.style.WARNING(
                    f"SKIP ({count} title matches, expected exactly 1): {title!r}"
                ))
                skipped += 1
                continue

            project = matches.first()
            diffs = []
            for field in SYNCED_FIELDS:
                new_value = fields.get(field, "")
                old_value = getattr(project, field)
                if old_value != new_value:
                    if field == "content":
                        diffs.append(f"content: {len(old_value)} chars -> {len(new_value)} chars")
                    else:
                        diffs.append(f"{field}: {old_value!r} -> {new_value!r}")

            if not diffs:
                unchanged += 1
                continue

            label = "APPLY" if options["apply"] else "DRY-RUN"
            self.stdout.write(f"[{label}] {title}")
            for d in diffs:
                self.stdout.write(f"    {d}")
            changed += 1

            if options["apply"]:
                for field in SYNCED_FIELDS:
                    setattr(project, field, fields.get(field, ""))
                project.save()

        self.stdout.write("")
        self.stdout.write(f"matched-and-changed: {changed}, unchanged: {unchanged}, skipped: {skipped}")
        if not options["apply"]:
            self.stdout.write(self.style.WARNING(
                "Dry run only — no changes written. Re-run with --apply to write them."
            ))
