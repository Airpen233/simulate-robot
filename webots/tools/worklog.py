"""Render ``WORKLOG.md`` from git history.

Why this exists
---------------
``PROGRESS.md`` answers "what results do we have". It cannot answer "what did
the other person actually do this week" — for that you have to read commit
messages, one by one, and hold them in your head.

This tool folds that in: it groups commits by day and by author, keeps the
body of each message (where the reasoning lives), and surfaces the files that
moved. Nobody has to maintain it, so it cannot go stale.

Design notes
------------
* Commits whose subject matches ``Merge pull request`` are dropped; the
  commits they merge already appear individually.
* ``chore:`` commits are folded into a single count instead of being listed,
  so a day of bookkeeping does not drown a day of real work.
* Author identities are normalised: a person who committed under two e-mails
  must appear once, otherwise the log invents phantom colleagues.
* A commit message body is kept verbatim (indented) because that is where the
  "why" lives. Truncating it would defeat the point.

Usage
-----
    python tools/worklog.py              # write WORKLOG.md at the repo root
    python tools/worklog.py --print      # show it, write nothing
    python tools/worklog.py --days 7     # limit the window

No external dependencies.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "WORKLOG.md"

# Same person, several e-mails. Add aliases here when a new one shows up.
AUTHOR_ALIASES = {
    "airpen112469@outlook.com": "airpen",
    "airpen233@users.noreply.github.com": "airpen",
}

NOISE_SUBJECT = re.compile(r"^Merge pull request", re.I)
FOLD_SUBJECT = re.compile(r"^(chore|style|ci)(\(|:)", re.I)


def git(*args: str) -> str:
    """Run git in the repo root and return stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def canonical_author(email: str, name: str) -> str:
    """Collapse e-mail aliases so one person does not look like two."""

    key = email.strip().lower()
    if key in AUTHOR_ALIASES:
        return AUTHOR_ALIASES[key]
    local = key.split("@")[0]
    return AUTHOR_ALIASES.get(local, local or name.strip().lower() or "unknown")


def read_commits(days: int | None) -> list[dict[str, object]]:
    """Parse ``git log`` into structured commit records."""

    args = [
        "log",
        "--date=iso-strict",
        "--pretty=format:%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b%x1e",
    ]
    if days:
        args.append(f"--since={days} days ago")

    raw = git(*args)
    commits: list[dict[str, object]] = []

    for chunk in raw.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("\x1f")
        if len(parts) < 6:
            continue
        sha, name, email, when, subject, body = parts[:6]
        if NOISE_SUBJECT.match(subject):
            continue
        commits.append(
            {
                "sha": sha[:7],
                "author": canonical_author(email, name),
                "raw_author": name,
                "when": when,
                "subject": subject.strip(),
                "body": body.strip(),
            }
        )
    return commits


def files_changed_detail(sha: str) -> tuple[int, int, int]:
    """(authored_files, authored_lines, evidence_lines) for one commit.

    Archived logs and world files are committed as evidence, not authored
    content. Counting them makes the first import commit look like 17k lines of
    work and buries every later commit, so they are tracked separately.

    The initial import is also excluded from authored lines: it brings an
    existing project under version control in one commit, which is a baseline
    rather than a day's work. It still counts as a commit.
    """

    if is_initial_import(sha):
        out = git("show", "--numstat", "--format=", sha)
        files = sum(1 for line in out.splitlines() if len(line.split("\t")) == 3)
        return files, 0, 0

    out = git("show", "--numstat", "--format=", sha)
    files = 0
    lines = 0
    evidence = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        path = parts[2]
        added = int(parts[0]) if parts[0].isdigit() else 0
        deleted = int(parts[1]) if parts[1].isdigit() else 0
        bulk = (
            path.endswith(".log")
            or path.startswith("webots/logs/")
            or path.endswith(".wbt")
            or path.endswith("_world.json")
        )
        if bulk:
            evidence += added + deleted
            continue
        files += 1
        lines += added + deleted
    return files, lines, evidence


def is_initial_import(sha: str) -> bool:
    """True for a root commit, which imports the project rather than changing it."""

    try:
        roots = git("rev-list", "--max-parents=0", "HEAD").split()
    except RuntimeError:
        return False
    return any(root.startswith(sha) or sha.startswith(root[:7]) for root in roots)


def top_dirs(sha: str, limit: int = 3) -> list[str]:
    """Which areas of the repo a commit touched, most frequent first."""

    out = git("show", "--name-only", "--format=", sha)
    counts: dict[str, int] = defaultdict(int)
    for path in out.splitlines():
        path = path.strip()
        if not path:
            continue
        if "/" in path:
            head = path.split("/")[0]
            if head in ("webots", "src", "tests", "docs", ".github"):
                second = path.split("/")[1] if path.count("/") >= 1 else ""
                head = f"{head}/{second}" if second and not second.endswith(".log") else head
        else:
            head = "(root)"
        counts[head] += 1
    return [d for d, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]


