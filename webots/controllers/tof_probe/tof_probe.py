"""Probe the e-puck v2 ToF sensor alongside the eight infrared sensors.

The v1 model used throughout this project has a proximity range of roughly 6 cm
(measured: ps5 falls from 1659 at 3 cm to baseline by 8 cm). A 9 cm gap cannot be
sensed with that hardware, which is why the gap-traversal scenarios never worked.

The v2 model adds a `tof` DistanceSensor with a 2 m range and a factory
calibration table. This controller reports both, in metres, so the difference is
concrete rather than argued.

Kept separate from calibration_controller.py on purpose: that one runs in worlds
without a ToF device, and asking for a missing device would abort it.
"""

from __future__ import annotations

from pathlib import Path

from controller import Robot  # noqa: F401  (provided by Webots at runtime)

LOG_PATH = Path(__file__).resolve().parent / "tof_probe.log"

SETTLE_STEPS = 10
SAMPLES = 20


def log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def main() -> int:
    LOG_PATH.unlink(missing_ok=True)
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    for name in ("left wheel motor", "right wheel motor"):
        motor = robot.getDevice(name)
        if motor is not None:
            motor.setPosition(float("inf"))
            motor.setVelocity(0.0)

    ps = []
    for index in range(8):
        device = robot.getDevice(f"ps{index}")
        if device is None:
            log(f"RESULT: error ps{index} missing")
            return 1
        device.enable(timestep)
        ps.append(device)

    tof = robot.getDevice("tof")
    if tof is None:
        log("RESULT: no_tof_sensor (this is e-puck version 1)")
        return 0
    tof.enable(timestep)
    log("RESULT: tof_present")

    for _ in range(SETTLE_STEPS):
        if robot.step(timestep) == -1:
            log("RESULT: error ended during settle")
            return 1

    tof_values = []
    ps_values = [[] for _ in range(8)]
    for _ in range(SAMPLES):
        if robot.step(timestep) == -1:
            break
        tof_values.append(tof.getValue())
        for index in range(8):
            ps_values[index].append(ps[index].getValue())

    if tof_values:
        mean_tof = sum(tof_values) / len(tof_values)
        log(f"TOF_METERS {mean_tof:.4f}")
    for index in range(8):
        if ps_values[index]:
            mean_ps = sum(ps_values[index]) / len(ps_values[index])
            log(f"PS{index}_RAW {mean_ps:.2f}")

    log(f"RESULT: done samples={len(tof_values)}")
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
