"""Webots adapter for the Simulate Robot logic layer.

The pure command/status logic lives in logic/robot.py and is synced from
the WSL project. This file only touches Webots devices and the simulation
loop; it does not duplicate the command parser.
"""

import math
import os
import sys
import traceback

from controller import Robot

# Ensure the controller directory is importable even if Webots starts from
# a different working directory.
sys.path.insert(0, os.path.dirname(__file__))
from logic.robot import parse_command  # noqa: E402

TIME_STEP_MS = 32
WHEEL_RADIUS_M = 0.0205
MAX_WHEEL_SPEED = 4.0
TARGET_COMMAND = os.environ.get("SIMULATE_ROBOT_COMMAND", "go to 0, 0.8")  # 2D y maps to Webots +X (the e-puck's forward axis)
DISTANCE_TOLERANCE_M = 0.03
TIMEOUT_S = float(os.environ.get("SIMULATE_ROBOT_TIMEOUT", "20.0"))

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "robot_controller.log")

_original_print = print


def log(*args, **kwargs):
    _original_print(*args, **kwargs)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        _original_print(*args, file=handle, **kwargs)


print = log


# Calibrated in the 3x3 m arena: baseline is about 65-70; ps7 rises above
# 120 roughly 15 mm before the robot touches the 0.12 m obstacle box.
PS_STOP_THRESHOLD = 120.0


def stop(left_motor, right_motor):
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)


def main():
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    print(f"PYTHON: {sys.version.split()[0]} {sys.executable}", flush=True)
    print("DEVICES:", flush=True)
    for index in range(robot.getNumberOfDevices()):
        device = robot.getDeviceByIndex(index)
        print(f"  {index}: {device.getName()}", flush=True)

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

    command = parse_command(TARGET_COMMAND)
    if command.action == "stop":
        stop(left_motor, right_motor)
        print("RESULT: stopped", flush=True)
        return 0

    if command.target is None:
        raise ValueError("move command has no target")
    if abs(command.target.x) > 1e-9 or command.target.y <= 0:
        raise ValueError(
            "this first 3D demo only supports a straight-ahead target "
            f"(0, positive), got {command.target}"
        )

    target_distance = float(command.target.y)
    traveled = 0.0
    previous_left = left_sensor.getValue()
    previous_right = right_sensor.getValue()
    steps = 0

    print(
        f"TARGET: {command.target} -> forward {target_distance:.2f} m",
        flush=True,
    )

    while robot.step(timestep) != -1:
        steps += 1

        left_value = left_sensor.getValue()
        right_value = right_sensor.getValue()
        if math.isfinite(left_value) and math.isfinite(previous_left):
            traveled += abs(left_value - previous_left) * WHEEL_RADIUS_M * 0.5
        if math.isfinite(right_value) and math.isfinite(previous_right):
            traveled += abs(right_value - previous_right) * WHEEL_RADIUS_M * 0.5
        previous_left = left_value
        previous_right = right_value

        ps0_value = ps0.getValue()
        ps7_value = ps7.getValue()
        front_value = max(ps0_value, ps7_value)

        if steps % 15 == 0:
            print(
                f"STEP t={robot.getTime():.2f}s "
                f"ps0={ps0_value:.1f} ps7={ps7_value:.1f} "
                f"traveled={traveled:.3f}m",
                flush=True,
            )

        if front_value > PS_STOP_THRESHOLD:
            stop(left_motor, right_motor)
            print(
                f"RESULT: blocked front={front_value:.1f} "
                f"traveled={traveled:.3f}m",
                flush=True,
            )
            return 0

        if traveled >= target_distance - DISTANCE_TOLERANCE_M:
            stop(left_motor, right_motor)
            print(f"RESULT: reached traveled={traveled:.3f}m", flush=True)
            return 0

        if robot.getTime() > TIMEOUT_S:
            stop(left_motor, right_motor)
            print(
                f"RESULT: timeout traveled={traveled:.3f}m "
                f"front={front_value:.1f}",
                flush=True,
            )
            return 0

        left_motor.setVelocity(MAX_WHEEL_SPEED)
        right_motor.setVelocity(MAX_WHEEL_SPEED)

    print("RESULT: error simulation ended before a terminal state", flush=True)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESULT: error {exc!r}", flush=True)
        traceback.print_exc()
        raise
