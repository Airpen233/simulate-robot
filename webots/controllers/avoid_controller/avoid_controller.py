"""Stage 2 random-obstacle avoidance controller.

This adapter reads the eight e-puck proximity sensors and delegates every
avoidance decision to the pure ``logic.avoidance`` state machine. It never
uses Supervisor ground truth for control; Supervisor is only a verifier.
"""

from __future__ import annotations

import json
import math
import os
import sys
import traceback

from controller import Robot

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "robot_controller")))

from logic.avoidance import (  # noqa: E402
    AvoidAction,
    AvoidConfig,
    AvoidState,
    AvoidStateMachine,
    SensorSnapshot,
)
from logic.kinematics import Pose, advance_pose, angle_error, heading_to_target, wheel_velocities  # noqa: E402

TIME_STEP_MS = 32
WHEEL_RADIUS_M = 0.0200
# Effective wheelbase, measured rather than nominal. A motion probe drove six
# magnitudes (+45/+90/+180/+270/-90/-180 deg) and compared the Supervisor's true
# heading against the commanded angle: the robot consistently over-rotated by a
# factor of 1.02353 (residual 0.65 deg mean, 1.10 deg max). Since omega =
# dv * r / L, that factor means the real L is 0.058 / 1.02353 = 0.05667.
#
# The nominal e-puck value is 0.052 and was already known to be off; 0.058 was an
# earlier hand calibration. Neither matched, which is why the probe exists.
WHEEL_BASE_M = 0.05667
MAX_WHEEL_SPEED = 4.0
SLOW_WHEEL_SPEED = float(os.environ.get("SIMULATE_SLOW_SPEED", "3.0"))
BACKUP_WHEEL_SPEED = -3.0
SPIN_WHEEL_SPEED = 2.0

TARGET_X = float(os.environ.get("SIMULATE_TARGET_X", "1.0"))
TARGET_Y = float(os.environ.get("SIMULATE_TARGET_Y", "0.0"))
TIMEOUT_S = float(os.environ.get("SIMULATE_TIMEOUT", "24.0"))
SCENE = os.environ.get("SIMULATE_SCENE", "unknown")
SEED = os.environ.get("SIMULATE_SEED", "unknown")
SCENE_JSON = os.environ.get("SIMULATE_SCENE_JSON", "")

CFG = AvoidConfig(
    front_stop=float(os.environ.get("SIMULATE_FRONT_STOP", "120.0")),
    side_block=float(os.environ.get("SIMULATE_SIDE_BLOCK", "200.0")),
    side_margin=float(os.environ.get("SIMULATE_SIDE_MARGIN", "30.0")),
    rear_clear=float(os.environ.get("SIMULATE_REAR_CLEAR", "80.0")),
    turn_duration_s=float(os.environ.get("SIMULATE_TURN_S", "0.90")),
    move_duration_s=float(os.environ.get("SIMULATE_MOVE_S", "2.50")),
    backup_duration_s=float(os.environ.get("SIMULATE_BACKUP_S", "0.80")),
    max_avoid_attempts=int(os.environ.get("SIMULATE_MAX_AVOID", "8")),
    max_backup_attempts=int(os.environ.get("SIMULATE_MAX_BACKUP", "1")),
)

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "avoid_controller.log")

_original_print = print


def log(*args, **kwargs):
    _original_print(*args, **kwargs)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        _original_print(*args, file=handle, **kwargs)


print = log


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


def stop(left_motor, right_motor) -> None:
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)


def set_wheel_rad_s(left_motor, right_motor, left: float, right: float) -> None:
    limit = MAX_WHEEL_SPEED
    left_motor.setVelocity(max(-limit, min(limit, left)))
    right_motor.setVelocity(max(-limit, min(limit, right)))


