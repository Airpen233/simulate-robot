"""Read the eight proximity sensors once, in a static world, and exit.

The world is static: the robot pose and the obstacle pose are literal values in
the .wbt, nothing moves. That is deliberate — an earlier design teleported the
obstacle with a Supervisor and failed five different ways (controller never
started, logging swallowed by --batch, ``customData`` absent on Solid, sampling
window mismatched, and finally the box not colliding where it was moved).

Nothing here synchronises, so nothing can silently fail to update.

Freezing the wheels is still important: even with no controller command, an
apple-shaped body on a slope-free floor should not drift, but the encoders would
turn if it did and the Supervisor's recorded pose would then disagree with the
pose the sensors were sampled at.

Output is one line per sensor, written to a file next to this controller (print
is not reliably captured in --batch mode).
"""

from __future__ import annotations

from pathlib import Path

from controller import Robot  # noqa: F401  (provided by Webots at runtime)

LOG_PATH = Path(__file__).resolve().parent / "calibration_controller.log"

# From the official E-puck.proto, sensors look along local +X.
# Angles are degrees counter-clockwise from +X; e-puck's +Y points to its left.
SENSOR_BEARINGS = {
    "ps0": -17.2,
    "ps1": -45.9,
    "ps2": -90.0,
    "ps3": -151.5,
    "ps4": 151.2,
    "ps5": 90.0,
    "ps6": 45.8,
    "ps7": 17.1,
}

SENSOR_NAMES = [f"ps{i}" for i in range(8)]

SETTLE_STEPS = 10  # let the sensor pipeline fill before reading
SAMPLES_PER_SENSOR = 20  # average this many consecutive frames


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

    sensors = []
    for name in SENSOR_NAMES:
        device = robot.getDevice(name)
        if device is None:
            log(f"RESULT: error missing sensor {name}")
            return 1
        device.enable(timestep)
        sensors.append(device)

    log("CALIBRATION_START")
    log(
        "SENSOR_BEARINGS "
        + " ".join(f"{n}={SENSOR_BEARINGS[n]:+.1f}" for n in SENSOR_NAMES)
    )

    for _ in range(SETTLE_STEPS):
        if robot.step(timestep) == -1:
            log("RESULT: error simulation ended during settle")
            return 1

    samples: list[list[float]] = []
    for _ in range(SAMPLES_PER_SENSOR):
        if robot.step(timestep) == -1:
            break
        samples.append([s.getValue() for s in sensors])

    if not samples:
        log("RESULT: error no samples collected")
        return 1

    averaged = [
        sum(sample[i] for sample in samples) / len(samples)
        for i in range(len(SENSOR_NAMES))
    ]
    for index, name in enumerate(SENSOR_NAMES):
        log(
            f"READING sensor={name} bearing={SENSOR_BEARINGS[name]:+.1f} "
            f"value={averaged[index]:.2f}"
        )

    log(f"RESULT: done sensors={len(SENSOR_NAMES)} samples={len(samples)}")

    # A plain Robot controller cannot quit the simulation, and the runner only
    # kills Webots after WaitSeconds. Exiting here leaves the process alive with
    # nothing to do, so the log on disk looks stale on the next run. Returning is
    # correct: the runner reads the file, then stops Webots itself.
    return 0


if __name__ == "__main__":
    # An uncaught exception leaves the log empty, which is indistinguishable from
    # "Webots never started the controller". Record it instead.
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
