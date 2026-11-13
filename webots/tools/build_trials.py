"""Build and maintain the immutable trial ledger (``trials.csv``).

Why this exists
---------------
``EXPERIMENT_WORKFLOW.md`` §2 requires one row per attempt, appended at
collection time and never edited afterwards. This script produces that ledger
from the archived logs so the numbers in every report stay traceable to
evidence.

The ledger is *derived*, but the discipline is what matters: each row carries
the code commit and the config fingerprint, so a later report cannot silently
mix results produced by different code or parameters.

Repeat runs are recognised by the ``_r<N>`` suffix (``fixed_front_r2``,
``random_seed_3_r2``). The first run of a scenario has no suffix and is
``run_index = 1``.

Usage
-----
    python tools/build_trials.py                # write logs/trials.csv
    python tools/build_trials.py --print        # show the table, write nothing
    python tools/build_trials.py --group-by scene

No external dependencies.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from measure_clearance import (  # noqa: E402
    RUN_DIR,
    all_runs,
    clearance_at,
    find_run,
    load_obstacles,
    parse_poses,
    parse_true_end,
    scene_name,
)

LEDGER = ROOT / "logs" / "trials.csv"

REPEAT_RE = re.compile(r"^(?P<base>.+?)_r(?P<index>\d+)$")
CONTROLLER_RESULT_RE = re.compile(r"RESULT:\s*(?P<result>\w+)")

COLUMNS = [
    "trial_id",
    "run",
    "scene",
    "run_index",
    "category",
    "code_commit",
    "config_hash",
    "controller_result",
    "true_error_m",
    "true_success_3cm",
    "min_clearance_m",
    "clearance_ok",
    "collision_samples",
    "verdict",
    "pose_samples",
]


def git_commit() -> str:
    """Short hash of the commit the workspace is built from."""

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def config_hash() -> str:
    """Fingerprint of AvoidConfig so parameter drift is visible in the ledger."""

    import hashlib
    import json
    from dataclasses import asdict

    logic = ROOT / "controllers" / "robot_controller" / "logic"
    sys.path.insert(0, str(logic))
    try:
        from avoidance import AvoidConfig  # noqa: PLC0415

        payload = json.dumps(asdict(AvoidConfig()), sort_keys=True, default=str)
    except Exception:  # noqa: BLE001
        return "unknown"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def split_run(name: str) -> tuple[str, int]:
    """``fixed_front_r2`` -> (``fixed_front``, 2); ``fixed_front`` -> (..., 1)."""

    match = REPEAT_RE.match(name)
    if match:
        return match.group("base"), int(match.group("index"))
    return name, 1


# The original fixed runs are named ``fixed_<scene>`` while the repeat runner
# emits ``<scene>_r<N>``. Both must collapse to one key or the ledger shows two
# half-empty scenes instead of one scene with N=3.
SCENE_ALIASES = {
    "fixed_front": "front",
    "fixed_left_blocked": "left_blocked",
    "fixed_right_blocked": "right_blocked",
    "fixed_both_blocked": "both_blocked",
    "fixed_no_path": "no_path",
    "fixed_clear": "clear",
    "fixed_fixed_seed7": "fixed_seed7",
}


def normalize_scene(base: str) -> str:
    """Map a base run name onto the canonical scene key."""

    return SCENE_ALIASES.get(base, base)


def category_of(base: str) -> str:
    """Group a base run name into the family it belongs to."""

    if base.startswith("random_seed_"):
        return "random"
    if base.startswith("fixed_"):
        return "fixed"
    if base.startswith("test_"):
        return "test"
    if base.startswith("beginner_"):
        return "beginner"
    if base.startswith("stage2_"):
        return "stage2"
    if base == "takeover_check":
        return "check"
    return "other"


def collect() -> list[dict[str, object]]:
    commit = git_commit()
    cfg = config_hash()
    rows: list[dict[str, object]] = []

    runs = all_runs()

    for run in runs:
        base, run_index = split_run(run)
        scene = normalize_scene(base)
        controller_path = find_run(run, "_controller.log")
        supervisor_log = find_run(run, "_supervisor.log")

        row: dict[str, object] = {
            "run": run,
            "scene": scene,
            "run_index": run_index,
            "category": category_of(base),
            "code_commit": commit,
            "config_hash": cfg,
            "controller_result": "",
            "true_error_m": "",
            "true_success_3cm": "",
            "min_clearance_m": "",
            "clearance_ok": "",
            "collision_samples": "",
            "verdict": "",
            "pose_samples": 0,
        }

        if controller_path is not None and controller_path.exists():
            match = CONTROLLER_RESULT_RE.search(
                controller_path.read_text(encoding="utf-8", errors="replace")
            )
            if match:
                row["controller_result"] = match.group("result")

        if supervisor_log is None or not supervisor_log.exists():
            row["verdict"] = "NO_SUPERVISOR_LOG"
            rows.append(row)
            continue

        final = parse_true_end(supervisor_log)
        if final:
            row["true_error_m"] = f"{final['true_error_m']:.5f}"
            row["true_success_3cm"] = "yes" if final["true_error_m"] <= 0.03 else "no"
            row["collision_samples"] = final["collision_samples"]

        world = scene_name(supervisor_log)
        poses = parse_poses(supervisor_log)
        row["pose_samples"] = len(poses)

        obstacles = load_obstacles(world) if world else None
        if poses and obstacles:
            worst = min(
                clearance_at(x, y, obstacles, 0.037) for _, x, y, _ in poses
            )
            row["min_clearance_m"] = f"{worst:.6f}"
            row["clearance_ok"] = "yes" if worst > 0.0 else "no"

            if final:
                if final["collision_samples"] > 0:
                    row["verdict"] = "COLLISION"
                elif worst <= 0.0:
                    row["verdict"] = "CONTACT_NOT_DETECTED"
                else:
                    row["verdict"] = "CLEAR"
        elif not final:
            row["verdict"] = "NO_TRUE_END"

        rows.append(row)

    for index, row in enumerate(rows, start=1):
        row["trial_id"] = f"T{index:04d}"

    return rows


def stability(rows: list[dict[str, object]], key: str) -> list[dict[str, object]]:
    """Per-scene stability across repetitions (``EXPERIMENT_WORKFLOW.md`` §1)."""

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)

    out = []
    for scene, members in sorted(groups.items()):
        members.sort(key=lambda r: int(r["run_index"]))
        n = len(members)

        # A scene with no obstacles has no clearance to violate, so the
        # clearance criterion is not applicable rather than failed. Treating
        # the empty value as "not ok" would make every obstacle-free scene
        # permanently un-passable (the `clear` scene hit exactly this).
        def _passes(row: dict[str, object]) -> bool:
            error_ok = row["true_success_3cm"] == "yes"
            clearance_na = row["min_clearance_m"] == ""
            clearance_ok = row["clearance_ok"] == "yes"
            return bool(error_ok and (clearance_ok or clearance_na))

        passes = sum(1 for m in members if _passes(m))
        results = {str(m["controller_result"]) for m in members}
        errors = [
            float(m["true_error_m"]) for m in members if m["true_error_m"] != ""
        ]
        clearances = [
            float(m["min_clearance_m"]) for m in members if m["min_clearance_m"] != ""
        ]
        if n < 2:
            verdict = "SINGLE"
        elif passes == n:
            verdict = "STABLE_PASS"
        elif passes == 0:
            verdict = "STABLE_FAIL"
        else:
            verdict = "UNSTABLE"

        out.append(
            {
                "scene": scene,
                "n": n,
                "pass": passes,
                "verdict": verdict,
                "clearance_applicable": "yes" if clearances else "no",
                "result_variety": len(results),
                "err_min": f"{min(errors):.4f}" if errors else "",
                "err_max": f"{max(errors):.4f}" if errors else "",
                "clr_min": f"{min(clearances) * 1000:+.2f}" if clearances else "",
                "clr_max": f"{max(clearances) * 1000:+.2f}" if clearances else "",
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="do_print", action="store_true")
    parser.add_argument("--group-by", default="scene")
    args = parser.parse_args()

    rows = collect()

    if args.do_print:
        header = f"{'trial':6s} {'run':40s} {'idx':>3s} {'ctrl':10s} {'err_m':>8s} {'clr_mm':>8s}  verdict"
        print(header)
        print("-" * len(header))
        for r in rows:
            clr = f"{float(r['min_clearance_m']) * 1000:+.2f}" if r["min_clearance_m"] != "" else ""
            err = r["true_error_m"] if r["true_error_m"] != "" else ""
            print(
                f"{r['trial_id']:6s} {str(r['run'])[:40]:40s} {r['run_index']:3d} "
                f"{str(r['controller_result'])[:10]:10s} {err:>8s} {clr:>8s}  {r['verdict']}"
            )
    else:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {LEDGER.relative_to(ROOT)}  ({len(rows)} rows)")

    table = stability(rows, args.group_by)
    multi = [t for t in table if t["n"] > 1]
    print()
    print(f"per-{args.group_by} stability  (repeat runs only, N>1: {len(multi)} scenes)")
    head = f"{'scene':22s} {'n':>2s} {'pass':>5s} {'verdict':14s} {'err range (m)':>18s} {'clr range (mm)':>18s}"
    print(head)
    print("-" * len(head))
    for t in sorted(table, key=lambda x: (-x["n"], x["scene"])):
        err_r = f"{t['err_min']}-{t['err_max']}" if t["err_min"] else ""
        clr_r = f"{t['clr_min']}..{t['clr_max']}" if t["clr_min"] else ""
        print(
            f"{t['scene'][:22]:22s} {t['n']:2d} {t['pass']:2d}/{t['n']:<2d} "
            f"{t['verdict']:14s} {err_r:>18s} {clr_r:>18s}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
