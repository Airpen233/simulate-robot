"""Generate reproducible Webots worlds for the random-obstacle avoidance stage.

Standard library only. The arena is 2.2 x 2.2 m because a 1.6 x 1.6 m arena
centred at the origin has its right wall at x=0.8, while the requested target
is (1.0, 0.0). The 2.2 m arena keeps the target 0.1 m inside the wall, then
adds robot/safety margins.

Usage examples:
  python generate_random_world.py --scenario fixed --seed 7
  python generate_random_world.py --scenario scenarios
  python generate_random_world.py --scenario random --seed 1
  python generate_random_world.py --self-test
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

ARENA_SIZE = 2.2
HALF = ARENA_SIZE / 2.0
TARGET = (1.0, 0.0)
START = (0.0, 0.0)
ROBOT_RADIUS = 0.045
WALL_MARGIN = 0.10
START_TARGET_MARGIN = 0.10
OBSTACLE_GAP = 0.08
GRID_STEP = 0.05
PATH_INFLATE = ROBOT_RADIUS + 0.020

WEBOTS_DIR = Path(__file__).resolve().parents[1]
WORLDS_DIR = WEBOTS_DIR / "worlds"
GENERATED_DIR = WORLDS_DIR / "generated"
SCENARIOS_DIR = WORLDS_DIR / "scenarios"
WORLD_LOGS_DIR = WEBOTS_DIR / "logs" / "worlds"

COLORS = [
    "0.80 0.20 0.20",
    "0.90 0.50 0.10",
    "0.15 0.45 0.80",
    "0.55 0.20 0.75",
    "0.20 0.65 0.45",
    "0.85 0.75 0.15",
]

FIXED_SCENARIOS: dict[str, list[tuple[float, float, float]]] = {
    "clear": [],
    "front": [(0.45, 0.0, 0.16)],
    "left_blocked": [(0.40, 0.10, 0.16)],
    "right_blocked": [(0.40, -0.10, 0.16)],
    "both_blocked": [(0.42, 0.0, 0.16), (0.30, 0.24, 0.14), (0.30, -0.24, 0.14)],
    "no_path": [
        (0.36, 0.0, 0.16),
        (0.12, 0.25, 0.14),
        (0.12, -0.25, 0.14),
        (-0.24, 0.0, 0.14),
    ],
}


@dataclass(frozen=True)
class Obstacle:
    x: float
    y: float
    size: float


def _start_clear(obstacle: Obstacle) -> bool:
    return math.hypot(obstacle.x - START[0], obstacle.y - START[1]) >= (
        ROBOT_RADIUS + obstacle.size / 2.0 + START_TARGET_MARGIN
    )


def _target_clear(obstacle: Obstacle) -> bool:
    return math.hypot(obstacle.x - TARGET[0], obstacle.y - TARGET[1]) >= (
        ROBOT_RADIUS + obstacle.size / 2.0 + START_TARGET_MARGIN
    )


def _wall_clear(obstacle: Obstacle) -> bool:
    half = obstacle.size / 2.0
    return (
        abs(obstacle.x) + half <= HALF - WALL_MARGIN
        and abs(obstacle.y) + half <= HALF - WALL_MARGIN
    )


def _separated(first: Obstacle, second: Obstacle) -> bool:
    dx = abs(first.x - second.x)
    dy = abs(first.y - second.y)
    needed = (first.size + second.size) / 2.0 + OBSTACLE_GAP
    return dx >= needed or dy >= needed


def _blocked_cells(obstacles: list[Obstacle]) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    steps = int(round(ARENA_SIZE / GRID_STEP))
    for obstacle in obstacles:
        half = obstacle.size / 2.0 + PATH_INFLATE
        for ix in range(steps + 1):
            x = -HALF + ix * GRID_STEP
            if abs(x - obstacle.x) > half:
                continue
            for iy in range(steps + 1):
                y = -HALF + iy * GRID_STEP
                if abs(y - obstacle.y) <= half:
                    cells.add((ix, iy))
    return cells


def _cell(point: tuple[float, float]) -> tuple[int, int]:
    return (
        int(round((point[0] + HALF) / GRID_STEP)),
        int(round((point[1] + HALF) / GRID_STEP)),
    )


def has_path(obstacles: list[Obstacle]) -> bool:
    """Coarse 4-neighbour BFS with obstacles inflated by robot + safety margin."""

    steps = int(round(ARENA_SIZE / GRID_STEP))
    blocked = _blocked_cells(obstacles)
    start = _cell(START)
    goal = _cell(TARGET)
    if start in blocked or goal in blocked:
        return False
    queue = [start]
    seen = {start}
    while queue:
        x, y = queue.pop(0)
        if (x, y) == goal:
            return True
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx <= steps and 0 <= ny <= steps):
                continue
            if (nx, ny) in blocked or (nx, ny) in seen:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return False


def validate_layout(obstacles: list[Obstacle]) -> tuple[bool, str]:
    for obstacle in obstacles:
        if not _start_clear(obstacle):
            return False, f"obstacle at ({obstacle.x:.2f},{obstacle.y:.2f}) overlaps robot start"
        if not _target_clear(obstacle):
            return False, f"obstacle at ({obstacle.x:.2f},{obstacle.y:.2f}) overlaps target"
        if not _wall_clear(obstacle):
            return False, f"obstacle at ({obstacle.x:.2f},{obstacle.y:.2f}) intersects wall margin"
    for i, first in enumerate(obstacles):
        for second in obstacles[i + 1 :]:
            if not _separated(first, second):
                return False, "obstacles are too close"
    if not has_path(obstacles):
        return False, "no coarse path from start to target"
    return True, "ok"


def _route_challenge(obstacles: list[Obstacle]) -> bool:
    """True if at least one obstacle is near the start->target corridor."""

    return any(0.20 <= obstacle.x <= 0.90 and abs(obstacle.y) <= 0.22 for obstacle in obstacles)


def random_layout(seed: int, count: int) -> tuple[list[Obstacle], int]:
    rng = random.Random(seed)
    for attempt in range(1, 2001):
        obstacles: list[Obstacle] = []
        for _ in range(count):
            size = rng.uniform(0.12, 0.18)
            half = size / 2.0
            x = rng.uniform(-HALF + WALL_MARGIN + half, HALF - WALL_MARGIN - half)
            y = rng.uniform(-HALF + WALL_MARGIN + half, HALF - WALL_MARGIN - half)
            obstacles.append(Obstacle(round(x, 3), round(y, 3), round(size, 3)))
        if not _route_challenge(obstacles) and obstacles:
            # Ensure every random layout actually challenges the direct route;
            # the BFS check below still guarantees a feasible path remains.
            index = rng.randrange(len(obstacles))
            size = rng.uniform(0.12, 0.18)
            obstacles[index] = Obstacle(
                round(rng.uniform(0.30, 0.75), 3),
                round(rng.uniform(-0.18, 0.18), 3),
                round(size, 3),
            )
        ok, _ = validate_layout(obstacles)
        if ok:
            return obstacles, attempt
    raise RuntimeError(f"could not generate {count} obstacles for seed {seed}")


def _obstacle_block(obstacle: Obstacle, index: int) -> str:
    color = COLORS[index % len(COLORS)]
    size = obstacle.size
    return f"""DEF OBSTACLE{index + 1} Solid {{
  translation {obstacle.x:.3f} {obstacle.y:.3f} 0
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor {color}
        roughness 0.5
        metalness 0
      }}
      geometry Box {{
        size {size:.3f} {size:.3f} {size:.3f}
      }}
    }}
  ]
  name "obstacle {index + 1}"
  boundingObject Box {{
    size {size:.3f} {size:.3f} {size:.3f}
  }}
}}"""


def world_text(scenario: str, seed: int, obstacles: list[Obstacle]) -> str:
    blocks = "\n".join(_obstacle_block(obstacle, i) for i, obstacle in enumerate(obstacles))
    return f"""#VRML_SIM R2025a utf8

EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/backgrounds/protos/TexturedBackground.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/backgrounds/protos/TexturedBackgroundLight.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/floors/protos/RectangleArena.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/robots/gctronic/e-puck/protos/E-puck.proto"

WorldInfo {{
  info [
    "Simulate Robot random-obstacle stage: scenario={scenario} seed={seed} target=(1.0,0.0)."
  ]
  title "Simulate Robot - random obstacles {scenario}"
  basicTimeStep 32
}}
Viewpoint {{
  orientation -0.2324493692067285 -0.14943881545798998 0.9610594836896971 3.9676615263416637
  position 0.2768847838918187 0.2403033535301425 0.26892434176287777
  follow "e-puck"
}}
TexturedBackground {{
}}
TexturedBackgroundLight {{
}}
RectangleArena {{
  floorSize {ARENA_SIZE} {ARENA_SIZE}
}}
{blocks}
DEF E_PUCK E-puck {{
  controller "avoid_controller"
}}
Robot {{
  controller "avoid_supervisor"
  supervisor TRUE
}}
Pose {{
  translation 1.0 0.02 0
  children [
    Shape {{
      appearance PBRAppearance {{
        baseColor 0.1 0.8 0.1
        roughness 0.5
        metalness 0
      }}
      geometry Cylinder {{
        height 0.01
        radius 0.07
      }}
    }}
  ]
}}
"""


def write_world(
    scenario: str,
    seed: int,
    obstacles: list[Obstacle],
    world_path: Path,
) -> dict[str, object]:
    world_path.parent.mkdir(parents=True, exist_ok=True)
    world_path.write_text(world_text(scenario, seed, obstacles), encoding="utf-8")
    WORLD_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    info: dict[str, object] = {
        "scenario": scenario,
        "seed": seed,
        "world": str(world_path),
        "arena_size_m": ARENA_SIZE,
        "start": list(START),
        "target": list(TARGET),
        "path_found": has_path(obstacles),
        "obstacles": [
            {"name": f"OBSTACLE{i + 1}", "x": o.x, "y": o.y, "size": o.size}
            for i, o in enumerate(obstacles)
        ],
    }
    json_path = WORLD_LOGS_DIR / f"{world_path.stem}.json"
    json_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        default="fixed",
        choices=["fixed", "clear", "front", "left_blocked", "right_blocked", "both_blocked", "no_path", "random", "scenarios"],
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=0, help="random obstacle count; 0 = random 4..6")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        for seed in range(1, 21):
            count = 4 + seed % 3
            obstacles, attempts = random_layout(seed, count)
            ok, reason = validate_layout(obstacles)
            if not ok:
                raise SystemExit(f"self-test failed seed={seed}: {reason}")
            print(f"seed={seed} count={count} attempts={attempts} ok")
        print("SELF_TEST_OK")
        return 0

    if args.scenario == "scenarios":
        for name, spec in FIXED_SCENARIOS.items():
            obstacles = [Obstacle(x, y, size) for x, y, size in spec]
            ok, reason = validate_layout(obstacles)
            info = write_world(
                name,
                args.seed,
                obstacles,
                WORLDS_DIR / f"stage2_scenario_{name}.wbt",
            )
            print(f"{name}: path={info['path_found']} validation={reason}")
        return 0

    if args.scenario == "fixed":
        count = args.count or 4
        obstacles, attempts = random_layout(args.seed, count)
        info = write_world("fixed", args.seed, obstacles, WORLDS_DIR / "stage2_random_obstacles.wbt")
        print(f"fixed seed={args.seed} attempts={attempts} obstacles={len(obstacles)} path={info['path_found']}")
        return 0

    if args.scenario == "random":
        count = args.count or (4 + args.seed % 3)
        obstacles, attempts = random_layout(args.seed, count)
        info = write_world(
            "random",
            args.seed,
            obstacles,
            WORLDS_DIR / f"stage2_random_seed_{args.seed}.wbt",
        )
        print(f"random seed={args.seed} attempts={attempts} obstacles={len(obstacles)} path={info['path_found']}")
        return 0

    spec = FIXED_SCENARIOS[args.scenario]
    obstacles = [Obstacle(x, y, size) for x, y, size in spec]
    info = write_world(args.scenario, args.seed, obstacles, SCENARIOS_DIR / f"{args.scenario}.wbt")
    print(f"{args.scenario}: obstacles={len(obstacles)} path={info['path_found']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
