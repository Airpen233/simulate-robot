"""Summarize controller + Supervisor logs from the random-obstacle suite.

Parses every ``*_controller.log`` / ``*_supervisor.log`` pair in
``webots/logs/random_avoid`` and writes ``summary.csv`` plus a Markdown table.
No external dependencies.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "logs" / "random_avoid"
TARGET = (1.0, 0.0)
TRUE_TOLERANCE_M = 0.03


def parse_controller(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    result = re.findall(r"RESULT:\s*(\w+)", text)
    summary = re.findall(r"SUMMARY state=(\w+) attempts=(\d+) turns=(\d+) backups=(\d+) recovers=(\d+)", text)
    data: dict[str, object] = {
        "controller_result": result[-1] if result else "missing",
        "attempts": 0,
        "turns": 0,
        "backups": 0,
        "recovers": 0,
    }
    if summary:
        _, attempts, turns, backups, recovers = summary[-1]
        data.update(
            attempts=int(attempts),
            turns=int(turns),
            backups=int(backups),
            recovers=int(recovers),
        )
    return data


def parse_supervisor(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    true_end = re.findall(
        r"RESULT: true_end pos=\[([-\d.]+),([-\d.]+)\] yaw=([-\d.]+) target=\(([-\d.]+),([-\d.]+)\) "
        r"error=([-\d.]+) collision_samples=(\d+) max_contacts=(\d+)",
        text,
    )
    if not true_end:
        return {
            "true_x": None,
            "true_y": None,
            "true_yaw": None,
            "true_error": None,
            "collision_samples": 0,
            "max_contacts": 0,
        }
    x, y, yaw, tx, ty, error, samples, max_contacts = true_end[-1]
    return {
        "true_x": float(x),
        "true_y": float(y),
        "true_yaw": float(yaw),
        "true_error": float(error),
        "collision_samples": int(samples),
        "max_contacts": int(max_contacts),
    }


def main() -> int:
    rows = []
    for controller_path in sorted(RUN_DIR.glob("*_controller.log")):
        name = controller_path.name[: -len("_controller.log")]
        if not (name.startswith("fixed_") or name.startswith("random_seed_")):
            continue
        supervisor_path = RUN_DIR / f"{name}_supervisor.log"
        scene_path = RUN_DIR / f"{name}_world.json"
        row = {"run": name}
        row.update(parse_controller(controller_path))
        row.update(parse_supervisor(supervisor_path) if supervisor_path.exists() else parse_supervisor(Path("/nonexistent")))
        if scene_path.exists():
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            row["scenario"] = scene.get("scenario", "")
            row["seed"] = scene.get("seed", "")
            row["obstacles"] = len(scene.get("obstacles", []))
            row["path_found"] = scene.get("path_found", "")
        else:
            row["scenario"] = ""
            row["seed"] = ""
            row["obstacles"] = ""
            row["path_found"] = ""
        error = row["true_error"]
        reached = row["controller_result"] == "reached"
        collision = (row["collision_samples"] or 0) > 0
        row["controller_reached"] = reached
        row["true_success_3cm"] = bool(reached and error is not None and error <= TRUE_TOLERANCE_M and not collision)
        rows.append(row)

    if not rows:
        print("NO_RUNS")
        return 1

    fieldnames = [
        "run",
        "scenario",
        "seed",
        "obstacles",
        "path_found",
        "controller_result",
        "controller_reached",
        "true_x",
        "true_y",
        "true_yaw",
        "true_error",
        "true_success_3cm",
        "collision_samples",
        "max_contacts",
        "attempts",
        "turns",
        "backups",
        "recovers",
    ]
    csv_path = RUN_DIR / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    reached = sum(1 for row in rows if row["controller_reached"])
    success = sum(1 for row in rows if row["true_success_3cm"])
    collisions = sum(1 for row in rows if (row["collision_samples"] or 0) > 0)
    errors = [row["true_error"] for row in rows if row["true_error"] is not None]
    reached_errors = [row["true_error"] for row in rows if row["controller_reached"] and row["true_error"] is not None]
    print(f"runs={total} controller_reached={reached} true_success_3cm={success} collisions={collisions}")
    if errors:
        print(f"true_error_all mean={sum(errors) / len(errors):.4f} max={max(errors):.4f}")
    if reached_errors:
        print(f"true_error_reached mean={sum(reached_errors) / len(reached_errors):.4f} max={max(reached_errors):.4f}")
    print(f"summary_csv={csv_path}")
    print()
    print("| run | result | true_error | collision | attempts | turns | backups | recovers |")
    print("|---|---|---|---|---|---|---|---|")
    for row in rows:
        error = "n/a" if row["true_error"] is None else f"{row['true_error']:.4f}"
        print(
            f"| {row['run']} | {row['controller_result']} | {error} | "
            f"{row['collision_samples']} | {row['attempts']} | {row['turns']} | "
            f"{row['backups']} | {row['recovers']} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
