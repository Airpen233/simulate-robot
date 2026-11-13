"""Minimal probe to test whether Webots starts a Python controller."""

import pathlib
import traceback

WEBOTS_DIR = pathlib.Path(__file__).resolve().parents[2]
MARKER = WEBOTS_DIR / "logs" / "probe_entered.txt"
LOG = WEBOTS_DIR / "logs" / "probe.log"


def log(message: str) -> None:
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    print(message, flush=True)


LOG.unlink(missing_ok=True)
MARKER.parent.mkdir(parents=True, exist_ok=True)
MARKER.write_text("controller process entered\n", encoding="utf-8")

try:
    log("PROBE: controller process entered")
    from controller import Robot  # noqa: E402

    log("PROBE: Webots import OK")
    robot = Robot()
    log("PROBE: Robot created")
    log(f"PROBE: timestep={int(robot.getBasicTimeStep())}")
    log(f"PROBE: devices={robot.getNumberOfDevices()}")
    for i in range(robot.getNumberOfDevices()):
        device = robot.getDeviceByIndex(i)
        log(f"PROBE_DEVICE: {i} {device.getName()}")
    log("PROBE: done")
except Exception:  # noqa: BLE001
    log("PROBE: EXCEPTION")
    log(traceback.format_exc())
