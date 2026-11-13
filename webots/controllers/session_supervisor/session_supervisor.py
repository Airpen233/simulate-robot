"""Bounded demo supervisor: log the real pose and quit the simulation."""

import math
import os
import pathlib
import traceback

from controller import Supervisor

TIME_STEP_MS = 32
MAX_DEMO_SECONDS = 25.0

WEBOTS_DIR = pathlib.Path(__file__).resolve().parents[2]
LOG_DIR = WEBOTS_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "session_supervisor.log"
MARKER = LOG_DIR / "supervisor_entered.txt"


def log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    print(message, flush=True)


LOG_PATH.unlink(missing_ok=True)
MARKER.write_text("supervisor process entered\n", encoding="utf-8")

try:
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())
    log(f"SESSION_START t={robot.getTime():.2f}")

    robot_node = robot.getFromDef("E_PUCK")
    obstacle_node = robot.getFromDef("OBSTACLE")
    log(f"ROBOT_NODE={'ok' if robot_node else 'missing'}")
    log(f"OBSTACLE_NODE={'ok' if obstacle_node else 'missing'}")
    if robot_node:
        log(f"ROBOT_POSITION {robot_node.getPosition()}")
        log(f"ROBOT_ORIENTATION {robot_node.getOrientation()}")
    if obstacle_node:
        log(f"OBSTACLE_POSITION {obstacle_node.getPosition()}")

    last_log = -1.0
    while robot.step(timestep) != -1:
        now = robot.getTime()
        if now - last_log >= 0.5:
            last_log = now
            if robot_node:
                orientation = robot_node.getOrientation()
                yaw = math.atan2(orientation[3], orientation[0])
                log(
                    f"POSE t={now:.2f} pos={robot_node.getPosition()} "
                    f"yaw={yaw:.4f} ori={orientation}"
                )
        if now > MAX_DEMO_SECONDS:
            log(f"RESULT: session_timeout t={now:.2f}")
            try:
                robot.simulationQuit(0)
                log("QUIT_OK")
            except Exception as exc:  # noqa: BLE001
                log(f"QUIT_ERROR {exc!r}")
            break
except Exception:  # noqa: BLE001
    log("SUPERVISOR_EXCEPTION")
    log(traceback.format_exc())
