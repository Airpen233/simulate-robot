"""Stage 2 motion controller: differential drive, odometry and waypoint navigation.

Modes are selected with SIMULATE_MODE so the same controller can be reused for
calibration runs and the final demos:

- drive: open-loop wheel speeds for a fixed duration (calibration)
- forward: closed-loop straight distance
- turn: closed-loop in-place rotation to a signed angle (positive = left/CCW)
- navigate: waypoint navigation in the odometry frame
- avoid: waypoint navigation with a minimal stop-turn-resume rule

The pure kinematics live in logic/kinematics.py, synced from the Linux
project. This file only handles Webots devices and the step loop.
"""

from __future__ import annotations

import math
import os
import sys
import traceback

from controller import Robot

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "robot_controller")))

from logic.kinematics import (  # noqa: E402
    Pose,
    advance_pose,
    angle_error,
    heading_to_target,
    wheel_velocities,
)

TIME_STEP_MS = 32
# effective values calibrated against Supervisor ground truth: straight-line
# odometry was 2.3% high, and in-place rotation was about 10% high.
WHEEL_RADIUS_M = 0.0200
WHEEL_BASE_M = 0.058
MAX_WHEEL_SPEED = 4.0
SPIN_WHEEL_SPEED = 2.0
POSITION_TOLERANCE_M = 0.02
HEADING_TOLERANCE_RAD = math.radians(5.0)
PS_STOP_THRESHOLD = 120.0
TIMEOUT_S = float(os.environ.get("SIMULATE_TIMEOUT", "22.0"))

MODE = os.environ.get("SIMULATE_MODE", "navigate")
TARGET_X = float(os.environ.get("SIMULATE_TARGET_X", "0.8"))
TARGET_Y = float(os.environ.get("SIMULATE_TARGET_Y", "0.8"))
TARGET_ANGLE_DEG = float(os.environ.get("SIMULATE_ANGLE_DEG", "90"))
TARGET_DISTANCE_M = float(os.environ.get("SIMULATE_DISTANCE", "0.5"))
DRIVE_LEFT = float(os.environ.get("SIMULATE_LEFT", "2.0"))
DRIVE_RIGHT = float(os.environ.get("SIMULATE_RIGHT", "2.0"))
DRIVE_DURATION_S = float(os.environ.get("SIMULATE_DURATION", "2.0"))

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "motion_controller.log")

_original_print = print


def log(*args, **kwargs):
    _original_print(*args, **kwargs)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        _original_print(*args, file=handle, **kwargs)


print = log


def stop(left_motor, right_motor) -> None:
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)


def set_wheel_rad_s(left_motor, right_motor, left: float, right: float) -> None:
    limit = MAX_WHEEL_SPEED
    left_motor.setVelocity(max(-limit, min(limit, left)))
    right_motor.setVelocity(max(-limit, min(limit, right)))


class Odometry:
    """Relative planar pose from signed wheel-encoder deltas."""

    def __init__(self) -> None:
        self.pose = Pose(0.0, 0.0, 0.0)
        self.previous_left: float | None = None
        self.previous_right: float | None = None
        self.distance_m = 0.0

    def update(self, left_value: float, right_value: float) -> Pose:
        if not (math.isfinite(left_value) and math.isfinite(right_value)):
            return self.pose
        if self.previous_left is None or self.previous_right is None:
            self.previous_left = left_value
            self.previous_right = right_value
            return self.pose

        left_delta = (left_value - self.previous_left) * WHEEL_RADIUS_M
        right_delta = (right_value - self.previous_right) * WHEEL_RADIUS_M
        self.previous_left = left_value
        self.previous_right = right_value
        self.distance_m += (left_delta + right_delta) / 2.0
        self.pose = advance_pose(self.pose, left_delta, right_delta, WHEEL_BASE_M)
        return self.pose


