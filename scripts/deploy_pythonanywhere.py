#!/usr/bin/env python
"""코드를 PythonAnywhere 에 올리고 웹앱을 리로드합니다.

업로드 목록은 **git 이 추적하는 파일**(`git ls-files`)에서 가져옵니다.
`.gitignore` 에 이미 `db.sqlite3`, `media`, `.env`, `staticfiles` 가 있으므로
운영 데이터와 비밀값은 자동으로 제외됩니다. 실수로 추적 대상이 되더라도
막히도록 DENY 목록을 이중 안전장치로 둡니다.

    pip install -r requirements-dev.txt
    # .env 에 PA_USERNAME / PA_TOKEN

    python scripts/deploy_pythonanywhere.py --list-webapps   # 도메인 확인
    python scripts/deploy_pythonanywhere.py --dry-run        # 올릴 목록만 확인
    python scripts/deploy_pythonanywhere.py                  # 변경분 업로드 + 리로드
    python scripts/deploy_pythonanywhere.py --static         # collectstatic 결과도 함께

주의 — API 로 안 되는 것 (Bash 콘솔에서 한 번씩 직접):
    * requirements.txt 가 바뀐 배포:  pip install --user -r requirements.txt
    * 마이그레이션:                    python manage.py migrate
  두 경우 스크립트가 끝날 때 다시 안내합니다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pa_api as pa  # noqa: E402

#: git 이 추적하더라도 절대 올리지 않을 것. 운영 데이터/비밀값 보호용.
DENY_EXACT = {"db.sqlite3", ".env", "data.json", "home.hex", "profile_image.jpg"}
DENY_PREFIXES = ("media/", "_pa_sync/", "_pa_backup/", ".github/", "staticfiles/",
                 "backups/")   # 콘텐츠 스냅샷은 git 에만 두고 서버에는 올리지 않는다
DENY_SUFFIXES = (".pyc", ".pyo", ".log", ".sqlite3")

#: 업로드한 파일의 해시를 기록해 다음 배포에서 변경분만 올립니다.
STATE_FILE = pa.BASE_DIR / "_pa_sync" / "deploy-state.json"

#: 이 파일들이 바뀌면 서버에서 손으로 해줘야 하는 작업이 있습니다.
NEEDS_PIP = "requirements.txt"
NEEDS_MIGRATE_PREFIX = "portfolio/migrations/"
NEEDS_COLLECTSTATIC_PREFIX = "static/"


def git_tracked_files():
    try:
        output = subprocess.run(
            ["git", "ls-files"],
            cwd=pa.BASE_DIR, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pa.die("git ls-files 실행에 실패했습니다. git 저장소 안에서 실행하세요.")
    return [line.strip() for line in output.splitlines() if line.strip()]


def allowed(relative):
    if relative in DENY_EXACT:
        return False
    if relative.startswith(DENY_PREFIXES):
        return False
    if relative.endswith(DENY_SUFFIXES):
        return False
    return True


def collect_static_files():
    """collectstatic 산출물. WhiteNoise 가 STATIC_ROOT 에서 서빙합니다.

    staticfiles/ 는 DENY_PREFIXES 에도 있지만, 그건 `git ls-files` 결과를
    거르는 용도입니다. 여기서 돌려주는 경로는 `--static` 을 명시했을 때만
    쓰이므로 의도적으로 필터를 거치지 않습니다.
    """
    root = pa.BASE_DIR / "staticfiles"
    if not root.is_dir():
        print("staticfiles/ 가 없습니다. 먼저 실행하세요:"
              "\n  python manage.py collectstatic --noinput")
        return []
    return [
        p.relative_to(pa.BASE_DIR).as_posix()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.name.endswith(pa.SKIP_SUFFIXES)
    ]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="PythonAnywhere 배포")
    parser.add_argument("--dry-run", action="store_true",
                        help="업로드 없이 대상 목록만 출력")
    parser.add_argument("--all", action="store_true",
                        help="변경분이 아니라 전체를 다시 업로드")
    parser.add_argument("--static", action="store_true",
                        help="staticfiles/ (collectstatic 결과)도 함께 업로드")
    parser.add_argument("--no-reload", action="store_true",
                        help="업로드만 하고 웹앱은 리로드하지 않음")
    parser.add_argument("--reload-only", action="store_true",
                        help="업로드 없이 웹앱만 리로드 (migrate 를 끝낸 뒤)")
    parser.add_argument("--list-webapps", action="store_true",
                        help="웹앱 도메인 목록을 출력하고 종료")
    parser.add_argument("--remote-dir", help="원격 프로젝트 경로 (기본: 자동 탐색)")
    parser.add_argument("--domain", help=f"리로드할 도메인 (기본: {pa.DOMAIN})")
    args = parser.parse_args()

    # --dry-run 은 목록 확인용이라 자격증명 없이도 돌아갑니다.
    if args.dry_run:
        session = base = None
        remote_dir = args.remote_dir or pa.REMOTE_DIR or "(자동 탐색)"
        domain = args.domain or pa.DOMAIN or "(PA_USERNAME 미설정)"
    else:
        session, base = pa.connect()

        if args.list_webapps:
            apps = pa.list_webapps(session, base)
            if not apps:
                print("등록된 웹앱이 없습니다.")
            for app in apps:
                print(f"  {app.get('domain_name')}"
                      f"  python={app.get('python_version')}"
                      f"  source={app.get('source_directory')}")
            return

        if args.reload_only:
            target = args.domain or pa.DOMAIN
            print(f"리로드: {target}")
            pa.reload_webapp(session, base, target)
            print("완료")
            return

        remote_dir = pa.resolve_remote_dir(session, base, args.remote_dir)
        domain = args.domain or pa.DOMAIN

    candidates = [f for f in git_tracked_files() if allowed(f)]
    skipped = [f for f in git_tracked_files() if not allowed(f)]
    if args.static:
        candidates += collect_static_files()

    state = {} if args.all else load_state()
    plan, unchanged = [], 0
    for relative in candidates:
        local = pa.BASE_DIR / relative
        if not local.is_file():
            continue
        checksum = digest(local)
        if state.get(relative) == checksum:
            unchanged += 1
            continue
        plan.append((relative, local, checksum))

    print(f"원격 프로젝트: {remote_dir}")
    print(f"웹앱 도메인:   {domain}")
    print(f"업로드 대상:   {len(plan)}개 (변경 없음 {unchanged}개, 제외 {len(skipped)}개)\n")

    if skipped:
        print("제외됨 (운영 데이터/비밀값 보호):")
        for relative in skipped[:8]:
            print(f"  - {relative}")
        if len(skipped) > 8:
            print(f"  … 외 {len(skipped) - 8}개")
        print()

    if not plan:
        print("변경된 파일이 없습니다.")
        if not args.no_reload and not args.dry_run:
            print(f"리로드: {domain}")
            pa.reload_webapp(session, base, domain)
            print("완료")
        return

    for relative, _local, _checksum in plan:
        print(f"  {'(dry-run) ' if args.dry_run else ''}{relative}")

    if args.dry_run:
        print("\n--dry-run 이라 아무것도 올리지 않았습니다.")
        return

    print()
    uploaded = 0
    try:
        for index, (relative, local, checksum) in enumerate(plan, 1):
            status = pa.upload(session, base, local, f"{remote_dir}/{relative}")
            state[relative] = checksum
            uploaded += 1
            print(f"  [{status}] {index:>3}/{len(plan)}  {relative}", flush=True)
            # 중단되더라도 다시 실행하면 남은 것부터 이어갑니다.
            if index % 10 == 0:
                save_state(state)
    finally:
        save_state(state)

    print(f"\n{uploaded}개 업로드 완료")

    changed = {relative for relative, _l, _c in plan}
    todo = []
    if NEEDS_PIP in changed:
        todo.append("pip install --user -r requirements.txt")
    if any(r.startswith(NEEDS_MIGRATE_PREFIX) for r in changed):
        todo.append("python manage.py migrate")
    # 1000개가 넘는 해시 파일을 하나씩 올리는 것보다 서버에서 한 번 돌리는 편이
    # 빠르고, 서버에 설치된 패키지 버전과도 어긋나지 않습니다.
    if not args.static and any(r.startswith(NEEDS_COLLECTSTATIC_PREFIX) for r in changed):
        todo.append("python manage.py collectstatic --noinput")

    # 새 코드가 아직 없는 컬럼을 참조하면 사이트가 500 을 냅니다.
    # 마이그레이션이 걸려 있으면 리로드를 미루고 사람이 먼저 처리하게 합니다.
    if todo:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            # Actions UI 로그에 묻히지 않도록 경고 어노테이션을 남깁니다.
            print(f"::warning title=수동 작업 필요::업로드는 끝났지만 리로드를 건너뛰었습니다. "
                  f"서버 콘솔에서 실행하세요: {'; '.join(todo)}")
        migrating = any("migrate" in line for line in todo)
        print("\n" + "!" * 62)
        print("리로드를 건너뛰었습니다 — 먼저 서버에서 처리해야 할 작업이 있습니다.")
        print("지금 리로드하면 DB 스키마가 코드와 어긋나 사이트가 죽을 수 있습니다.\n"
              if migrating else
              "지금 리로드하면 정적 파일이 옛 버전이라 화면이 깨질 수 있습니다.\n")
        print("PythonAnywhere Bash 콘솔에서:")
        print(f"  cd {remote_dir}")
        for line in todo:
            print(f"  {line}")
        print("\n그 다음 리로드:")
        print(f"  python scripts/deploy_pythonanywhere.py --reload-only")
        print("  (또는 웹 탭에서 Reload 버튼)")
        print("!" * 62)
        return

    if not args.no_reload:
        print(f"리로드: {domain}")
        pa.reload_webapp(session, base, domain)
        print("완료")


if __name__ == "__main__":
    main()
