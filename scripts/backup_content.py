#!/usr/bin/env python
"""운영 콘텐츠를 사람이 읽을 수 있는 스냅샷으로 백업합니다.

지금 모든 콘텐츠는 서버의 SQLite 파일 하나에 들어 있습니다. 그 파일이
사라지면 프로젝트 설명·보고서·활동 기록이 전부 사라집니다.

운영 DB 를 내려받아 **로컬에서** `dumpdata` 를 돌려 JSON 으로 떨굽니다.
서버 콘솔이 필요 없습니다. JSON 이라 git 에 넣으면 언제 무엇이 바뀌었는지
diff 로 볼 수 있습니다.

    python scripts/backup_content.py                 # 변경됐을 때만 새 스냅샷
    python scripts/backup_content.py --force         # 항상 새로 저장
    python scripts/backup_content.py --with-media    # 이미지까지 (git 밖)
    python scripts/backup_content.py --git-commit    # 저장 후 커밋까지
    python scripts/backup_content.py --prune 20      # 오래된 스냅샷 정리
    python scripts/backup_content.py --restore backups/portfolio-....json

복원은 로컬 DB 를 대상으로만 동작합니다. 운영에 되돌리려면 서버 콘솔에서
loaddata 를 실행해야 합니다 (스크립트가 명령을 안내합니다).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pa_api as pa  # noqa: E402

BACKUP_DIR = pa.BASE_DIR / "backups"
MEDIA_BACKUP_DIR = pa.BASE_DIR / "_pa_backup" / "media-snapshots"
APP = "portfolio"
STAMP_RE = re.compile(r"portfolio-(\d{8}-\d{6})\.json$")


def _dumpdata_from(db_path):
    """주어진 SQLite 파일을 대상으로 dumpdata 를 실행해 JSON 문자열을 돌려줍니다."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "about_me.settings")
    # 백업만 할 것이므로 운영 플래그는 필요 없습니다.
    os.environ.setdefault("SECRET_KEY", "backup-only")
    os.environ["DEBUG"] = "True"

    sys.path.insert(0, str(pa.BASE_DIR))
    import django

    if not getattr(django, "_backup_setup_done", False):
        django.setup()
        django._backup_setup_done = True

    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections

    settings.DATABASES["default"]["NAME"] = str(db_path)
    connections.close_all()

    buffer = io.StringIO()
    call_command(
        "dumpdata", APP,
        indent=2, format="json",
        stdout=buffer,
    )
    connections.close_all()
    return buffer.getvalue()


