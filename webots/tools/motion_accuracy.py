"""Turn motion-probe output into an accuracy table.

Why this exists
---------------
The probe produces raw pose samples at phase boundaries. Reading them by hand is
where the first analysis went wrong: a naive 90 deg comparison reported a -266 deg
error because samples from different phases were paired, and a naive 180 deg
comparison reported -356 deg because a heading of -176.58 is the same direction as
+183.42 but subtraction wraps at +-180.

Both mistakes look like catastrophic hardware failure and would have sent the
investigation in the wrong direction. So the comparison is encoded here, once,
with the wrapping handled explicitly.

The heading comparison uses the shortest angular distance, and the scale factor is
fitted over several magnitudes rather than taken from a single measurement — a
single angle cannot distinguish a proportional wheelbase error from a fixed
starting offset.

Usage
-----
    python tools/motion_accuracy.py            # read the controller logs
    python tools/motion_accuracy.py --print    # same, but show the fit

No external dependencies.
"""

from __future__ import annotations

import argparse
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE_LOG = ROOT / "controllers" / "motion_probe" / "motion_probe.log"
SUPERVISOR_LOG = ROOT / "controllers" / "motion_supervisor" / "motion_supervisor.log"

# The value the controller currently uses. Kept here so the report can state what
# the measurement implies, without importing the controller (which needs Webots).
CURRENT_WHEEL_BASE_M = 0.0580
WHEEL_RADIUS_M = 0.0200
SPIN_WHEEL_SPEED = 2.0

POSE_RE = re.compile(
    r"token=(?P<token>\S+)\s+t=(?P<t>[\d.]+)\s+"
    r"x=(?P<x>[-\d.]+)\s+y=(?P<y>[-\d.]+)\s+yaw=(?P<yaw>[-\d.]+)"
)
PHASE_RE = re.compile(r"PHASE_BEGIN (?P<label>\S+) kind=(?P<kind>\w+) command=(?P<cmd>[-\d.]+)")


def wrap_deg(value: float) -> float:
    """Shortest signed angle in degrees, in (-180, 180].

    This is the function whose absence produced the bogus -356 deg reading: 180 deg
    and -176.58 deg differ by 3.42 deg, not 356.58 deg.
    """

    while value > 180.0:
        value -= 360.0
    while value <= -180.0:
        value += 360.0
    return value


def read_poses(path: Path) -> dict[str, tuple[float, float, float]]:
    """``token -> (x, y, yaw_rad)`` from the supervisor log."""

    poses: dict[str, tuple[float, float, float]] = {}
    if not path.exists():
        return poses
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = POSE_RE.search(line)
        if match:
            poses[match.group("token")] = (
                float(match.group("x")),
                float(match.group("y")),
                float(match.group("yaw")),
            )
    return poses


def read_script(path: Path) -> list[tuple[str, str, float]]:
    """``[(label, kind, command)]`` in execution order."""

    script: list[tuple[str, str, float]] = []
    if not path.exists():
        return script
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PHASE_RE.search(line)
        if match:
            script.append(
                (match.group("label"), match.group("kind"), float(match.group("cmd")))
            )
    return script


