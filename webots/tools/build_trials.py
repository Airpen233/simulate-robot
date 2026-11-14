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
    runner_of,
    scene_name,
)

LEDGER = ROOT / "logs" / "trials.csv"


def _mtime(path: Path | None) -> str:
    """Wall-clock time of the log file, or empty when unavailable."""

    if path is None:
        return ""
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return ""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

REPEAT_RE = re.compile(r"^(?P<base>.+?)_r(?P<index>\d+)$")
CONTROLLER_RESULT_RE = re.compile(r"RESULT:\s*(?P<result>\w+)")

COLUMNS = [
    "trial_id",
    "run",
    "runner",
    "recorded_at",
    "scene",
    "run_index",
    "category",
    "commit_at_run",
    "config_at_run",
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
    """Fingerprint of the CURRENT AvoidConfig.

    WARNING: this describes the working tree at generation time, not the
    configuration the run used. Logs carry no config snapshot, so for archived
    evidence the true configuration is unrecoverable. Do not put this value in
    the ledger: doing so labels every historical row with today's settings and
    looks authoritative while being wrong. See ``config_at_commit`` below for
    the closest honest substitute.
    """

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


def config_at_commit(commit: str) -> str:
    """Config hash that was in the tree at ``commit``, or empty if unavailable.

    This is a property of the code, not of any particular run. It is still a
    better answer than the live hash for old rows, because a row written before
    the config changed really did use that older code — provided the row's
    commit is known.
    """

    if not commit or commit == "unknown":
        return ""
    logic = "webots/controllers/robot_controller/logic/avoidance.py"
    try:
        source = git_show(commit, logic)
    except RuntimeError:
        return ""
    if not source:
        return ""
    return _hash_config_source(source)


def _hash_config_source(source: str) -> str:
    """Hash the AvoidConfig defaults parsed out of a source blob."""

    import hashlib
    import re

    block = re.search(r"class AvoidConfig:(.*?)(?=\n@dataclass|\nclass )", source, re.S)
    if not block:
        return ""
    fields = re.findall(r"^\s{4}(\w+)\s*:\s*[^=]+=\s*(.+?)\s*$", block.group(1), re.M)
    if not fields:
        return ""
    payload = ";".join(f"{name}={value}" for name, value in fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def git_show(commit: str, path: str) -> str:
    """Contents of ``path`` at ``commit``, empty when the file did not exist."""

    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout if result.returncode == 0 else ""


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


def commit_at(when: str) -> str:
    """Commit that was HEAD closest to ``when`` (an ISO-8601 UTC stamp).

    This is the honest reconstruction of "what code produced this log": pick
    the newest commit that already existed when the log was written. Returns an
    empty string when the stamp is missing or predates the repository, which is
    truthful — the log's provenance really is unknown then.

    Caveat worth stating in the ledger: mtime is the file's last write, not
    necessarily its creation, so a copied or touched file can claim a later
    commit than it used. It is the best available signal, not proof.
    """

    if not when:
        return ""
    result = subprocess.run(
        ["git", "rev-list", "-1", f"--before={when}", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout.strip()[:7] if result.returncode == 0 else ""


def collect() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    runs = all_runs()

    for run in runs:
        base, run_index = split_run(run)
        scene = normalize_scene(base)
        controller_path = find_run(run, "_controller.log")
        supervisor_log = find_run(run, "_supervisor.log")

        row: dict[str, object] = {
            "run": run,
            "runner": runner_of(supervisor_log)
            if supervisor_log is not None and supervisor_log.exists()
            else runner_of(controller_path)
            if controller_path is not None
            else "unknown",
            # Logs carry no absolute clock. mtime is the only wall-clock signal
            # available, so it is what a teammate can sort by.
            "recorded_at": _mtime(supervisor_log or controller_path),
            "scene": scene,
            "run_index": run_index,
            "category": category_of(base),
            "commit_at_run": "",
            "config_at_run": "",
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

        # Reconstruct which code produced this log from its mtime, rather than
        # stamping it with today's HEAD (which would be a quiet lie).
        stamp = str(row["recorded_at"])
        resolved = commit_at(stamp)
        row["commit_at_run"] = resolved
        row["config_at_run"] = config_at_commit(resolved) if resolved else ""

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
