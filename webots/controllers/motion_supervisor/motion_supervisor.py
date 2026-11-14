"""Sample the true pose at every motion-probe boundary.

The controller cannot read the true pose — that requires a Supervisor. So this
controller only watches, and samples when the probe says to.

Synchronisation
---------------
The probe writes ``<label>:<begin|end>`` into the e-puck Robot node's `customData`
field. Webots documents that field as the intended convenience for robot/supervisor
communication ("may also be used as a convenience for communicating between a robot
and a supervisor without implementing a Receiver / Emitter system",
reference/robot.md), so no Emitter/Receiver pair is needed.

An earlier version guessed boundaries from "the robot is stationary". That produced
a -266 deg error for a 90 deg turn because samples were paired across phases.

`getPosition()` is not cached — it recomputes from the node each call (confirmed in
cyberbotics/webots#3034) — so sampling every frame is correct, not stale.
"""

from __future__ import annotations

import math
from pathlib import Path

from controller import Supervisor  # noqa: F401  (provided by Webots at runtime)

LOG_PATH = Path(__file__).resolve().parent / "motion_supervisor.log"

MAX_SECONDS = 120.0


def log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def main() -> int:
    LOG_PATH.unlink(missing_ok=True)
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())

    log(f"SESSION_START t={robot.getTime():.2f}")

    node = robot.getFromDef("E_PUCK")
    if node is None:
        log("RESULT: error E_PUCK not found")
        robot.simulationQuit(1)
        return 1

    # Field handles are only valid after the world has stepped once on this build.
    robot.step(timestep)

    translation = node.getField("translation")
    if translation is None:
        log("RESULT: error E_PUCK has no translation field")
        robot.simulationQuit(1)
        return 1

    # The probe writes through Robot.setCustomData, so read the same field here.
    custom = node.getField("customData")
    if custom is None:
        log("RESULT: error E_PUCK has no customData field")
        robot.simulationQuit(1)
        return 1

    index = 0
    last_token = ""

    while robot.step(timestep) != -1:
        now = robot.getTime()
        if now > MAX_SECONDS:
            log(f"RESULT: timeout t={now:.2f}")
            robot.simulationQuit(1)
            return 1

        token = custom.getSFString() or ""
        if token == last_token or token in ("", "idle"):
            continue
        last_token = token

        position = node.getPosition()
        orientation = node.getOrientation()
        yaw = math.atan2(orientation[3], orientation[0])
        log(
            f"POSE idx={index} token={token} t={now:.3f} "
            f"x={position[0]:.6f} y={position[1]:.6f} yaw={yaw:.6f}"
        )
        index += 1

    log(f"RESULT: done poses={index}")
    return 0


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
