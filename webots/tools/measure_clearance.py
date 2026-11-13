"""Measure the minimum geometric clearance between the e-puck and every obstacle.

Why this exists
---------------
``collision_samples`` from the Supervisor is a **false negative**. It counts
contact points produced by the physics solver, and at a 32 ms timestep a
zero-pressure graze does not create any. The front scenario recorded
``collision_samples=0`` while the true minimum clearance was **-0.17 mm** —
the robot physically overlapped the box.

This script computes the second acceptance channel that
``EXPERIMENT_WORKFLOW.md`` §4 requires:

    A. contact points  -> collision_samples (can miss grazes)
    B. geometry        -> min_clearance_m   (from Supervisor ground truth)

Acceptance needs both: A == 0 **and** B > 0.

Data sources
------------
- Ground-truth poses: ``*_supervisor.log`` lines
  ``POSE t=<t> pos=[x, y, z] yaw=<yaw> contacts=<n>``
- Obstacle boxes: ``logs/worlds/<scene>.json`` with ``{name, x, y, size}``

Geometry
--------
Obstacles are axis-aligned boxes of half-extent ``size / 2``. The e-puck body
is modelled as a cylinder of radius ``ROBOT_RADIUS_M``. Webots' official
``E-puck.proto`` declares:

    boundingObject Group {
      children [
        Pose { translation 0 0 0.025
               children [ Cylinder { height 0.045, radius 0.037 } ] }
        Pose { translation 0 0 0.0051
               children [ Box { size 0.05 0.04 0.01 } ] }
      ]
    }

so 0.037 m is the authoritative radius (the small 0.05 x 0.04 box at the base
sits inside that circle and does not change the footprint).

Limitation — sampling, not integration
--------------------------------------
The Supervisor logs a pose every 0.5 s. The reported clearance is therefore the
minimum over **sampled** poses, not a continuous minimum. Between two samples
the robot may pass closer. Treat the number as an upper bound on the true
minimum. Shrinking the Supervisor's log interval to 0.1 s tightens it at the
cost of 5x larger logs.

Interpreting the result — read this before quoting a number
------------------------------------------------------------
Across the 30 archived runs, every "graze" lands within a very narrow band:

    15 runs: surface-to-centre distance 36.27 - 36.83 mm
    robot radius 37 mm  ->  clearance -0.73 .. -0.17 mm

That clustering is not a coincidence and it is not motion noise. It is what a
**contact-constrained** body looks like: once the solver decides two shapes
touch, it keeps the penetration at roughly the contact tolerance instead of
letting the robot sink into the box. Six different scenes produce the very same
-0.17 mm because the geometry stalls at the same constraint, not because the
runs are identical.

So the honest reading of a small negative clearance is:

    "the robot was in sustained contact with the obstacle"

not "the robot overlapped it by exactly the reported depth". The magnitude below
zero is meaningless at this resolution; the **sign** is what matters.

Corroborating evidence for contact (rather than near-miss) in `fixed_front`:
the trajectory holds y at -0.11683 for two consecutive samples (t=11.30 and
11.81) while still advancing in x, i.e. the robot slid along the face instead of
passing freely — and its speed did **not** drop (7.9 cm/s), so it was not
blocked, it was rubbing.

Practical consequence: treat any clearance <= 0 as FAILED regardless of how small
the violation looks. Do not dismiss -0.17 mm as "numerical noise".

Usage
-----
    python tools/measure_clearance.py                 # every run in random_avoid
    python tools/measure_clearance.py --run fixed_front
    python tools/measure_clearance.py --json          # machine-readable output

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "logs" / "random_avoid"
WORLD_DIR = ROOT / "logs" / "worlds"

# Authoritative value from Webots R2025a E-puck.proto (boundingObject Cylinder).
ROBOT_RADIUS_M = 0.037

# The pose line the Supervisor writes every 0.5 s.
POSE_RE = re.compile(
    r"POSE\s+t=(?P<t>[-\d.]+)\s+"
    r"pos=\[(?P<x>[-\d.eE+]+),\s*(?P<y>[-\d.eE+]+),\s*(?P<z>[-\d.eE+]+)\]\s+"
    r"yaw=(?P<yaw>[-\d.]+)\s+contacts=(?P<contacts>\d+)"
)

# The scene line names the world file, which maps to the sidecar JSON.
SCENE_RE = re.compile(r"SCENE=(?P<path>.+?)\s+seed=")
TRUE_END_RE = re.compile(
    r"RESULT:\s*true_end\s+.*?error=(?P<error>[\d.]+)\s+"
    r"collision_samples=(?P<samples>\d+)"
)


def parse_poses(path: Path) -> list[tuple[float, float, float, int]]:
    """Return ``[(t, x, y, contacts), ...]`` from a Supervisor log."""

    poses: list[tuple[float, float, float, int]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = POSE_RE.search(line)
        if match:
            poses.append(
                (
                    float(match.group("t")),
                    float(match.group("x")),
                    float(match.group("y")),
                    int(match.group("contacts")),
                )
            )
    return poses


def parse_true_end(path: Path) -> dict[str, float] | None:
    """Return the final ground-truth error and collision count, if logged."""

    match = TRUE_END_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return None
    return {
        "true_error_m": float(match.group("error")),
        "collision_samples": int(match.group("samples")),
    }


def scene_name(path: Path) -> str | None:
    """Extract the world basename from the Supervisor's SCENE line."""

    match = SCENE_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return None
    return Path(match.group("path").strip().strip('"')).name