def _content_hash(text):
    """저장 시각처럼 매번 바뀌는 값이 없으므로 본문 해시로 변경 여부를 판단합니다."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _latest_backup():
    if not BACKUP_DIR.is_dir():
        return None
    snapshots = sorted(BACKUP_DIR.glob("portfolio-*.json"))
    return snapshots[-1] if snapshots else None


def _summarise(text):
    try:
        records = json.loads(text)
    except ValueError:
        return {}
    counts = {}
    for record in records:
        model = record.get("model", "?").split(".")[-1]
        counts[model] = counts.get(model, 0) + 1
    return counts


def cmd_backup(args):
    session, base = pa.connect()
    remote_dir = pa.resolve_remote_dir(session, base, args.remote_dir)

    with tempfile.TemporaryDirectory() as tmp:
        remote_db = Path(tmp) / "remote.sqlite3"
        print(f"운영 DB 내려받는 중… ({remote_dir}/db.sqlite3)")
        size = pa.download(session, base, f"{remote_dir}/db.sqlite3", remote_db)
        if size is None:
            pa.die("운영 서버에 db.sqlite3 가 없습니다.")
        print(f"  {pa.human(size)}")

        print("dumpdata 실행 중…")
        payload = _dumpdata_from(remote_db)

    counts = _summarise(payload)
    print("  " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    previous = _latest_backup()
    if previous and not args.force:
        if _content_hash(previous.read_text(encoding="utf-8")) == _content_hash(payload):
            print(f"\n직전 스냅샷과 내용이 같습니다: {previous.name}")
            print("강제로 저장하려면 --force")
            return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = BACKUP_DIR / f"portfolio-{stamp}.json"
    target.write_text(payload, encoding="utf-8")
    print(f"\n저장: {target.relative_to(pa.BASE_DIR)}  ({pa.human(len(payload.encode()))})")

    if previous:
        print(f"직전:  {previous.name}")
        print("       변경 내용은 git diff 로 확인할 수 있습니다.")

    if args.with_media:
        _backup_media(session, base, remote_dir, stamp)

    if args.prune:
        _prune(args.prune)

    if args.git_commit:
        _git_commit(target)


def _backup_media(session, base, remote_dir, stamp):
    """이미지 스냅샷. 용량이 커서 git 밖(_pa_backup/)에 둡니다."""
    target = MEDIA_BACKUP_DIR / stamp
    files = pa.walk(session, base, f"{remote_dir}/media")
    if not files:
        print("\n미디어: 서버에 파일이 없습니다.")
        return
    print(f"\n미디어 {len(files)}개 내려받는 중…")
    total = 0
    for remote_file in files:
        relative = remote_file[len(remote_dir) + 1:]
        got = pa.download(session, base, remote_file, target / relative)
        total += got or 0
    print(f"  저장: {target.relative_to(pa.BASE_DIR)}  ({pa.human(total)})")
    print("  (용량이 커서 git 에는 넣지 않습니다 — _pa_backup/ 은 .gitignore 대상)")


def _prune(keep):
    snapshots = sorted(BACKUP_DIR.glob("portfolio-*.json"))
    excess = snapshots[:-keep] if keep > 0 else []
    for path in excess:
        path.unlink()
    if excess:
        print(f"\n오래된 스냅샷 {len(excess)}개 삭제 (최근 {keep}개 유지)")


def _git_commit(target):
    relative = target.relative_to(pa.BASE_DIR).as_posix()
    try:
        subprocess.run(["git", "add", relative], cwd=pa.BASE_DIR, check=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"chore: 콘텐츠 백업 {target.stem}"],
            cwd=pa.BASE_DIR, capture_output=True, text=True,
        )
        print("\n" + (result.stdout or result.stderr).strip().splitlines()[0])
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as exc:
        print(f"\ngit 커밋 실패: {exc}")


def cmd_restore(args):
    source = Path(args.restore)
    if not source.is_file():
        pa.die(f"파일이 없습니다: {source}")

    print(f"복원 대상: 로컬 db.sqlite3")
    print(f"스냅샷:    {source}")
    print()
    print("주의: loaddata 는 같은 pk 의 행을 덮어씁니다. 스냅샷에 없는 행은")
    print("      그대로 남습니다(완전 초기화가 아닙니다).")
    if input("계속할까요? [y/N] ").strip().lower() != "y":
        print("취소했습니다.")
        return

    backup = pa.BASE_DIR / "_pa_backup" / f"pre-restore-{datetime.now():%Y%m%d-%H%M%S}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pa.BASE_DIR / "db.sqlite3", backup / "db.sqlite3")
    print(f"현재 로컬 DB 백업: {backup.relative_to(pa.BASE_DIR)}/db.sqlite3")

    subprocess.run(
        [sys.executable, "manage.py", "loaddata", str(source)],
        cwd=pa.BASE_DIR, check=False,
    )
    print()
    print("운영 서버에 되돌리려면 서버 Bash 콘솔에서:")
    print(f"  cd /home/{pa.USERNAME}/about_me")
    print(f"  # 스냅샷 파일을 먼저 올린 뒤")
    print(f"  python manage.py loaddata <파일명>.json")


def main():
    parser = argparse.ArgumentParser(description="운영 콘텐츠 백업")
    parser.add_argument("--force", action="store_true",
                        help="내용이 같아도 새 스냅샷을 저장")
    parser.add_argument("--with-media", action="store_true",
                        help="이미지 파일도 함께 내려받기 (git 밖에 저장)")
    parser.add_argument("--git-commit", action="store_true",
                        help="저장 후 git 커밋까지")
    parser.add_argument("--prune", type=int, metavar="N",
                        help="최근 N개만 남기고 오래된 스냅샷 삭제")
    parser.add_argument("--restore", metavar="FILE",
                        help="스냅샷을 로컬 DB 에 복원")
    parser.add_argument("--remote-dir", help="원격 프로젝트 경로 (기본: 자동 탐색)")
    args = parser.parse_args()

    if args.restore:
        cmd_restore(args)
    else:
        cmd_backup(args)


if __name__ == "__main__":
    main()
