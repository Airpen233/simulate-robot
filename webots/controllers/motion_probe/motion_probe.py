"""Measure how far the robot actually moves when told to move.

Why this exists
---------------
Every motion in this project is open-loop: the controller sets a wheel speed, waits
a fixed number of seconds, and *assumes* the robot travelled a set distance or
angle. Nothing has ever verified that assumption.

That matters because the failure attribution depends on it. The narrow-gap scenes
leave 1.6-2.6 cm of margin while the target-stop error is 1.7-2.9 cm; without a
measured baseline we cannot say whether the gap failures are a perception problem
or a motion-accuracy problem. Tuning a PID before measuring would be guessing.

Synchronisation — the part that went wrong first
------------------------------------------------
The Supervisor must sample the pose at the exact start and end of each move, or the
measured angle belongs to the wrong phase.

The first attempt had the Supervisor infer boundaries from "the robot stopped
moving". That is fragile: a slow straight segment looks stationary, and the
mis-paired samples produced a reported -266 deg error for a 90 deg turn — a
nonsense number that nearly sent the whole investigation down the wrong path.

Webots documents a purpose-built channel for this: the `customData` field of a Robot
node "may also be used as a convenience for communicating between a robot and a
supervisor without implementing a Receiver/Emitter system" (reference/robot.md). So
the probe stamps a token at every boundary and the Supervisor samples when the token
changes. No guessing, no timing assumptions.

Token format: ``<label>:<begin|end>``; ``idle`` means no boundary is pending.

Output goes to files because print is not reliably captured in --batch mode.
"""

from __future__ import annotations

import math
from pathlib import Path

from controller import Robot  # noqa: F401  (provided by Webots at runtime)

LOG_PATH = Path(__file__).resolve().parent / "motion_probe.log"

WHEEL_RADIUS_M = 0.0200
# Kept in step with avoid_controller.py. This probe is what produced the number in
# the first place; re-running it with the corrected value should now show a scale
# factor near 1.0 and errors near zero, which is how the correction gets verified
# rather than assumed.
WHEEL_BASE_M = 0.05667
SPIN_WHEEL_SPEED = 2.0
STRAIGHT_WHEEL_SPEED = 3.0

# Derived the same way the avoidance controller derives them.
SPIN_RATE_RAD_S = (SPIN_WHEEL_SPEED - (-SPIN_WHEEL_SPEED)) * WHEEL_RADIUS_M / WHEEL_BASE_M
STRAIGHT_RATE_M_S = STRAIGHT_WHEEL_SPEED * WHEEL_RADIUS_M


def log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def main() -> int:
    LOG_PATH.unlink(missing_ok=True)
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    left = robot.getDevice("left wheel motor")
    right = robot.getDevice("right wheel motor")
    for motor in (left, right):
        motor.setPosition(float("inf"))
        motor.setVelocity(0.0)

    log("MOTION_PROBE_START")
    log(
        f"GEOMETRY wheel_radius={WHEEL_RADIUS_M} wheel_base={WHEEL_BASE_M} "
        f"spin_rate_rad_s={SPIN_RATE_RAD_S:.4f} straight_rate_m_s={STRAIGHT_RATE_M_S:.4f}"
    )

    # (label, kind, magnitude) — kind is 'spin' (radians) or 'straight' (metres)
    #
    # Angles are chosen to expose the wheelbase error from several directions: a
    # single 90 deg sample cannot tell a proportional wheelbase error from a fixed
    # starting-angle offset. Four magnitudes, two of them negative, and a 270 deg
    # turn (which crosses the +-180 wrap) separate those cases.
    script = [
        ("spin_45", "spin", math.radians(45.0)),
        ("spin_90", "spin", math.radians(90.0)),
        ("spin_180", "spin", math.radians(180.0)),
        ("spin_270", "spin", math.radians(270.0)),
        ("spin_n90", "spin", math.radians(-90.0)),
        ("spin_n180", "spin", math.radians(-180.0)),
        ("straight_050", "straight", 0.50),
        ("straight_020", "straight", 0.20),
    ]

    settle_steps = 12

    def settle() -> None:
        for _ in range(settle_steps):
            robot.step(timestep)

    for label, kind, magnitude in script:
        settle()

        # Announce the boundary and let the Supervisor take its opening sample.
        # One step is enough: the Supervisor reads the token on the same frame the
        # simulator advances, and both controllers are synchronous by default.
        robot.setCustomData(f"{label}:begin")
        robot.step(timestep)

        log(f"PHASE_BEGIN {label} kind={kind} command={magnitude:.6f}")

        if kind == "spin":
            duration = abs(magnitude) / SPIN_RATE_RAD_S
            sign = 1.0 if magnitude >= 0 else -1.0
            left.setVelocity(-SPIN_WHEEL_SPEED * sign)
            right.setVelocity(SPIN_WHEEL_SPEED * sign)
            predicted = abs(magnitude)
        else:
            duration = abs(magnitude) / STRAIGHT_RATE_M_S
            left.setVelocity(STRAIGHT_WHEEL_SPEED)
            right.setVelocity(STRAIGHT_WHEEL_SPEED)
            predicted = abs(magnitude)

        steps = int(round(duration / (timestep / 1000.0)))
        for _ in range(steps):
            robot.step(timestep)

        left.setVelocity(0.0)
        right.setVelocity(0.0)
        settle()

        robot.setCustomData(f"{label}:end")
        robot.step(timestep)
        log(f"PHASE_END {label} predicted={predicted:.6f} duration_s={duration:.4f}")

    settle()
    robot.setCustomData("idle")
    log("RESULT: done")


if __name__ == "__main__":
    import traceback

    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write("RESULT: exception\n")
            handle.write(traceback.format_exc())
        raise
