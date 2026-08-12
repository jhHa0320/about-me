"""두 SQLite 포트폴리오 DB 를 비교합니다.

로컬과 운영 양쪽 모두 쓰기가 가능하기 때문에, 어느 한쪽을 덮어쓰기 전에
"어느 쪽에 무엇이 더 있는지" 를 먼저 볼 수 있어야 합니다.
"""

from __future__ import annotations

import sqlite3

#: (테이블, 표시 이름, 행을 알아볼 수 있는 컬럼)
TABLES = [
    ("portfolio_profile", "프로필", "name"),
    ("portfolio_education", "학력", "school"),
    ("portfolio_career", "경력", "organization"),
    ("portfolio_skill", "기술", "name"),
    ("portfolio_projecttype", "프로젝트 유형", "name"),
    ("portfolio_projectcategory", "프로젝트 분류", "name"),
    ("portfolio_project", "프로젝트", "title"),
    ("portfolio_activity", "활동·자격증", "title"),
    ("portfolio_leadership", "리더십", "title"),
]

#: 다대다 연결 테이블 — (테이블, 표시 이름, 좌측 컬럼, 우측 컬럼)
M2M = [
    ("portfolio_project_tech_stacks", "프로젝트-기술", "project_id", "skill_id"),
    ("portfolio_project_categories", "프로젝트-분류", "project_id", "projectcategory_id"),
]

#: 비교해도 의미 없는 컬럼
IGNORED_COLUMNS = set()

#: 이보다 긴 값은 미리보기만 보여줍니다.
PREVIEW = 70


def _connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _columns(con, table):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def _has_table(con, table):
    return con.execute(
        "select 1 from sqlite_master where type='table' and name=?", (table,)
    ).fetchone() is not None


def _rows(con, table):
    return {r["id"]: dict(r) for r in con.execute(f"select * from {table}")}


def _preview(value):
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW else text[:PREVIEW] + f"… ({len(text)}자)"


def last_migration(path):
    con = _connect(path)
    try:
        row = con.execute(
            "select name from django_migrations where app='portfolio' "
            "order by id desc limit 1"
        ).fetchone()
        return row[0] if row else "(없음)"
    except sqlite3.Error:
        return "(확인 불가)"
    finally:
        con.close()


def compare(left_path, right_path, left_name="로컬", right_name="운영"):
    """두 DB 를 비교해 사람이 읽을 수 있는 줄 목록과 요약을 돌려줍니다."""
    left, right = _connect(left_path), _connect(right_path)
    lines = []
    only_left = only_right = modified = 0

    try:
        # --- 행 수 요약 ---
        lines.append(f"{'테이블':<14}{left_name:>8}{right_name:>8}   차이")
        lines.append("  " + "─" * 44)
        for table, label, _key in TABLES:
            if not (_has_table(left, table) and _has_table(right, table)):
                lines.append(f"  {label:<14}{'?':>8}{'?':>8}   테이블 없음")
                continue
            lc = left.execute(f"select count(*) from {table}").fetchone()[0]
            rc = right.execute(f"select count(*) from {table}").fetchone()[0]
            delta = ""
            if lc != rc:
                delta = f"{right_name}에 +{rc - lc}" if rc > lc else f"{left_name}에 +{lc - rc}"
            lines.append(f"  {label:<14}{lc:>8}{rc:>8}   {delta}")

        # --- 행 단위 차이 ---
        for table, label, key in TABLES:
            if not (_has_table(left, table) and _has_table(right, table)):
                continue

            lrows, rrows = _rows(left, table), _rows(right, table)
            shared_cols = [
                c for c in _columns(left, table)
                if c in _columns(right, table) and c not in IGNORED_COLUMNS
            ]

            added = sorted(set(rrows) - set(lrows))
            removed = sorted(set(lrows) - set(rrows))
            changed = []
            for rid in sorted(set(lrows) & set(rrows)):
                diff = [
                    c for c in shared_cols
                    if (lrows[rid][c] or "") != (rrows[rid][c] or "")
                ]
                if diff:
                    changed.append((rid, diff))

            if not (added or removed or changed):
                continue

            lines.append("")
            lines.append(f"■ {label}")
            for rid in added:
                only_right += 1
                lines.append(f"    + {right_name}에만  #{rid}  {rrows[rid].get(key)}")
            for rid in removed:
                only_left += 1
                lines.append(f"    - {left_name}에만  #{rid}  {lrows[rid].get(key)}")
            for rid, diff in changed:
                modified += 1
                lines.append(f"    ~ 내용 다름  #{rid}  {rrows[rid].get(key)}")
                for col in diff:
                    lines.append(f"        {col}")
                    lines.append(f"          {left_name}: {_preview(lrows[rid][col])}")
                    lines.append(f"          {right_name}: {_preview(rrows[rid][col])}")

        # --- 다대다 ---
        for table, label, lcol, rcol in M2M:
            if not (_has_table(left, table) and _has_table(right, table)):
                continue
            lp = {(r[lcol], r[rcol]) for r in left.execute(f"select * from {table}")}
            rp = {(r[lcol], r[rcol]) for r in right.execute(f"select * from {table}")}
            if lp == rp:
                continue
            lines.append("")
            lines.append(f"■ {label}")
            for pair in sorted(rp - lp):
                only_right += 1
                lines.append(f"    + {right_name}에만  {lcol}={pair[0]} → {rcol}={pair[1]}")
            for pair in sorted(lp - rp):
                only_left += 1
                lines.append(f"    - {left_name}에만  {lcol}={pair[0]} → {rcol}={pair[1]}")
    finally:
        left.close()
        right.close()

    summary = {
        "only_left": only_left,
        "only_right": only_right,
        "modified": modified,
        "identical": not (only_left or only_right or modified),
    }
    return lines, summary
