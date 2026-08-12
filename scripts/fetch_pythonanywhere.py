#!/usr/bin/env python
"""PythonAnywhere 에 배포된 운영 데이터를 로컬로 가져옵니다.

이 저장소에서 git 으로 추적되지 않는 것 — `db.sqlite3` 와 `media/` — 은
운영 서버에만 있습니다. 관리자 페이지에서 콘텐츠를 고치면 서버 쪽이 최신이
되므로, 로컬에서 작업하기 전에 이 스크립트로 내려받습니다.

기본 동작은 **스테이징 폴더로 내려받기만** 합니다. 로컬 파일을 덮어쓰지
않습니다. 교체하려면 `--apply` 를 명시해야 하고, 그때도 기존 파일을 먼저
`_pa_backup/<시각>/` 으로 백업합니다.

    pip install -r requirements-dev.txt
    # .env 에 PA_USERNAME / PA_TOKEN 을 채운 뒤

    python scripts/fetch_pythonanywhere.py --list          # 서버 구조 확인
    python scripts/fetch_pythonanywhere.py                 # 내려받기만
    python scripts/fetch_pythonanywhere.py --apply         # 로컬에 반영
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pa_api as pa  # noqa: E402

#: (원격 상대경로, 로컬 상대경로, 재귀 여부)
TARGETS = [
    ("db.sqlite3", "db.sqlite3", False),
    ("media", "media", True),
]


def cmd_list(session, base, path):
    target = path or f"/home/{pa.USERNAME}"
    entries = pa.listdir(session, base, target)
    if entries is None:
        pa.die(f"디렉터리를 찾을 수 없습니다: {target}")
    print(f"\n{target}")
    for name, meta in sorted(entries.items()):
        is_dir = meta.get("type") == "directory"
        size = meta.get("size")
        print(f"  {'DIR ' if is_dir else 'file'}  {name}{'/' if is_dir else ''}"
              f"{'  ' + pa.human(size) if size else ''}")
    print()


def cmd_pull(session, base, remote_dir, dest, apply_changes):
    print(f"원격 프로젝트: {remote_dir}")
    print(f"스테이징 위치: {dest}\n")

    total_files = total_bytes = 0
    for remote_rel, _local_rel, recursive in TARGETS:
        remote_path = f"{remote_dir}/{remote_rel}"
        files = pa.walk(session, base, remote_path) if recursive else [remote_path]

        if not files:
            print(f"  - {remote_rel} : 없음 또는 비어 있음")
            continue

        for remote_file in files:
            relative = remote_file[len(remote_dir) + 1:]
            size = pa.download(session, base, remote_file, dest / relative)
            if size is None:
                print(f"  ! {relative} : 서버에 없음 (404)")
                continue
            total_files += 1
            total_bytes += size
            print(f"  + {relative}  ({pa.human(size)})")

    print(f"\n{total_files}개 파일, {pa.human(total_bytes)} 내려받음")

    if not total_files:
        print("가져온 파일이 없습니다. --list 로 경로를 먼저 확인해 보세요.")
        return

    if not apply_changes:
        print("\n로컬 파일은 건드리지 않았습니다."
              "\n확인 후 반영하려면:  python scripts/fetch_pythonanywhere.py --apply")
        return

    backup = pa.BASE_DIR / "_pa_backup" / dest.name
    print(f"\n기존 로컬 파일 백업: {backup}")
    for _remote_rel, local_rel, _recursive in TARGETS:
        current = pa.BASE_DIR / local_rel
        if not current.exists():
            continue
        destination = backup / local_rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if current.is_dir():
            shutil.copytree(current, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(current, destination)
        print(f"  backup  {local_rel}")

    for _remote_rel, local_rel, _recursive in TARGETS:
        staged = dest / local_rel
        if not staged.exists():
            continue
        current = pa.BASE_DIR / local_rel
        if staged.is_dir():
            shutil.copytree(staged, current, dirs_exist_ok=True)
        else:
            shutil.copy2(staged, current)
        print(f"  apply   {local_rel}")

    print("\n반영 완료. 이어서 실행하세요:"
          "\n  python manage.py migrate"
          "\n  python manage.py runserver")


def main():
    parser = argparse.ArgumentParser(description="PythonAnywhere 운영 데이터 내려받기")
    parser.add_argument("--list", nargs="?", const="", metavar="PATH",
                        help="원격 디렉터리 내용을 출력하고 종료")
    parser.add_argument("--remote-dir", help="원격 프로젝트 경로 (기본: 자동 탐색)")
    parser.add_argument("--dest", help="스테이징 폴더 (기본: _pa_sync/<시각>)")
    parser.add_argument("--apply", action="store_true",
                        help="내려받은 파일을 로컬에 반영 (기존 파일은 백업)")
    args = parser.parse_args()

    session, base = pa.connect()

    if args.list is not None:
        cmd_list(session, base, args.list or None)
        return

    remote_dir = pa.resolve_remote_dir(session, base, args.remote_dir)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = Path(args.dest) if args.dest else pa.BASE_DIR / "_pa_sync" / stamp
    cmd_pull(session, base, remote_dir, dest, args.apply)


if __name__ == "__main__":
    main()
