"""Pure avoidance logic for the e-puck random-obstacle stage.

This module contains no Webots imports. The Webots adapter is responsible for
reading the eight proximity sensors and applying the returned action to the
wheel motors.

Sensor grouping is based on the official e-puck PROTO (R2025a):

- front: ps0 (front-right), ps7 (front-left)
- left:  ps5 (left), ps6 (front-left)
- right: ps1 (front-right), ps2 (right)
- rear:  ps3 (rear-right), ps4 (rear-left)

The e-puck has no sensor directly behind the robot. ``rear`` is therefore only
a left/right-offset rear estimate, never a guarantee that the centre rear is
clear. The adapter must keep the backup short, slow and limited.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class AvoidState(str, Enum):
    NAVIGATE = "NAVIGATE"
    BRAKE = "BRAKE"
    EVALUATE = "EVALUATE"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    MOVE_AROUND = "MOVE_AROUND"
    REASSESS = "REASSESS"
    BACKUP = "BACKUP"
    RECOVER = "RECOVER"
    REACHED = "REACHED"
    BLOCKED = "BLOCKED"
    STUCK = "STUCK"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class AvoidAction(str, Enum):
    DRIVE = "DRIVE"
    STOP = "STOP"
    SPIN_LEFT = "SPIN_LEFT"
    SPIN_RIGHT = "SPIN_RIGHT"
    SPIN_TO_TARGET = "SPIN_TO_TARGET"
    FORWARD_SLOW = "FORWARD_SLOW"
    BACKWARD_SLOW = "BACKWARD_SLOW"


class TurnDirection(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


@dataclass(frozen=True)
class SensorSnapshot:
    """Raw e-puck proximity values (higher = closer)."""

    ps0: float = 0.0
    ps1: float = 0.0
    ps2: float = 0.0
    ps3: float = 0.0
    ps4: float = 0.0
    ps5: float = 0.0
    ps6: float = 0.0
    ps7: float = 0.0

    @staticmethod
    def _finite(value: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return numeric if math.isfinite(numeric) else 0.0

    def front(self) -> float:
        return max(self._finite(self.ps0), self._finite(self.ps7))

    def left(self) -> float:
        return max(self._finite(self.ps5), self._finite(self.ps6))

    def right(self) -> float:
        return max(self._finite(self.ps1), self._finite(self.ps2))

    def rear(self) -> float:
        return max(self._finite(self.ps3), self._finite(self.ps4))

    def raw(self) -> tuple[float, ...]:
        return tuple(self._finite(getattr(self, f"ps{i}")) for i in range(8))


@dataclass(frozen=True)
class AvoidConfig:
    """Thresholds and limits. Durations are seconds; distances are metres.

    Values are initial engineering defaults. The fixed scenarios are used to
    calibrate the side/rear thresholds from real sensor readings.
    """

    front_stop: float = 120.0
    side_block: float = 200.0
    side_margin: float = 30.0
    rear_clear: float = 80.0
    target_tolerance_m: float = 0.02
    brake_duration_s: float = 0.10
    turn_duration_s: float = 0.90
    move_duration_s: float = 0.60
    backup_duration_s: float = 0.50
    reassess_duration_s: float = 0.10
    heading_tolerance_rad: float = math.radians(5.0)
    max_avoid_attempts: int = 6
    max_backup_attempts: int = 1
    max_same_direction_attempts: int = 2
    # Stall detection. A robot commanded to drive whose encoders barely move is
    # pushing against something: the wheels spin, odometry accumulates, and the
    # controller believes it is travelling. That is how random_seed_4 reported
    # "reached" while sitting 45 cm from the target.
    stall_window_s: float = 0.5
    stall_min_progress_m: float = 0.001


@dataclass(frozen=True)
class AvoidDecision:
    state: AvoidState
    action: AvoidAction
    reason: str
    front: float = 0.0
    left: float = 0.0
    right: float = 0.0
    rear: float = 0.0
    turn_direction: TurnDirection | None = None
    last_failed: TurnDirection | None = None
    avoid_attempts: int = 0
    backup_attempts: int = 0
    turn_count: int = 0
    backup_count: int = 0
    recover_count: int = 0
    terminal: bool = False


def choose_turn_direction(
    snapshot: SensorSnapshot,
    heading_error: float,
    config: AvoidConfig,
    last_turn: TurnDirection | None = None,
    last_failed: TurnDirection | None = None,
    same_direction_count: int = 0,
) -> tuple[TurnDirection | None, str]:
    """Choose a side using the two side sensor groups.

    Lower raw proximity means more space. ``heading_error > 0`` means the target
    is to the left (counter-clockwise), matching the project convention.
    """

    left = snapshot.left()
    right = snapshot.right()
    left_safe = left < config.side_block
    right_safe = right < config.side_block

    if not left_safe and not right_safe:
        return None, f"both sides blocked: left={left:.1f} right={right:.1f}"

    if left_safe and not right_safe:
        return TurnDirection.LEFT, f"right blocked ({right:.1f}); left is the only clear side"

    if right_safe and not left_safe:
        return TurnDirection.RIGHT, f"left blocked ({left:.1f}); right is the only clear side"

    target_side = (
        TurnDirection.LEFT
        if heading_error > 0.0
        else TurnDirection.RIGHT
        if heading_error < 0.0
        else (TurnDirection.LEFT if left <= right else TurnDirection.RIGHT)
    )
    other = TurnDirection.RIGHT if target_side is TurnDirection.LEFT else TurnDirection.LEFT

    if last_failed is not None and last_failed is target_side:
        return other, f"target side {target_side.value} failed last time; choose the other side"

    if last_turn is target_side and same_direction_count >= config.max_same_direction_attempts:
        return other, f"target side {target_side.value} reached the repeat limit; choose the other side"

    if left + config.side_margin < right:
        return TurnDirection.LEFT, f"left clearer: left={left:.1f} right={right:.1f}"

    if right + config.side_margin < left:
        return TurnDirection.RIGHT, f"right clearer: left={left:.1f} right={right:.1f}"

    return target_side, f"both sides clear; prefer target side {target_side.value}"


def can_backup(snapshot: SensorSnapshot, config: AvoidConfig) -> bool:
    """Conservative rear check.

    Only the two rear-offset sensors are available. This is a necessary, not
    sufficient, condition; the adapter still limits backup to a short, slow,
    one-time motion and immediately re-assesses.
    """

    return snapshot.rear() < config.rear_clear


class AvoidStateMachine:
    """Time-driven state machine independent of Webots.

    The adapter calls ``tick`` once per simulation step with the current
    sensor snapshot, odometry distance and heading error. It applies the
    returned action and stops when ``terminal`` is true.
    """

    def __init__(
        self,
        target: tuple[float, float],
        config: AvoidConfig | None = None,
        now: float = 0.0,
    ) -> None:
        self.target = target
        self.config = config or AvoidConfig()
        self.state = AvoidState.NAVIGATE
        self.state_started = now
        self.state_reason = "start"
        self.terminal = False
        self.last_turn: TurnDirection | None = None
        self.last_failed: TurnDirection | None = None
        self.same_direction_count = 0
        self.avoid_attempts = 0
        self.backup_attempts = 0
        self.turn_count = 0
        self.backup_count = 0
        self.recover_count = 0
        # Rolling (time, distance) samples used by the stall detector.
        self.stall_samples: list[tuple[float, float]] = []
        self.stall_events = 0

    def _update_stall(self, now: float, travelled_m: float, commanded: bool) -> bool:
        """Return True when the robot is pushing without moving.

        ``travelled_m`` is the odometry distance accumulated by the caller. Only
        forward/backward commands count: while spinning in place the wheels
        legitimately turn without translating, so a stall check there would
        fire on every turn.
        """

        cfg = self.config
        if not commanded:
            self.stall_samples.clear()
            return False

        self.stall_samples.append((now, travelled_m))
        # Keep one sample older than the window so the measured span can
        # actually reach stall_window_s. Trimming to `>= horizon` alone keeps
        # the window slightly narrower than requested and the span test below
        # then never passes (the first version deadlocked exactly that way).
        horizon = now - cfg.stall_window_s
        self.stall_samples = [s for s in self.stall_samples if s[0] >= horizon]
        if len(self.stall_samples) < 2:
            return False

        progress = self.stall_samples[-1][1] - self.stall_samples[0][1]
        span = self.stall_samples[-1][0] - self.stall_samples[0][0]
        if span < cfg.stall_window_s:
            return False
        if progress < cfg.stall_min_progress_m:
            self.stall_events += 1
            self.stall_samples.clear()
            return True
        return False
        self.stall_events += 1
        self.stall_samples.clear()
        return True

    def _decision(
        self,
        action: AvoidAction,
        reason: str,
        snapshot: SensorSnapshot,
        turn_direction: TurnDirection | None = None,
    ) -> AvoidDecision:
        return AvoidDecision(
            state=self.state,
            action=action,
            reason=reason,
            front=snapshot.front(),
            left=snapshot.left(),
            right=snapshot.right(),
            rear=snapshot.rear(),
            turn_direction=turn_direction,
            last_failed=self.last_failed,
            avoid_attempts=self.avoid_attempts,
            backup_attempts=self.backup_attempts,
            turn_count=self.turn_count,
            backup_count=self.backup_count,
            recover_count=self.recover_count,
            terminal=self.terminal,
        )

    def _enter(self, state: AvoidState, now: float, reason: str) -> None:
        self.state = state
        self.state_started = now
        self.state_reason = reason

    def _finish(self, state: AvoidState, reason: str, snapshot: SensorSnapshot) -> AvoidDecision:
        self._enter(state, self.state_started, reason)
        self.terminal = True
        return self._decision(AvoidAction.STOP, reason, snapshot)

    def force_terminal(self, state: AvoidState, reason: str) -> AvoidDecision:
        """Force TIMEOUT/ERROR (or another terminal state) from the adapter."""

        self.state = state
        self.state_reason = reason
        self.terminal = True
        return AvoidDecision(
            state=state,
            action=AvoidAction.STOP,
            reason=reason,
            last_failed=self.last_failed,
            avoid_attempts=self.avoid_attempts,
            backup_attempts=self.backup_attempts,
            turn_count=self.turn_count,
            backup_count=self.backup_count,
            recover_count=self.recover_count,
            terminal=True,
        )

    def tick(
        self,
        now: float,
        snapshot: SensorSnapshot,
        distance: float,
        heading_error: float,
        travelled_m: float | None = None,
        commanded_forward: bool = False,
    ) -> AvoidDecision:
        cfg = self.config

        if self.terminal:
            return self._decision(AvoidAction.STOP, self.state_reason, snapshot)

        # Stall guard. Checked before the REACHED test on purpose: a robot
        # whose wheels are spinning against an obstacle can see its odometry
        # climb past the target tolerance, which is a false arrival, not a
        # success. random_seed_4 did exactly this (estimated 0.982 m, truth
        # 0.55 m).
        if travelled_m is not None and self._update_stall(now, travelled_m, commanded_forward):
            return self._finish(
                AvoidState.STUCK,
                f"no progress: travelled < {cfg.stall_min_progress_m * 1000:.0f} mm "
                f"in {cfg.stall_window_s:.1f} s while commanded to drive",
                snapshot,
            )

        if self.state is AvoidState.NAVIGATE:
            if distance <= cfg.target_tolerance_m:
                return self._finish(AvoidState.REACHED, "within position tolerance", snapshot)
            if snapshot.front() >= cfg.front_stop:
                self._enter(AvoidState.BRAKE, now, f"front={snapshot.front():.1f} >= {cfg.front_stop:.1f}")
                return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
            return self._decision(AvoidAction.DRIVE, "path clear", snapshot)

        if self.state is AvoidState.BRAKE:
            if now - self.state_started >= cfg.brake_duration_s:
                self._enter(AvoidState.EVALUATE, now, "brake complete")
                return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
            return self._decision(AvoidAction.STOP, self.state_reason, snapshot)

        if self.state is AvoidState.EVALUATE:
            self.avoid_attempts += 1
            if self.avoid_attempts > cfg.max_avoid_attempts:
                return self._finish(
                    AvoidState.STUCK,
                    f"avoid attempts {self.avoid_attempts} > {cfg.max_avoid_attempts}",
                    snapshot,
                )

            # A side can look clear while the front remains blocked, so the
            # robot keeps turning into the same trap. After the same direction
            # has failed repeatedly, allow one short backup even if only one
            # side looks clear. Rear clearance is still required.
            if (
                self.last_failed is not None
                and self.same_direction_count >= cfg.max_same_direction_attempts
                and can_backup(snapshot, cfg)
                and self.backup_attempts < cfg.max_backup_attempts
            ):
                self.backup_attempts += 1
                self.backup_count += 1
                reason = (
                    f"direction {self.last_failed.value} failed repeatedly; "
                    f"rear={snapshot.rear():.1f} < {cfg.rear_clear:.1f}; short backup"
                )
                self._enter(AvoidState.BACKUP, now, reason)
                return self._decision(AvoidAction.BACKWARD_SLOW, reason, snapshot)

            direction, reason = choose_turn_direction(
                snapshot,
                heading_error,
                cfg,
                last_turn=self.last_turn,
                last_failed=self.last_failed,
                same_direction_count=self.same_direction_count,
            )
            if direction is not None:
                if self.last_turn is direction:
                    self.same_direction_count += 1
                else:
                    self.same_direction_count = 1
                self.last_turn = direction
                self.turn_count += 1
                state = AvoidState.TURN_LEFT if direction is TurnDirection.LEFT else AvoidState.TURN_RIGHT
                self._enter(state, now, reason)
                action = AvoidAction.SPIN_LEFT if direction is TurnDirection.LEFT else AvoidAction.SPIN_RIGHT
                return self._decision(action, reason, snapshot, direction)

            if can_backup(snapshot, cfg) and self.backup_attempts < cfg.max_backup_attempts:
                self.backup_attempts += 1
                self.backup_count += 1
                reason = f"both sides blocked; rear={snapshot.rear():.1f} < {cfg.rear_clear:.1f}; short backup"
                self._enter(AvoidState.BACKUP, now, reason)
                return self._decision(AvoidAction.BACKWARD_SLOW, reason, snapshot)

            if can_backup(snapshot, cfg):
                reason = f"both sides blocked; backup limit {cfg.max_backup_attempts} reached"
            else:
                reason = f"both sides blocked; rear={snapshot.rear():.1f} >= {cfg.rear_clear:.1f}"
            return self._finish(AvoidState.BLOCKED, reason, snapshot)

        if self.state in (AvoidState.TURN_LEFT, AvoidState.TURN_RIGHT):
            if now - self.state_started >= cfg.turn_duration_s:
                self._enter(AvoidState.MOVE_AROUND, now, "turn complete")
                return self._decision(AvoidAction.FORWARD_SLOW, self.state_reason, snapshot)
            action = AvoidAction.SPIN_LEFT if self.state is AvoidState.TURN_LEFT else AvoidAction.SPIN_RIGHT
            return self._decision(action, self.state_reason, snapshot, self.last_turn)

        if self.state is AvoidState.MOVE_AROUND:
            if now - self.state_started >= cfg.move_duration_s:
                self._enter(AvoidState.REASSESS, now, "controlled move complete")
                return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
            return self._decision(AvoidAction.FORWARD_SLOW, self.state_reason, snapshot)

        if self.state is AvoidState.REASSESS:
            if now - self.state_started >= cfg.reassess_duration_s:
                if snapshot.front() >= cfg.front_stop:
                    self.last_failed = self.last_turn
                    self._enter(AvoidState.EVALUATE, now, "still blocked after move")
                    return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
                self.recover_count += 1
                self._enter(AvoidState.RECOVER, now, "front clear; recover heading")
                return self._decision(AvoidAction.SPIN_TO_TARGET, self.state_reason, snapshot)
            return self._decision(AvoidAction.STOP, self.state_reason, snapshot)

        if self.state is AvoidState.RECOVER:
            if abs(heading_error) <= cfg.heading_tolerance_rad:
                self._enter(AvoidState.NAVIGATE, now, "heading recovered")
                return self._decision(AvoidAction.DRIVE, self.state_reason, snapshot)
            if snapshot.front() >= cfg.front_stop:
                self._enter(AvoidState.BRAKE, now, f"front={snapshot.front():.1f} while recovering")
                return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
            return self._decision(AvoidAction.SPIN_TO_TARGET, self.state_reason, snapshot)

        if self.state is AvoidState.BACKUP:
            if now - self.state_started >= cfg.backup_duration_s:
                self._enter(AvoidState.REASSESS, now, "backup complete")
                return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
            return self._decision(AvoidAction.BACKWARD_SLOW, self.state_reason, snapshot)

        return self._decision(AvoidAction.STOP, self.state_reason, snapshot)