def analyse() -> dict[str, object]:
    poses = read_poses(SUPERVISOR_LOG)
    script = read_script(PROBE_LOG)

    spins: list[dict[str, object]] = []
    straights: list[dict[str, object]] = []

    for label, kind, command in script:
        begin = poses.get(f"{label}:begin")
        end = poses.get(f"{label}:end")
        if begin is None or end is None:
            continue

        if kind == "spin":
            commanded_deg = math.degrees(command)
            measured_deg = math.degrees(end[2] - begin[2])
            error_deg = wrap_deg(measured_deg - commanded_deg)
            actual_deg = commanded_deg + error_deg
            spins.append(
                {
                    "label": label,
                    "commanded_deg": commanded_deg,
                    "measured_deg": measured_deg,
                    "error_deg": error_deg,
                    "actual_deg": actual_deg,
                    "ratio": actual_deg / commanded_deg if commanded_deg else 0.0,
                }
            )
        else:
            measured = math.dist(begin[:2], end[:2])
            error = measured - command
            straights.append(
                {
                    "label": label,
                    "commanded_m": command,
                    "measured_m": measured,
                    "error_m": error,
                    "ratio": measured / command if command else 0.0,
                }
            )

    # Fit actual = k * commanded + c over the spin samples. A single sample cannot
    # separate a proportional error from a fixed offset, so more than one is
    # required for the number to mean anything.
    k = None
    c = None
    residuals: list[float] = []
    if len(spins) >= 2:
        xs = [float(s["commanded_deg"]) for s in spins]
        ys = [float(s["actual_deg"]) for s in spins]
        n = len(xs)
        sx, sy = sum(xs), sum(ys)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, ys))
        denominator = n * sxx - sx * sx
        if denominator:
            k = (n * sxy - sx * sy) / denominator
            c = (sy - k * sx) / n
            residuals = [abs(y - (k * x + c)) for x, y in zip(xs, ys)]

    # With omega = 2 * SPIN * r / L, a rotation that comes out k times larger than
    # commanded means the controller's L is too LARGE by that same factor:
    # a bigger L gives a smaller omega, so too much rotation implies L was
    # understated in omega... concretely, omega_real = omega_code * k, therefore
    # L_real = L_code / k. (Writing L_code * k here was the first version's bug: it
    # proposed 0.05936, which rotates 87.93 deg for a 90 deg command — worse than
    # doing nothing.)
    implied_wheel_base = CURRENT_WHEEL_BASE_M / k if k else None

    return {
        "spins": spins,
        "straights": straights,
        "k": k,
        "offset_deg": c,
        "residuals": residuals,
        "implied_wheel_base_m": implied_wheel_base,
    }


def render(result: dict[str, object]) -> str:
    spins = result["spins"]
    straights = result["straights"]
    k = result["k"]
    c = result["offset_deg"]
    residuals = result["residuals"]
    implied = result["implied_wheel_base_m"]

    lines: list[str] = []
    lines.append("# 动作精度实测")
    lines.append("")
    lines.append(f"数据源：`{PROBE_LOG.relative_to(ROOT)}` + `{SUPERVISOR_LOG.relative_to(ROOT)}`")
    lines.append("")

    lines.append("## 转动")
    lines.append("")
    if spins:
        lines.append("| 命令 | 实测 | 误差 | 实测/命令 |")
        lines.append("| --- | --- | --- | --- |")
        for s in spins:
            lines.append(
                f"| {s['commanded_deg']:+.0f}° | {s['measured_deg']:+.2f}° | "
                f"{s['error_deg']:+.2f}° | {s['ratio']:.4f} |"
            )
    else:
        lines.append("无数据。")
    lines.append("")

    lines.append("## 直行")
    lines.append("")
    if straights:
        lines.append("| 命令 | 实测 | 误差 | 实测/命令 |")
        lines.append("| --- | --- | --- | --- |")
        for s in straights:
            lines.append(
                f"| {s['commanded_m'] * 100:.0f} cm | {s['measured_m'] * 100:.2f} cm | "
                f"{s['error_m'] * 100:+.2f} cm | {s['ratio']:.4f} |"
            )
    else:
        lines.append("无数据。")
    lines.append("")

    lines.append("## 拟合")
    lines.append("")
    if k is not None:
        lines.append(f"实测转角 = {k:.5f} × 命令 + {c:+.3f}°")
        lines.append("")
        if residuals:
            lines.append(
                f"残差均值 {statistics.mean(residuals):.2f}°，最大 {max(residuals):.2f}°。"
            )
            lines.append("")
        if implied is not None:
            lines.append(
                f"若偏差来自轮距：当前 `WHEEL_BASE_M = {CURRENT_WHEEL_BASE_M}`，"
                f"实测隐含值应为 **{implied:.5f}**。"
            )
            lines.append("")
            lines.append(
                "> 这是由转角反推的值，不是厂家标称值。它把转向机构的实际行为"
                "折算成一个等效轮距；修改前应先确认偏差在所有角度上是一致的"
                "（看上面「实测/命令」一列是否接近）。"
            )
    else:
        lines.append("样本不足，无法拟合。至少需要两个不同角度。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="do_print", action="store_true")
    args = parser.parse_args()

    result = analyse()
    text = render(result)

    if args.do_print:
        print(text)
        return 0

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
