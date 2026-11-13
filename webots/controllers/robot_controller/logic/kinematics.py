"""Differential-drive kinematics and planar pose helpers.

Conventions used by this pure-Python layer:

- The robot moves in a 2D plane (x, y).
- Heading is measured counter-clockwise from the +X axis, in radians.
- Positive wheel speeds drive the robot forward.
- Positive angular velocity means counter-clockwise rotation.

The Webots adapter is responsible for mapping this mathematical convention
to the e-puck/Webots yaw convention after measuring the real model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RobotVelocity:
    """Robot body velocity produced by the two wheel speeds."""

    linear_m_s: float
    angular_rad_s: float


@dataclass(frozen=True)
class Pose:
    """Planar pose: world position plus heading in radians."""

    x: float
    y: float
    heading_rad: float


def _validate_geometry(wheel_radius_m: float, wheel_base_m: float) -> None:
    if wheel_radius_m <= 0.0:
        raise ValueError("wheel_radius_m must be positive")
    if wheel_base_m <= 0.0:
        raise ValueError("wheel_base_m must be positive")


def differential_drive(
    left_rad_s: float,
    right_rad_s: float,
    wheel_radius_m: float,
    wheel_base_m: float,
) -> RobotVelocity:
    """Convert left/right wheel angular speeds to body linear/angular speed.

    v = r * (wR + wL) / 2
    w = r * (wR - wL) / L

    Equal speeds give pure translation. Opposite equal speeds give pure
    rotation with zero linear speed.
    """

    _validate_geometry(wheel_radius_m, wheel_base_m)
    linear = wheel_radius_m * (right_rad_s + left_rad_s) / 2.0
    angular = wheel_radius_m * (right_rad_s - left_rad_s) / wheel_base_m
    return RobotVelocity(linear_m_s=linear, angular_rad_s=angular)


def wheel_velocities(
    linear_m_s: float,
    angular_rad_s: float,
    wheel_radius_m: float,
    wheel_base_m: float,
) -> tuple[float, float]:
    """Inverse kinematics: desired body velocity -> (left, right) wheel speeds."""

    _validate_geometry(wheel_radius_m, wheel_base_m)
    half_track = wheel_base_m / 2.0
    left = (linear_m_s - angular_rad_s * half_track) / wheel_radius_m
    right = (linear_m_s + angular_rad_s * half_track) / wheel_radius_m
    return left, right


def normalize_angle(angle_rad: float) -> float:
    """Wrap an angle to [-pi, pi] using the shortest signed direction."""

    return math.atan2(math.sin(angle_rad), math.cos(angle_rad))


def angle_error(target_rad: float, current_rad: float) -> float:
    """Signed shortest rotation from current heading to target heading."""

    return normalize_angle(target_rad - current_rad)


def heading_to_target(
    current_x: float,
    current_y: float,
    target_x: float,
    target_y: float,
) -> float:
    """World heading (CCW from +X) pointing from current position to target."""

    return math.atan2(target_y - current_y, target_x - current_x)


def advance_pose(
    pose: Pose,
    left_delta_m: float,
    right_delta_m: float,
    wheel_base_m: float,
) -> Pose:
    """Integrate one wheel-odometry sample into a new planar pose.

    The midpoint heading is used for the arc, which is the standard
    second-order approximation for a short differential-drive step.
    """

    if wheel_base_m <= 0.0:
        raise ValueError("wheel_base_m must be positive")

    distance = (left_delta_m + right_delta_m) / 2.0
    delta_heading = (right_delta_m - left_delta_m) / wheel_base_m
    mid_heading = pose.heading_rad + delta_heading / 2.0
    return Pose(
        x=pose.x + distance * math.cos(mid_heading),
        y=pose.y + distance * math.sin(mid_heading),
        heading_rad=normalize_angle(pose.heading_rad + delta_heading),
    )


def pose_distance(first: Pose, second: Pose) -> float:
    """Euclidean distance between the positions of two poses."""

    return math.hypot(second.x - first.x, second.y - first.y)
