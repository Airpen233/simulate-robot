"""Render ``PROGRESS.md`` from the trial ledger.

Why this exists
---------------
Two people work in separate checkouts on separate machines. Nothing is shared
except this repository, so "how far along is the other person" has to be
readable from a committed file — not from memory, not from chat.

``PROGRESS.md`` answers three questions in one screen:

* who has run what, and when they last did
* how the acceptance rate currently stands, by scene
* which runs touched an obstacle (the failure mode the contact-point channel
  cannot see)

Everything here is derived from ``logs/trials.csv``; nothing is hand-written,
so the page cannot drift from the evidence.

Usage
-----
    python tools/progress.py             # write logs/../PROGRESS.md
    python tools/progress.py --print     # show it, write nothing

No external dependencies.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_trials import LEDGER, collect, stability  # noqa: E402

OUTPUT = ROOT.parent / "PROGRESS.md"


def load_rows() -> list[dict[str, str]]:
    """Read the committed ledger, rebuilding it when missing."""

    if not LEDGER.exists():
        return [dict(r) for r in collect()]
    with LEDGER.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _passes(row: dict[str, str]) -> bool:
    """Same three-part criterion as the workflow document.

    ``min_clearance_m`` is empty for obstacle-free scenes; those skip the
    clearance test rather than fail it.
    """

    if row.get("true_success_3cm") != "yes":
        return False
    if row.get("min_clearance_m", "") == "":
        return True
    return row.get("clearance_ok") == "yes"


def fmt_ts(value: str) -> str:
    """Render an ISO timestamp as a compact UTC date, or a dash."""

    if not value:
        return "—"
    try:
        moment = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return value
    return moment.strftime("%Y-%m-%d %H:%M UTC")


def build(rows: list[dict[str, str]]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# 项目进度")
    lines.append("")
    lines.append(
        "> 本文件由 `webots/tools/progress.py` 从 `webots/logs/trials.csv` 自动生成。"
    )
    lines.append("> 不要手工编辑——下次生成会覆盖。改数据请改日志，然后重新生成。")
    lines.append(f"> 生成时间：{now}")
    lines.append("")

    # ---- who is doing what -------------------------------------------------
    per_runner: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        per_runner[row.get("runner") or "unknown"].append(row)

    lines.append("## 谁跑到哪了")
    lines.append("")
    lines.append("| 运行者 | 运行数 | 通过 | 最近一次 |")
    lines.append("| --- | --- | --- | --- |")
    for runner in sorted(per_runner):
        members = per_runner[runner]
        passed = sum(1 for m in members if _passes(m))
        stamps = [m.get("recorded_at", "") for m in members if m.get("recorded_at")]
        latest = fmt_ts(max(stamps)) if stamps else "—"
        lines.append(
            f"| `{runner}` | {len(members)} | {passed} | {latest} |"
        )
    lines.append("")

    # ---- scene level acceptance -------------------------------------------
    table = [t for t in stability([dict(r) for r in rows], "scene") if t["n"] > 1]
    if table:
        passed_scenes = sum(1 for t in table if t["verdict"] == "STABLE_PASS")
        lines.append("## 场景级验收")
        lines.append("")
        lines.append(
            f"判据：`reached` + `error ≤ 3cm` + `min_clearance > 0`"
            f"（无障碍场景跳过间隙项）。"
            f"**{passed_scenes}/{len(table)} 个场景稳定通过。**"
        )
        lines.append("")
        lines.append("| 场景 | 次数 | 通过 | 判定 | 误差范围 (m) | 间隙范围 (mm) |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for t in sorted(table, key=lambda x: (x["verdict"] != "STABLE_PASS", x["scene"])):
            err = f"{t['err_min']}–{t['err_max']}" if t["err_min"] else ""
            clr = f"{t['clr_min']}~{t['clr_max']}" if t["clr_min"] else "无障"
            lines.append(
                f"| `{t['scene']}` | {t['n']} | {t['pass']}/{t['n']} | "
                f"{t['verdict']} | {err} | {clr} |"
            )
        lines.append("")

    # ---- the failure mode contacts cannot see -----------------------------
    grazes = [r for r in rows if r.get("min_clearance_m", "") and float(r["min_clearance_m"]) <= 0.0]
    undetected = [g for g in grazes if (g.get("collision_samples") or "0") == "0"]
    lines.append("## 贴障（接触点通道看不见的那类）")
    lines.append("")
    if grazes:
        lines.append(
            f"几何间隙 ≤ 0 的运行 **{len(grazes)}** 个，"
            f"其中接触点通道未报出 **{len(undetected)}** 个。"
        )
        lines.append("")
        lines.append("| 运行 | 场景 | 间隙 (mm) | 接触点 |")
        lines.append("| --- | --- | --- | --- |")
        for g in sorted(grazes, key=lambda x: float(x["min_clearance_m"]))[:15]:
            lines.append(
                f"| `{g['run']}` | `{g['scene']}` | "
                f"{float(g['min_clearance_m']) * 1000:+.2f} | "
                f"{g.get('collision_samples') or '0'} |"
            )
        if len(grazes) > 15:
            lines.append("")
            lines.append(f"（只列最差的 15 个，共 {len(grazes)} 个）")
    else:
        lines.append("暂无。")
    lines.append("")

    # ---- what is next ------------------------------------------------------
    lines.append("## 下一步")
    lines.append("")
    lines.append("详见 [Notion 团队主页](https://app.notion.com/p/4173f761570d8156bfb5c2279fa1dfd7)。")
    lines.append("")
    lines.append("已知未解决：")
    lines.append("")
    lines.append("- `random_seed_4` 假到达（真值偏 45 cm）：根因是前向传感器照不到斜前方障碍物")
    lines.append("- 侧向传感器 ps1/ps2/ps5/ps6 无标定数据")
    lines.append("- 场景仅 17 个，统计意义不足")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="do_print", action="store_true")
    args = parser.parse_args()

    rows = load_rows()
    text = build(rows)

    if args.do_print:
        print(text)
        return 0

    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
