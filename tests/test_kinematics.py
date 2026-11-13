from __future__ import annotations

import math
import unittest

from src.kinematics import (
    Pose,
    RobotVelocity,
    advance_pose,
    angle_error,
    differential_drive,
    heading_to_target,
    normalize_angle,
    pose_distance,
    wheel_velocities,
)

WHEEL_RADIUS = 0.0205
WHEEL_BASE = 0.052


class DifferentialDriveTests(unittest.TestCase):
    def test_equal_wheel_speeds_drive_straight(self) -> None:
        velocity = differential_drive(2.0, 2.0, WHEEL_RADIUS, WHEEL_BASE)
        self.assertIsInstance(velocity, RobotVelocity)
        self.assertAlmostEqual(velocity.linear_m_s, 0.041)
        self.assertAlmostEqual(velocity.angular_rad_s, 0.0)

    def test_right_wheel_faster_gives_positive_angular_velocity(self) -> None:
        velocity = differential_drive(1.0, 3.0, WHEEL_RADIUS, WHEEL_BASE)
        self.assertAlmostEqual(velocity.linear_m_s, 0.041)
        self.assertGreater(velocity.angular_rad_s, 0.0)
        self.assertAlmostEqual(
            velocity.angular_rad_s,
            WHEEL_RADIUS * (3.0 - 1.0) / WHEEL_BASE,
        )

    def test_left_wheel_faster_gives_negative_angular_velocity(self) -> None:
        velocity = differential_drive(3.0, 1.0, WHEEL_RADIUS, WHEEL_BASE)
        self.assertLess(velocity.angular_rad_s, 0.0)

    def test_opposite_wheels_spin_in_place(self) -> None:
        velocity = differential_drive(-2.0, 2.0, WHEEL_RADIUS, WHEEL_BASE)
        self.assertAlmostEqual(velocity.linear_m_s, 0.0)
        self.assertGreater(velocity.angular_rad_s, 0.0)

    def test_wheel_velocities_invert_straight_motion(self) -> None:
        left, right = wheel_velocities(0.082, 0.0, WHEEL_RADIUS, WHEEL_BASE)
        self.assertAlmostEqual(left, 4.0)
        self.assertAlmostEqual(right, 4.0)

    def test_wheel_velocities_invert_spin(self) -> None:
        left, right = wheel_velocities(0.0, 0.8, WHEEL_RADIUS, WHEEL_BASE)
        self.assertAlmostEqual(left, -0.8 * WHEEL_BASE / 2.0 / WHEEL_RADIUS)
        self.assertAlmostEqual(right, 0.8 * WHEEL_BASE / 2.0 / WHEEL_RADIUS)
        self.assertAlmostEqual(left, -right)

    def test_invalid_geometry_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            differential_drive(1.0, 1.0, 0.0, WHEEL_BASE)
        with self.assertRaises(ValueError):
            differential_drive(1.0, 1.0, WHEEL_RADIUS, 0.0)


class AngleTests(unittest.TestCase):
    def test_normalize_angle_keeps_common_angles(self) -> None:
        self.assertAlmostEqual(normalize_angle(0.0), 0.0)
        self.assertAlmostEqual(normalize_angle(math.pi / 2), math.pi / 2)
        self.assertAlmostEqual(normalize_angle(math.pi), math.pi)
        self.assertAlmostEqual(normalize_angle(-math.pi), -math.pi)

    def test_normalize_angle_wraps_full_turns(self) -> None:
        self.assertAlmostEqual(normalize_angle(3 * math.pi), math.pi)
        self.assertAlmostEqual(normalize_angle(-3 * math.pi), -math.pi)
        self.assertAlmostEqual(normalize_angle(2 * math.pi + 0.5), 0.5)

    def test_angle_error_takes_shortest_path(self) -> None:
        self.assertAlmostEqual(angle_error(math.radians(10), math.radians(350)), math.radians(20))
        self.assertAlmostEqual(angle_error(math.radians(-170), math.radians(170)), math.radians(20))
        self.assertAlmostEqual(angle_error(0.0, math.radians(90)), math.radians(-90))

    def test_heading_to_target_uses_xy_plane(self) -> None:
        self.assertAlmostEqual(heading_to_target(0.0, 0.0, 1.0, 0.0), 0.0)
        self.assertAlmostEqual(heading_to_target(0.0, 0.0, 0.0, 1.0), math.pi / 2)
        self.assertAlmostEqual(heading_to_target(0.0, 0.0, -1.0, 0.0), math.pi)
        self.assertAlmostEqual(heading_to_target(1.0, 1.0, 1.0, 0.0), -math.pi / 2)


class PoseTests(unittest.TestCase):
    def test_straight_advance_updates_x_only(self) -> None:
        pose = advance_pose(Pose(0.0, 0.0, 0.0), 0.1, 0.1, WHEEL_BASE)
        self.assertAlmostEqual(pose.x, 0.1)
        self.assertAlmostEqual(pose.y, 0.0)
        self.assertAlmostEqual(pose.heading_rad, 0.0)

    def test_spin_in_place_updates_heading_only(self) -> None:
        pose = advance_pose(Pose(0.5, 0.5, 0.0), -0.01, 0.01, WHEEL_BASE)
        self.assertAlmostEqual(pose.x, 0.5)
        self.assertAlmostEqual(pose.y, 0.5)
        self.assertAlmostEqual(pose.heading_rad, 0.02 / WHEEL_BASE)

    def test_arc_uses_midpoint_heading(self) -> None:
        pose = advance_pose(Pose(0.0, 0.0, 0.0), 0.1, 0.2, 0.1)
        self.assertAlmostEqual(pose.heading_rad, 1.0)
        self.assertAlmostEqual(pose.x, 0.15 * math.cos(0.5))
        self.assertAlmostEqual(pose.y, 0.15 * math.sin(0.5))

    def test_pose_distance(self) -> None:
        self.assertAlmostEqual(pose_distance(Pose(0.0, 0.0, 0.0), Pose(3.0, 4.0, 1.0)), 5.0)


if __name__ == "__main__":
    unittest.main()
