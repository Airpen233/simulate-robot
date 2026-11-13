from __future__ import annotations

import unittest

from src.robot import Point, Robot, World, parse_command


class ParseCommandTests(unittest.TestCase):
    def test_english_move_command(self) -> None:
        command = parse_command("go to 3, 4")
        self.assertEqual(command.action, "move")
        self.assertEqual(command.target, Point(3.0, 4.0))

    def test_chinese_move_command(self) -> None:
        command = parse_command("移动到 3, 4")
        self.assertEqual(command.action, "move")
        self.assertEqual(command.target, Point(3.0, 4.0))

    def test_stop_commands(self) -> None:
        self.assertEqual(parse_command("stop").action, "stop")
        self.assertEqual(parse_command("停止").action, "stop")

    def test_invalid_command(self) -> None:
        with self.assertRaises(ValueError):
            parse_command("fly to the moon")


class RobotTests(unittest.TestCase):
    def test_reaches_target(self) -> None:
        robot = Robot(pose=Point(0.0, 0.0), step_size=1.0)
        result = robot.execute("go to 3, 4", World())
        self.assertEqual(result.status, "reached")
        self.assertAlmostEqual(robot.pose.x, 3.0)
        self.assertAlmostEqual(robot.pose.y, 4.0)
        self.assertGreater(result.steps, 0)

    def test_stops_before_obstacle(self) -> None:
        world = World(obstacles=frozenset({Point(2.0, 0.0)}))
        robot = Robot(pose=Point(0.0, 0.0), step_size=1.0)
        result = robot.execute("go to 4, 0", world)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(robot.pose, Point(1.0, 0.0))
        self.assertNotEqual(robot.pose, Point(2.0, 0.0))

    def test_stop_keeps_position(self) -> None:
        robot = Robot(pose=Point(1.0, 2.0))
        result = robot.execute("停止", World())
        self.assertEqual(result.status, "stopped")
        self.assertEqual(robot.pose, Point(1.0, 2.0))
        self.assertEqual(result.steps, 0)


if __name__ == "__main__":
    unittest.main()
