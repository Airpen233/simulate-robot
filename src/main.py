"""Command-line demo for the minimal robot core."""

from __future__ import annotations

import sys

from .robot import Point, Robot, World


def build_demo_world() -> World:
    """Start with an empty world; add obstacles here to try avoidance."""
    return World()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print('用法: python -m src.main "go to 3, 4"')
        print('示例: python -m src.main "移动到 3, 4"')
        print('停止: python -m src.main "stop"')
        return 2

    command_text = " ".join(args)
    start = Point(0.0, 0.0)
    robot = Robot(pose=start, step_size=0.5)
    world = build_demo_world()

    try:
        result = robot.execute(command_text, world)
    except ValueError as exc:
        print(f"命令错误: {exc}")
        return 2

    print(f"起点: {start}")
    print(f"命令: {command_text}")
    print(f"结果: {result.status} - {result.message}")
    print(f"步数: {result.steps}")
    print(f"终点: {result.pose}")
    return 0 if result.status in {"reached", "stopped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