def main() -> int:
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    left_motor = robot.getDevice("left wheel motor")
    right_motor = robot.getDevice("right wheel motor")
    left_sensor = robot.getDevice("left wheel sensor")
    right_sensor = robot.getDevice("right wheel sensor")
    ps = [robot.getDevice(f"ps{i}") for i in range(8)]

    required = {
        "left wheel motor": left_motor,
        "right wheel motor": right_motor,
        "left wheel sensor": left_sensor,
        "right wheel sensor": right_sensor,
        **{f"ps{i}": ps[i] for i in range(8)},
    }
    missing = [name for name, device in required.items() if device is None]
    if missing:
        raise RuntimeError(f"missing devices: {missing}")

    for device in (left_sensor, right_sensor, *ps):
        device.enable(timestep)
    for motor in (left_motor, right_motor):
        motor.setPosition(float("inf"))
        motor.setVelocity(0.0)

    log(f"MODE: avoid_v2 scene={SCENE} seed={SEED} target=({TARGET_X},{TARGET_Y})")
    log(f"CONFIG: {CFG}")
    log(
        "SENSOR_MAP: front=max(ps0,ps7) left=max(ps5,ps6) "
        "right=max(ps1,ps2) rear=max(ps3,ps4); rear has no centre sensor"
    )
    if SCENE_JSON and os.path.exists(SCENE_JSON):
        try:
            with open(SCENE_JSON, "r", encoding="utf-8") as handle:
                scene = json.load(handle)
            log(f"SCENE {json.dumps(scene, ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001
            log(f"SCENE_READ_ERROR {exc!r}")
    else:
        log(f"SCENE_JSON_MISSING {SCENE_JSON!r}")

    odometry = Odometry()
    machine = AvoidStateMachine(target=(TARGET_X, TARGET_Y), config=CFG)
    last_state: AvoidState | None = None
    last_action: AvoidAction | None = None
    last_trace = -1.0
    steps = 0

    def snapshot() -> SensorSnapshot:
        values = [float(device.getValue()) for device in ps]
        return SensorSnapshot(*values)

    def spin(error: float, scale: float = SPIN_WHEEL_SPEED) -> None:
        angular = scale if error > 0.0 else -scale
        left, right = wheel_velocities(0.0, angular, WHEEL_RADIUS_M, WHEEL_BASE_M)
        set_wheel_rad_s(left_motor, right_motor, left, right)

    def apply(action: AvoidAction, error: float) -> None:
        if action is AvoidAction.DRIVE:
            if abs(error) > CFG.heading_tolerance_rad:
                spin(error)
            else:
                set_wheel_rad_s(left_motor, right_motor, MAX_WHEEL_SPEED, MAX_WHEEL_SPEED)
        elif action is AvoidAction.SPIN_TO_TARGET:
            if abs(error) <= CFG.heading_tolerance_rad:
                stop(left_motor, right_motor)
            else:
                spin(error)
        elif action is AvoidAction.SPIN_LEFT:
            left, right = wheel_velocities(0.0, SPIN_WHEEL_SPEED, WHEEL_RADIUS_M, WHEEL_BASE_M)
            set_wheel_rad_s(left_motor, right_motor, left, right)
        elif action is AvoidAction.SPIN_RIGHT:
            left, right = wheel_velocities(0.0, -SPIN_WHEEL_SPEED, WHEEL_RADIUS_M, WHEEL_BASE_M)
            set_wheel_rad_s(left_motor, right_motor, left, right)
        elif action is AvoidAction.FORWARD_SLOW:
            set_wheel_rad_s(left_motor, right_motor, SLOW_WHEEL_SPEED, SLOW_WHEEL_SPEED)
        elif action is AvoidAction.BACKWARD_SLOW:
            set_wheel_rad_s(left_motor, right_motor, BACKUP_WHEEL_SPEED, BACKUP_WHEEL_SPEED)
        else:
            stop(left_motor, right_motor)

    def log_decision(decision, now, snapshot_value, pose, distance, error) -> None:
        log(
            f"DECISION t={now:.2f} state={decision.state.value} action={decision.action.value} "
            f"reason={decision.reason!r} ps={snapshot_value.raw()} "
            f"front={decision.front:.1f} left={decision.left:.1f} "
            f"right={decision.right:.1f} rear={decision.rear:.1f} "
            f"pose=({pose.x:.3f},{pose.y:.3f},{pose.heading_rad:.3f}) "
            f"dist={distance:.3f} err={error:.3f} "
            f"attempts={decision.avoid_attempts} turns={decision.turn_count} "
            f"backups={decision.backup_count} recovers={decision.recover_count} "
            f"last_failed={decision.last_failed.value if decision.last_failed else 'none'}"
        )

    try:
        while robot.step(timestep) != -1:
            steps += 1
            now = robot.getTime()
            pose = odometry.update(left_sensor.getValue(), right_sensor.getValue())
            snap = snapshot()
            distance = math.hypot(TARGET_X - pose.x, TARGET_Y - pose.y)
            desired = heading_to_target(pose.x, pose.y, TARGET_X, TARGET_Y)
            error = angle_error(desired, pose.heading_rad)

            # Tell the state machine whether the robot is actually travelling.
            # Odometry alone cannot distinguish "driving" from "wheels spinning
            # against a box", and that ambiguity is what produced the
            # random_seed_4 false arrival 45 cm from the target.
            commanded_forward = last_action in (
                AvoidAction.DRIVE,
                AvoidAction.FORWARD_SLOW,
                AvoidAction.BACKWARD_SLOW,
            )

            if now > TIMEOUT_S and not machine.terminal:
                decision = machine.force_terminal(
                    AvoidState.TIMEOUT, f"wall clock {now:.2f} > {TIMEOUT_S:.2f}"
                )
            else:
                decision = machine.tick(
                    now,
                    snap,
                    distance,
                    error,
                    travelled_m=odometry.distance_m,
                    commanded_forward=commanded_forward,
                )

            if decision.state is not last_state or decision.action is not last_action:
                log_decision(decision, now, snap, pose, distance, error)
                last_state = decision.state
                last_action = decision.action

            if now - last_trace >= 0.5:
                last_trace = now
                log(
                    f"TRACE t={now:.2f} state={decision.state.value} "
                    f"pose=({pose.x:.3f},{pose.y:.3f},{pose.heading_rad:.3f}) "
                    f"dist={distance:.3f} err={error:.3f} front={snap.front():.1f} "
                    f"left={snap.left():.1f} right={snap.right():.1f} rear={snap.rear():.1f}"
                )

            if decision.terminal:
                stop(left_motor, right_motor)
                log(
                    f"SUMMARY state={decision.state.value} attempts={decision.avoid_attempts} "
                    f"turns={decision.turn_count} backups={decision.backup_count} "
                    f"recovers={decision.recover_count} steps={steps}"
                )
                log(
                    f"RESULT: {decision.state.value.lower()} target=({TARGET_X},{TARGET_Y}) "
                    f"pose_est=({pose.x:.3f},{pose.y:.3f},{pose.heading_rad:.3f}) "
                    f"distance={distance:.3f} reason={decision.reason!r}"
                )
                return 0

            apply(decision.action, error)

        stop(left_motor, right_motor)
        log("RESULT: error simulation ended before a terminal state")
        return 1
    except Exception as exc:  # noqa: BLE001
        stop(left_motor, right_motor)
        log(f"RESULT: error {exc!r}")
        log(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