def load_obstacles(world_name: str) -> list[dict[str, float]] | None:
    """Load obstacle boxes for a world file from its sidecar JSON."""

    sidecar = WORLD_DIR / (Path(world_name).stem + ".json")
    if not sidecar.exists():
        return None
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    obstacles = data.get("obstacles") or []
    return [
        {"x": float(ob["x"]), "y": float(ob["y"]), "size": float(ob["size"])}
        for ob in obstacles
    ]


def clearance_at(
    px: float, py: float, obstacles: list[dict[str, float]], robot_radius: float
) -> float:
    """Signed distance from the robot's footprint edge to the nearest obstacle.

    Positive = free space, zero = touching, negative = overlapping.
    Returns ``inf`` when there are no obstacles.
    """

    best = math.inf
    for ob in obstacles:
        half = ob["size"] / 2.0
        # Distance from the point to the axis-aligned box (0 if inside).
        dx = max(abs(px - ob["x"]) - half, 0.0)
        dy = max(abs(py - ob["y"]) - half, 0.0)
        best = min(best, math.hypot(dx, dy) - robot_radius)
    return best


def measure(run: str, robot_radius: float = ROBOT_RADIUS_M) -> dict[str, object]:
    """Compute clearance statistics for one archived run."""

    supervisor = RUN_DIR / f"{run}_supervisor.log"
    result: dict[str, object] = {"run": run, "status": "ok"}

    if not supervisor.exists():
        result["status"] = "no_supervisor_log"
        return result

    poses = parse_poses(supervisor)
    if not poses:
        result["status"] = "no_pose_lines"
        return result

    world = scene_name(supervisor)
    result["world"] = world
    if not world:
        result["status"] = "no_scene_line"
        return result

    obstacles = load_obstacles(world)
    if obstacles is None:
        result["status"] = "no_sidecar_json"
        return result
    result["obstacle_count"] = len(obstacles)

    if not obstacles:
        result.update(
            min_clearance_m=None,
            note="scene has no obstacles; clearance undefined",
        )
        return result

    samples = [
        (clearance_at(x, y, obstacles, robot_radius), t, x, y)
        for t, x, y, _ in poses
    ]
    worst = min(samples)
    result.update(
        pose_samples=len(poses),
        min_clearance_m=round(worst[0], 6),
        min_clearance_at_t=round(worst[1], 2),
        min_clearance_at_xy=(round(worst[2], 4), round(worst[3], 4)),
        sample_interval_s=round(
            (poses[-1][0] - poses[0][0]) / max(len(poses) - 1, 1), 3
        ),
    )

    final = parse_true_end(supervisor)
    if final:
        result.update(final)
        # Dual-channel verdict from EXPERIMENT_WORKFLOW.md §4.
        contacts = final["collision_samples"]
        clear = worst[0]
        if contacts > 0:
            verdict = "COLLISION"
        elif clear <= 0.0:
            verdict = "CONTACT_NOT_DETECTED"
        else:
            verdict = "CLEAR"
        result["verdict"] = verdict
    else:
        result["verdict"] = "NO_TRUE_END"

    return result


def fmt_m(value: float | None) -> str:
    """Format a clearance in millimetres for the text table."""

    if value is None:
        return "     n/a"
    return f"{value * 1000:+7.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", help="limit to these run names")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument(
        "--robot-radius",
        type=float,
        default=ROBOT_RADIUS_M,
        help=f"e-puck body radius in metres (default {ROBOT_RADIUS_M})",
    )
    args = parser.parse_args()

    runs = args.run or sorted(
        p.name[: -len("_supervisor.log")] for p in RUN_DIR.glob("*_supervisor.log")
    )

    results = [measure(run, args.robot_radius) for run in runs]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    ok = [r for r in results if r.get("min_clearance_m") is not None]
    header = f"{'run':44s} {'pose':>5s} {'clearance':>10s} {'t@s':>6s} {'contacts':>8s}  verdict"
    print(f"robot radius = {args.robot_radius} m, clearance in mm (+free / -overlap)")
    print(header)
    print("-" * len(header))

    for r in results:
        if r.get("min_clearance_m") is None:
            print(f"{r['run'][:44]:44s} {'':>5s} {'':>10s} {'':>6s} {'':>8s}  {r['status']}")
            continue
        print(
            f"{r['run'][:44]:44s} {r.get('pose_samples', 0):5d} "
            f"{fmt_m(r['min_clearance_m']):>10s} {r.get('min_clearance_at_t', 0):6.2f} "
            f"{r.get('collision_samples', -1):8d}  {r.get('verdict', '?')}"
        )

    print()
    if ok:
        worst = min(ok, key=lambda r: r["min_clearance_m"])
        print(
            f"worst overall: {worst['run']}  "
            f"{worst['min_clearance_m'] * 1000:+.2f} mm  "
            f"at ({worst['min_clearance_at_xy'][0]}, {worst['min_clearance_at_xy'][1]})"
        )
        overlaps = [r for r in ok if r["min_clearance_m"] <= 0.0]
        hidden = [r for r in overlaps if r.get("collision_samples", 0) == 0]
        print(
            f"geometric overlap: {len(overlaps)}/{len(ok)} runs"
            f"  |  of those, undetected by contacts: {len(hidden)}"
        )
        if hidden:
            print("  undetected grazes (collision_samples=0 but clearance<=0):")
            for r in hidden:
                print(
                    f"    {r['run']}  {r['min_clearance_m'] * 1000:+.2f} mm"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
