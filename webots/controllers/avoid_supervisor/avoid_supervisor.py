"""Supervisor verifier for the random-obstacle stage.

It never participates in control. It logs the true pose, obstacle positions,
contact points (collisions) and the true final target error.
"""

from __future__ import annotations

import math
import os
import pathlib
import traceback

from controller import Supervisor

TIME_STEP_MS = 32
MAX_DEMO_SECONDS = 25.0
TARGET_X = float(os.environ.get("SIMULATE_TARGET_X", "1.0"))
TARGET_Y = float(os.environ.get("SIMULATE_TARGET_Y", "0.0"))
SCENE = os.environ.get("SIMULATE_SCENE", "unknown")
SEED = os.environ.get("SIMULATE_SEED", "unknown")

WEBOTS_DIR = pathlib.Path(__file__).resolve().parents[2]
LOG_DIR = WEBOTS_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "avoid_supervisor.log"


def log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    print(message, flush=True)


LOG_PATH.unlink(missing_ok=True)

try:
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())
    log(f"SESSION_START t={robot.getTime():.2f}")
    log(f"SCENE={SCENE} seed={SEED} target=({TARGET_X},{TARGET_Y})")

    robot_node = robot.getFromDef("E_PUCK")
    log(f"ROBOT_NODE={'ok' if robot_node else 'missing'}")

    obstacle_nodes = []
    obstacle_ids = set()
    for index in range(1, 7):
        node = robot.getFromDef(f"OBSTACLE{index}")
        if node:
            obstacle_nodes.append((f"OBSTACLE{index}", node))
            obstacle_ids.add(node.getId())
            log(f"{'OBSTACLE' + str(index)}_POSITION {node.getPosition()}")

    contact_tracking = False
    if robot_node:
        try:
            robot_node.enableContactPointsTracking(timestep, True)
            contact_tracking = True
            log("CONTACT_TRACKING=enabled")
        except Exception as exc:  # noqa: BLE001
            log(f"CONTACT_TRACKING=unavailable {exc!r}")

    if robot_node:
        log(f"ROBOT_POSITION {robot_node.getPosition()}")
        log(f"ROBOT_ORIENTATION {robot_node.getOrientation()}")

    last_log = -1.0
    collision_samples = 0
    max_contacts = 0
    first_collision = None
    while robot.step(timestep) != -1:
        now = robot.getTime()
        contacts = 0
        if robot_node and contact_tracking:
            try:
                raw_contacts = robot_node.getContactPoints(True)
                # getContactPoints includes wheel/floor contacts. Count only
                # contacts whose other node is one of our obstacle solids.
                contacts = sum(1 for contact in raw_contacts if contact.getNodeId() in obstacle_ids)
            except Exception as exc:  # noqa: BLE001
                log(f"CONTACT_READ_ERROR {exc!r}")
                contact_tracking = False
        if contacts > 0:
            collision_samples += 1
            max_contacts = max(max_contacts, contacts)
            if first_collision is None:
                first_collision = now
                log(f"COLLISION t={now:.2f} contacts={contacts}")
        if now - last_log >= 0.5:
            last_log = now
            if robot_node:
                orientation = robot_node.getOrientation()
                yaw = math.atan2(orientation[3], orientation[0])
                log(
                    f"POSE t={now:.2f} pos={robot_node.getPosition()} "
                    f"yaw={yaw:.4f} contacts={contacts}"
                )
        if now > MAX_DEMO_SECONDS:
            if robot_node:
                position = robot_node.getPosition()
                orientation = robot_node.getOrientation()
                yaw = math.atan2(orientation[3], orientation[0])
                error = math.hypot(position[0] - TARGET_X, position[1] - TARGET_Y)
                log(
                    f"RESULT: true_end pos=[{position[0]:.5f},{position[1]:.5f}] "
                    f"yaw={yaw:.4f} target=({TARGET_X},{TARGET_Y}) "
                    f"error={error:.5f} collision_samples={collision_samples} "
                    f"max_contacts={max_contacts} first_collision={first_collision}"
                )
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
