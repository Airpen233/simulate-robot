"""Minimal command-driven robot core.

This module deliberately stays in 2D. It provides a small, testable
navigation loop that can later be connected to Webots or ROS 2 without
changing the command model.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class Point:
    """A position in the robot's 2D world."""

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def __str__(self) -> str:
        return f"({self.x:.1f}, {self.y:.1f})"


@dataclass(frozen=True)
class World:
    """The parts of the world the current robot needs to know about."""

    obstacles: frozenset[Point] = frozenset()

    def is_blocked(self, point: Point) -> bool:
        return point in self.obstacles


@dataclass(frozen=True)
class Command:
    """A parsed user command."""

    action: str
    target: Point | None = None


@dataclass(frozen=True)
class Result:
    """The outcome of executing one command."""

    status: str
    pose: Point
    steps: int
    message: str


_MOVE_PATTERNS = (
    re.compile(
        r"^(?:go|move)\s+to\s+(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)$"
    ),
    re.compile(
        r"^(?:移动到?|去到?|导航到?)\s*\(?\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*\)?$"
    ),
)
_STOP_PATTERN = re.compile(r"^(?:stop|halt|停止|停下)$")


def parse_command(text: str) -> Command:
    """Turn a small set of Chinese/English commands into a Command.

    Supported examples:
      - "go to 3, 4"
      - "move to 3 4"
      - "移动到 3, 4"
      - "停止" / "stop"
    """

    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        raise ValueError("命令不能为空")
    if _STOP_PATTERN.match(normalized):
        return Command(action="stop")
    for pattern in _MOVE_PATTERNS:
        match = pattern.match(normalized)
        if match:
            x_text, y_text = match.groups()
            return Command(action="move", target=Point(float(x_text), float(y_text)))
    raise ValueError(f"无法理解的命令：{text!r}")


class Robot:
    """A simple wheeled robot that moves toward a target point."""

    def __init__(
        self,
        pose: Point | None = None,
        step_size: float = 0.5,
        max_steps: int = 10_000,
    ) -> None:
        if step_size <= 0:
            raise ValueError("step_size 必须大于 0")
        if max_steps <= 0:
            raise ValueError("max_steps 必须大于 0")
        self.pose = pose or Point(0.0, 0.0)
        self.step_size = step_size
        self.max_steps = max_steps

    def move_to(self, target: Point, world: World) -> Result:
        """Move in small straight-line steps until target or obstacle."""

        steps = 0
        while self.pose.distance_to(target) > 1e-9 and steps < self.max_steps:
            remaining = self.pose.distance_to(target)
            step = min(self.step_size, remaining)
            next_pose = Point(
                self.pose.x + (target.x - self.pose.x) / remaining * step,
                self.pose.y + (target.y - self.pose.y) / remaining * step,
            )
            if world.is_blocked(next_pose):
                return Result(
                    status="blocked",
                    pose=self.pose,
                    steps=steps,
                    message=f"前方 {next_pose} 有障碍，机器人已停止",
                )
            self.pose = next_pose
            steps += 1

        if self.pose.distance_to(target) <= 1e-9:
            return Result(
                status="reached",
                pose=self.pose,
                steps=steps,
                message=f"已到达目标 {target}",
            )
        return Result(
            status="timeout",
            pose=self.pose,
            steps=steps,
            message="达到最大步数，仍未到达目标",
        )

    def execute(self, text: str, world: World) -> Result:
        """Parse and execute one command."""

        command = parse_command(text)
        if command.action == "stop":
            return Result(
                status="stopped",
                pose=self.pose,
                steps=0,
                message="收到停止指令，机器人保持原位",
            )
        if command.target is None:
            raise ValueError("移动指令缺少目标点")
        return self.move_to(command.target, world)