def strip_trailer(body: str) -> str:
    """Drop co-author / generated-by trailers that add nothing for a reader."""

    kept = []
    for line in body.splitlines():
        if re.match(r"^(Co-authored-by|Signed-off-by|Generated-by):", line, re.I):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def build(days: int | None) -> str:
    commits = read_commits(days)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# 工作日志")
    lines.append("")
    lines.append("> 由 `webots/tools/worklog.py` 从 git 历史自动生成，**无需手工维护**。")
    lines.append("> 每次提交后重跑一次即可：`cd webots && python tools/worklog.py`")
    window = f"最近 {days} 天" if days else "全部历史"
    lines.append(f"> 统计窗口：{window}｜生成时间：{now}")
    lines.append("")

    if not commits:
        lines.append("暂无提交记录。")
        return "\n".join(lines)

    by_day: dict[str, list[dict[str, object]]] = defaultdict(list)
    for commit in commits:
        by_day[str(commit["when"])[:10]].append(commit)

    # ---- per-author summary -------------------------------------------------
    per_author = defaultdict(lambda: {"commits": 0, "files": 0, "lines": 0, "days": set()})
    for commit in commits:
        bucket = per_author[str(commit["author"])]
        bucket["commits"] += 1
        bucket["days"].add(str(commit["when"])[:10])
        files, touched, _evidence = files_changed_detail(str(commit["sha"]))
        bucket["files"] += files
        bucket["lines"] += touched

    lines.append("## 谁做了什么")
    lines.append("")
    lines.append("| 人 | 提交数 | 涉及文件 | 改动行数 | 活跃天数 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for author in sorted(per_author):
        b = per_author[author]
        lines.append(
            f"| `{author}` | {b['commits']} | {b['files']} | {b['lines']} | {len(b['days'])} |"
        )
    lines.append("")

    # ---- day by day ---------------------------------------------------------
    lines.append("## 按天")
    lines.append("")
    for day in sorted(by_day, reverse=True):
        entries = by_day[day]
        authors = sorted({str(c["author"]) for c in entries})
        lines.append(f"### {day}　（{'、'.join(authors)}，{len(entries)} 个提交）")
        lines.append("")

        folded: list[dict[str, object]] = []
        initial: list[dict[str, object]] = []
        for commit in entries:
            if is_initial_import(str(commit["sha"])):
                initial.append(commit)
                continue
            if FOLD_SUBJECT.match(str(commit["subject"])):
                folded.append(commit)
                continue

            files, touched, evidence = files_changed_detail(str(commit["sha"]))
            areas = top_dirs(str(commit["sha"]))
            where = "、".join(f"`{a}`" for a in areas) if areas else ""
            evidence_note = f" + 证据 {evidence} 行" if evidence else ""
            lines.append(
                f"- **{commit['subject']}** `{commit['sha']}`"
                f"　（{files} 文件 / +{touched} 行{evidence_note}）"
            )
            if where:
                lines.append(f"  - 触及：{where}")
            body = strip_trailer(str(commit["body"]))
            if body:
                lines.append("")
                for body_line in body.splitlines()[:24]:
                    lines.append(f"    {body_line}" if body_line.strip() else "")
                lines.append("")

        if folded:
            lines.append(
                f"- 另有 {len(folded)} 个杂项提交（chore/ci/style）："
                + "、".join(f"`{c['sha']}`" for c in folded)
            )
        for commit in initial:
            lines.append(
                f"- _{commit['subject']}_ `{commit['sha']}`"
                f"　— 基线导入，不计入工作量"
            )
        lines.append("")

    # ---- what areas have been touched lately --------------------------------
    recent_areas: dict[str, int] = defaultdict(int)
    for commit in commits[:30]:
        for area in top_dirs(str(commit["sha"]), limit=5):
            recent_areas[area] += 1
    if recent_areas:
        lines.append("## 最近活跃的模块")
        lines.append("")
        lines.append("| 模块 | 涉及提交数 |")
        lines.append("| --- | --- |")
        for area, count in sorted(recent_areas.items(), key=lambda kv: -kv[1])[:10]:
            lines.append(f"| `{area}` | {count} |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="do_print", action="store_true")
    parser.add_argument("--days", type=int, default=0, help="limit to the last N days")
    args = parser.parse_args()

    text = build(args.days or None)

    if args.do_print:
        print(text)
        return 0

    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