def main() -> int:
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    left_motor = robot.getDevice("left wheel motor")
    right_motor = robot.getDevice("right wheel motor")
    left_sensor = robot.getDevice("left wheel sensor")
    right_sensor = robot.getDevice("right wheel sensor")
    ps0 = robot.getDevice("ps0")
    ps7 = robot.getDevice("ps7")

    required = {
        "left wheel motor": left_motor,
        "right wheel motor": right_motor,
        "left wheel sensor": left_sensor,
        "right wheel sensor": right_sensor,
        "ps0": ps0,
        "ps7": ps7,
    }
    missing = [name for name, device in required.items() if device is None]
    if missing:
        raise RuntimeError(f"missing devices: {missing}")

    for device in (left_sensor, right_sensor, ps0, ps7):
        device.enable(timestep)
    for motor in (left_motor, right_motor):
        motor.setPosition(float("inf"))
        motor.setVelocity(0.0)

    odometry = Odometry()
    steps = 0
    print(f"MODE: {MODE} python={sys.version.split()[0]}")
    print(f"GEOMETRY: r={WHEEL_RADIUS_M} L={WHEEL_BASE_M}")
    print(f"PARAMS: target=({TARGET_X},{TARGET_Y}) angle={TARGET_ANGLE_DEG} distance={TARGET_DISTANCE_M}")

    def update_odometry() -> Pose:
        return odometry.update(left_sensor.getValue(), right_sensor.getValue())

    def front_value() -> float:
        return max(ps0.getValue(), ps7.getValue())

    if MODE == "drive":
        set_wheel_rad_s(left_motor, right_motor, DRIVE_LEFT, DRIVE_RIGHT)
        while robot.step(timestep) != -1:
            steps += 1
            pose = update_odometry()
            if steps % 15 == 0:
                print(
                    f"POSE t={robot.getTime():.2f}s left={left_sensor.getValue():.3f} "
                    f"right={right_sensor.getValue():.3f} "
                    f"x={pose.x:.3f} y={pose.y:.3f} h={pose.heading_rad:.3f}",
                    flush=True,
                )
            if robot.getTime() >= DRIVE_DURATION_S:
                stop(left_motor, right_motor)
                print(
                    f"RESULT: drive left={DRIVE_LEFT} right={DRIVE_RIGHT} "
                    f"x={pose.x:.3f} y={pose.y:.3f} h={pose.heading_rad:.3f} "
                    f"distance={odometry.distance_m:.3f}",
                    flush=True,
                )
                return 0
        return 1

    if MODE == "forward":
        while robot.step(timestep) != -1:
            steps += 1
            pose = update_odometry()
            if steps % 15 == 0:
                print(
                    f"POSE t={robot.getTime():.2f}s x={pose.x:.3f} "
                    f"y={pose.y:.3f} h={pose.heading_rad:.3f} "
                    f"front={front_value():.1f}",
                    flush=True,
                )
            if front_value() > PS_STOP_THRESHOLD:
                stop(left_motor, right_motor)
                print(f"RESULT: blocked front={front_value():.1f} distance={odometry.distance_m:.3f}", flush=True)
                return 0
            if abs(odometry.distance_m) >= TARGET_DISTANCE_M - POSITION_TOLERANCE_M:
                stop(left_motor, right_motor)
                print(
                    f"RESULT: reached distance={odometry.distance_m:.3f} "
                    f"x={pose.x:.3f} y={pose.y:.3f} h={pose.heading_rad:.3f}",
                    flush=True,
                )
                return 0
            if robot.getTime() > TIMEOUT_S:
                stop(left_motor, right_motor)
                print(f"RESULT: timeout distance={odometry.distance_m:.3f}", flush=True)
                return 0
            set_wheel_rad_s(left_motor, right_motor, MAX_WHEEL_SPEED, MAX_WHEEL_SPEED)
        return 1

    if MODE == "turn":
        target_heading = math.radians(TARGET_ANGLE_DEG)
        while robot.step(timestep) != -1:
            steps += 1
            pose = update_odometry()
            error = angle_error(target_heading, pose.heading_rad)
            if steps % 15 == 0:
                print(
                    f"TURN t={robot.getTime():.2f}s h={pose.heading_rad:.3f} "
                    f"target={target_heading:.3f} error={error:.3f}",
                    flush=True,
                )
            if abs(error) <= HEADING_TOLERANCE_RAD:
                stop(left_motor, right_motor)
                print(
                    f"RESULT: turned target={target_heading:.3f} "
                    f"actual={pose.heading_rad:.3f} error={error:.3f}",
                    flush=True,
                )
                return 0
            if robot.getTime() > TIMEOUT_S:
                stop(left_motor, right_motor)
                print(f"RESULT: timeout turn actual={pose.heading_rad:.3f} error={error:.3f}", flush=True)
                return 0
            angular = SPIN_WHEEL_SPEED if error > 0 else -SPIN_WHEEL_SPEED
            left, right = wheel_velocities(0.0, angular, WHEEL_RADIUS_M, WHEEL_BASE_M)
            set_wheel_rad_s(left_motor, right_motor, left, right)
        return 1

    # navigate / avoid
    target = (TARGET_X, TARGET_Y)
    avoid_active = MODE == "avoid"
    avoid_phase = "drive"
    avoid_started = 0.0

    while robot.step(timestep) != -1:
        steps += 1
        pose = update_odometry()
        distance = math.hypot(target[0] - pose.x, target[1] - pose.y)
        desired = heading_to_target(pose.x, pose.y, target[0], target[1])
        error = angle_error(desired, pose.heading_rad)
        front = front_value()

        if steps % 15 == 0:
            print(
                f"NAV t={robot.getTime():.2f}s pose=({pose.x:.3f},{pose.y:.3f},{pose.heading_rad:.3f}) "
                f"dist={distance:.3f} desired={desired:.3f} error={error:.3f} front={front:.1f}",
                flush=True,
            )

        if distance <= POSITION_TOLERANCE_M:
            stop(left_motor, right_motor)
            print(
                f"RESULT: reached target=({target[0]},{target[1]}) "
                f"pose=({pose.x:.3f},{pose.y:.3f},{pose.heading_rad:.3f}) "
                f"distance={distance:.3f}",
                flush=True,
            )
            return 0

        if robot.getTime() > TIMEOUT_S:
            stop(left_motor, right_motor)
            print(
                f"RESULT: timeout pose=({pose.x:.3f},{pose.y:.3f},{pose.heading_rad:.3f}) "
                f"distance={distance:.3f}",
                flush=True,
            )
            return 0

        if avoid_active:
            if avoid_phase == "turn":
                if robot.getTime() - avoid_started >= 1.0:
                    avoid_phase = "forward"
                    avoid_started = robot.getTime()
                else:
                    left, right = wheel_velocities(0.0, SPIN_WHEEL_SPEED, WHEEL_RADIUS_M, WHEEL_BASE_M)
                    set_wheel_rad_s(left_motor, right_motor, left, right)
                    continue
            elif avoid_phase == "forward":
                if robot.getTime() - avoid_started >= 1.2:
                    avoid_phase = "drive"
                else:
                    set_wheel_rad_s(left_motor, right_motor, MAX_WHEEL_SPEED, MAX_WHEEL_SPEED)
                    continue
            elif front > PS_STOP_THRESHOLD and robot.getTime() - avoid_started > 1.5:
                stop(left_motor, right_motor)
                avoid_phase = "turn"
                avoid_started = robot.getTime()
                print(f"AVOID: obstacle front={front:.1f}", flush=True)
                continue

        if front > PS_STOP_THRESHOLD:
            stop(left_motor, right_motor)
            print(f"RESULT: blocked front={front:.1f} distance={distance:.3f}", flush=True)
            return 0

        if abs(error) > HEADING_TOLERANCE_RAD:
            angular = SPIN_WHEEL_SPEED if error > 0 else -SPIN_WHEEL_SPEED
            left, right = wheel_velocities(0.0, angular, WHEEL_RADIUS_M, WHEEL_BASE_M)
            set_wheel_rad_s(left_motor, right_motor, left, right)
        else:
            set_wheel_rad_s(left_motor, right_motor, MAX_WHEEL_SPEED, MAX_WHEEL_SPEED)

    print("RESULT: error simulation ended before a terminal state", flush=True)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"RESULT: error {exc!r}", flush=True)
        traceback.print_exc()
        raise
