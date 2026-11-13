from __future__ import annotations

import math
import unittest

from src.avoidance import (
    AvoidAction,
    AvoidConfig,
    AvoidState,
    AvoidStateMachine,
    SensorSnapshot,
    TurnDirection,
    can_backup,
    choose_turn_direction,
)


def snapshot(**overrides: float) -> SensorSnapshot:
    values = {f"ps{i}": 0.0 for i in range(8)}
    values.update(overrides)
    return SensorSnapshot(**values)


def config(**overrides: float) -> AvoidConfig:
    defaults = {
        "front_stop": 120.0,
        "side_block": 200.0,
        "side_margin": 30.0,
        "rear_clear": 80.0,
        "target_tolerance_m": 0.02,
        "brake_duration_s": 0.10,
        "turn_duration_s": 0.90,
        "move_duration_s": 0.60,
        "reassess_duration_s": 0.10,
        "heading_tolerance_rad": math.radians(5.0),
        "max_avoid_attempts": 6,
        "max_backup_attempts": 1,
        "max_same_direction_attempts": 2,
    }
    defaults.update(overrides)
    return AvoidConfig(**defaults)


class SensorSnapshotTests(unittest.TestCase):
    def test_groups_are_mapped_from_official_epuck_positions(self) -> None:
        s = snapshot(ps0=10, ps7=20, ps1=30, ps2=40, ps3=50, ps4=60, ps5=70, ps6=80)
        self.assertEqual(s.front(), 20)
        self.assertEqual(s.right(), 40)
        self.assertEqual(s.rear(), 60)
        self.assertEqual(s.left(), 80)

    def test_non_finite_readings_are_treated_as_zero(self) -> None:
        s = snapshot(ps0=float("nan"), ps7=0, ps5=float("inf"), ps1=float("-inf"))
        self.assertEqual(s.front(), 0)
        self.assertEqual(s.left(), 0)
        self.assertEqual(s.right(), 0)


class DirectionSelectionTests(unittest.TestCase):
    def test_right_blocked_left_clear_turns_left(self) -> None:
        direction, reason = choose_turn_direction(
            snapshot(ps5=50, ps6=40, ps1=250, ps2=260),
            0.0,
            config(),
        )
        self.assertEqual(direction, TurnDirection.LEFT)
        self.assertIn("right", reason)

    def test_left_blocked_right_clear_turns_right(self) -> None:
        direction, reason = choose_turn_direction(
            snapshot(ps5=250, ps6=260, ps1=50, ps2=40),
            0.0,
            config(),
        )
        self.assertEqual(direction, TurnDirection.RIGHT)
        self.assertIn("left", reason)

    def test_both_blocked_returns_none(self) -> None:
        direction, reason = choose_turn_direction(
            snapshot(ps5=250, ps6=260, ps1=250, ps2=260),
            0.0,
            config(),
        )
        self.assertIsNone(direction)
        self.assertIn("both", reason)

    def test_both_clear_prefers_target_side(self) -> None:
        left, _ = choose_turn_direction(snapshot(ps5=50, ps6=50, ps1=60, ps2=60), 0.5, config())
        right, _ = choose_turn_direction(snapshot(ps5=50, ps6=50, ps1=60, ps2=60), -0.5, config())
        self.assertEqual(left, TurnDirection.LEFT)
        self.assertEqual(right, TurnDirection.RIGHT)

    def test_clearance_difference_beyond_margin_wins(self) -> None:
        direction, reason = choose_turn_direction(
            snapshot(ps5=30, ps6=30, ps1=120, ps2=120),
            -0.5,
            config(side_margin=30),
        )
        self.assertEqual(direction, TurnDirection.LEFT)
        self.assertIn("clearer", reason)

    def test_avoids_repeating_failed_direction(self) -> None:
        direction, reason = choose_turn_direction(
            snapshot(ps5=50, ps6=50, ps1=55, ps2=55),
            0.5,
            config(max_same_direction_attempts=2),
            last_turn=TurnDirection.LEFT,
            last_failed=TurnDirection.LEFT,
            same_direction_count=2,
        )
        self.assertEqual(direction, TurnDirection.RIGHT)
        self.assertIn("failed", reason)

    def test_same_direction_limit_switches_when_other_is_clear(self) -> None:
        direction, reason = choose_turn_direction(
            snapshot(ps5=50, ps6=50, ps1=60, ps2=60),
            0.5,
            config(max_same_direction_attempts=1),
            last_turn=TurnDirection.LEFT,
            same_direction_count=1,
        )
        self.assertEqual(direction, TurnDirection.RIGHT)
        self.assertIn("limit", reason)


class BackupSafetyTests(unittest.TestCase):
    def test_backup_allowed_only_when_rear_is_clear(self) -> None:
        self.assertTrue(can_backup(snapshot(ps3=20, ps4=30), config(rear_clear=80)))
        self.assertFalse(can_backup(snapshot(ps3=80, ps4=30), config(rear_clear=80)))
        self.assertFalse(can_backup(snapshot(ps3=30, ps4=200), config(rear_clear=80)))


class StateMachineTests(unittest.TestCase):
    def make(self, **overrides: float) -> AvoidStateMachine:
        return AvoidStateMachine(target=(1.0, 0.0), config=config(**overrides))

    def test_clear_path_navigates(self) -> None:
        sm = self.make()
        d = sm.tick(0.0, snapshot(), distance=0.5, heading_error=0.0)
        self.assertEqual(d.state, AvoidState.NAVIGATE)
        self.assertEqual(d.action, AvoidAction.DRIVE)
        self.assertFalse(d.terminal)

    def test_reached_is_terminal(self) -> None:
        sm = self.make()
        d = sm.tick(0.0, snapshot(), distance=0.01, heading_error=0.0)
        self.assertEqual(d.state, AvoidState.REACHED)
        self.assertEqual(d.action, AvoidAction.STOP)
        self.assertTrue(d.terminal)
        self.assertEqual(sm.tick(1.0, snapshot(), 0.5, 0.0).action, AvoidAction.STOP)

    def test_front_obstacle_brakes_then_turns_left(self) -> None:
        sm = self.make()
        blocked = snapshot(ps0=200, ps7=210, ps5=40, ps6=40, ps1=250, ps2=250)
        d = sm.tick(0.0, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.BRAKE)
        self.assertEqual(d.action, AvoidAction.STOP)
        d = sm.tick(0.11, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.EVALUATE)
        d = sm.tick(0.12, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.TURN_LEFT)
        self.assertEqual(d.action, AvoidAction.SPIN_LEFT)
        self.assertEqual(d.turn_count, 1)

    def test_turn_move_reassess_recover_sequence(self) -> None:
        sm = self.make()
        blocked = snapshot(ps0=200, ps7=210, ps5=40, ps6=40, ps1=250, ps2=250)
        sm.tick(0.0, blocked, 0.5, 0.0)
        sm.tick(0.11, blocked, 0.5, 0.0)
        sm.tick(0.12, blocked, 0.5, 0.0)
        d = sm.tick(1.03, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.MOVE_AROUND)
        self.assertEqual(d.action, AvoidAction.FORWARD_SLOW)
        d = sm.tick(1.64, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.REASSESS)
        d = sm.tick(1.75, snapshot(), 0.5, 0.3)
        self.assertEqual(d.state, AvoidState.RECOVER)
        self.assertEqual(d.action, AvoidAction.SPIN_TO_TARGET)
        d = sm.tick(1.80, snapshot(), 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.NAVIGATE)
        self.assertEqual(d.action, AvoidAction.DRIVE)
        self.assertEqual(d.recover_count, 1)

    def test_reassess_still_blocked_reevaluates_with_failure_memory(self) -> None:
        sm = self.make()
        blocked = snapshot(ps0=200, ps7=210, ps5=40, ps6=40, ps1=250, ps2=250)
        sm.tick(0.0, blocked, 0.5, 0.0)
        sm.tick(0.11, blocked, 0.5, 0.0)
        sm.tick(0.12, blocked, 0.5, 0.0)
        sm.tick(1.03, blocked, 0.5, 0.0)
        d = sm.tick(1.64, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.REASSESS)
        d = sm.tick(1.75, blocked, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.EVALUATE)
        self.assertEqual(d.last_failed, TurnDirection.LEFT)
        d = sm.tick(1.76, snapshot(ps5=40, ps6=40, ps1=250, ps2=250), 0.5, 0.0)
        # Target is not on the left; the failed-left memory should choose right
        # only if the right side is safe. Here right is blocked, so left remains
        # the only safe side.
        self.assertEqual(d.state, AvoidState.TURN_LEFT)

    def test_both_blocked_backs_up_only_with_clear_rear(self) -> None:
        sm = self.make()
        both = snapshot(ps0=200, ps7=210, ps5=250, ps6=250, ps1=250, ps2=250, ps3=20, ps4=30)
        sm.tick(0.0, both, 0.5, 0.0)
        sm.tick(0.11, both, 0.5, 0.0)
        d = sm.tick(0.12, both, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.BACKUP)
        self.assertEqual(d.action, AvoidAction.BACKWARD_SLOW)
        self.assertEqual(d.backup_count, 1)

    def test_both_blocked_with_blocked_rear_is_blocked(self) -> None:
        sm = self.make()
        trapped = snapshot(ps0=200, ps7=210, ps5=250, ps6=250, ps1=250, ps2=250, ps3=200, ps4=210)
        sm.tick(0.0, trapped, 0.5, 0.0)
        sm.tick(0.11, trapped, 0.5, 0.0)
        d = sm.tick(0.12, trapped, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.BLOCKED)
        self.assertEqual(d.action, AvoidAction.STOP)
        self.assertTrue(d.terminal)

    def test_backup_limit_ends_in_blocked_or_stuck(self) -> None:
        sm = self.make(max_backup_attempts=1)
        both = snapshot(ps0=200, ps7=210, ps5=250, ps6=250, ps1=250, ps2=250, ps3=20, ps4=30)
        sm.tick(0.0, both, 0.5, 0.0)
        sm.tick(0.11, both, 0.5, 0.0)
        sm.tick(0.12, both, 0.5, 0.0)
        sm.tick(0.63, both, 0.5, 0.0)  # BACKUP -> REASSESS
        sm.tick(0.74, both, 0.5, 0.0)  # REASSESS -> EVALUATE
        d = sm.tick(0.75, both, 0.5, 0.0)
        self.assertIn(d.state, (AvoidState.BLOCKED, AvoidState.STUCK))
        self.assertTrue(d.terminal)

    def test_avoid_attempt_limit_marks_stuck(self) -> None:
        sm = self.make(max_avoid_attempts=1)
        blocked = snapshot(ps0=200, ps7=210, ps5=40, ps6=40, ps1=250, ps2=250)
        sm.tick(0.0, blocked, 0.5, 0.0)
        sm.tick(0.11, blocked, 0.5, 0.0)
        sm.tick(0.12, blocked, 0.5, 0.0)
        sm.tick(1.03, blocked, 0.5, 0.0)
        sm.tick(1.64, blocked, 0.5, 0.0)
        sm.tick(1.75, blocked, 0.5, 0.0)  # REASSESS -> EVALUATE
        d = sm.tick(1.76, blocked, 0.5, 0.0)  # attempt 2 > max 1
        self.assertEqual(d.state, AvoidState.STUCK)
        self.assertTrue(d.terminal)

    def test_repeated_failed_direction_can_backup_with_one_side_clear(self) -> None:
        sm = self.make(max_backup_attempts=1, max_same_direction_attempts=2)
        sm.state = AvoidState.EVALUATE
        sm.avoid_attempts = 2
        sm.last_failed = TurnDirection.LEFT
        sm.same_direction_count = 2
        snapshot_value = snapshot(ps0=300, ps7=300, ps5=50, ps6=50, ps1=250, ps2=250, ps3=20, ps4=20)
        d = sm.tick(0.0, snapshot_value, 0.5, 0.0)
        self.assertEqual(d.state, AvoidState.BACKUP)
        self.assertEqual(d.action, AvoidAction.BACKWARD_SLOW)

    def test_stall_detected_when_commanded_but_not_moving(self) -> None:
        """Wheels spinning against an obstacle must not look like travel.

        This is the random_seed_4 failure: the robot pushed a box, the encoders
        accumulated distance, and the controller declared "reached" 45 cm from
        the target. The stall guard turns that into an honest STUCK.
        """

        sm = self.make(stall_window_s=0.5, stall_min_progress_m=0.001)
        sm.state = AvoidState.NAVIGATE
        # Commanded forward, odometry frozen at 0.30 m for the whole window.
        decisions = []
        for step in range(20):
            now = step * 0.05
            decisions.append(
                sm.tick(now, snapshot(), 0.7, 0.0, travelled_m=0.30, commanded_forward=True)
            )
            if decisions[-1].terminal:
                break
        self.assertEqual(decisions[-1].state, AvoidState.STUCK)
        self.assertTrue(decisions[-1].terminal)
        self.assertIn("no progress", decisions[-1].reason)

    def test_stall_not_raised_when_moving(self) -> None:
        sm = self.make(stall_window_s=0.5, stall_min_progress_m=0.001)
        sm.state = AvoidState.NAVIGATE
        d = None
        for step in range(20):
            now = step * 0.05
            d = sm.tick(
                now, snapshot(), 0.7, 0.0,
                travelled_m=0.30 + step * 0.01, commanded_forward=True,
            )
            if d.terminal:
                break
        self.assertFalse(d.terminal)
        self.assertEqual(d.state, AvoidState.NAVIGATE)

    def test_stall_ignored_while_spinning(self) -> None:
        """Spinning in place turns the wheels without translating.

        A stall check applied there would fire on every turn, so the guard must
        stay dormant unless the robot is commanded to drive.
        """

        sm = self.make(stall_window_s=0.5, stall_min_progress_m=0.001)
        sm.state = AvoidState.NAVIGATE
        d = None
        for step in range(20):
            now = step * 0.05
            d = sm.tick(
                now, snapshot(), 0.7, 0.0, travelled_m=0.30, commanded_forward=False
            )
            if d.terminal:
                break
        self.assertFalse(d.terminal)

    def test_stall_beats_false_reached(self) -> None:
        """The stall guard must run before the REACHED test.

        A stuck robot's odometry can wander inside the target tolerance while
        the real robot is nowhere near the goal. Ordering matters: checking
        REACHED first would report a false success.
        """

        sm = self.make(
            target_tolerance_m=0.02, stall_window_s=0.5, stall_min_progress_m=0.001
        )
        sm.state = AvoidState.NAVIGATE
        d = None
        # Start well outside the tolerance and let odometry drift into it while
        # the wheels stay physically frozen against the obstacle. This is the
        # random_seed_4 shape: distance shrinking to ~0 purely from encoder
        # accumulation, not from real travel.
        for step in range(20):
            now = step * 0.05
            fake_distance = max(0.005, 0.5 - step * 0.05)
            d = sm.tick(
                now,
                snapshot(),
                fake_distance,
                0.0,
                travelled_m=0.30,
                commanded_forward=True,
            )
            if d.terminal:
                break
        self.assertEqual(d.state, AvoidState.STUCK)
        self.assertNotEqual(d.state, AvoidState.REACHED)

    def test_force_timeout_stops(self) -> None:
        sm = self.make()
        sm.tick(0.0, snapshot(), 0.5, 0.0)
        d = sm.force_terminal(AvoidState.TIMEOUT, "wall clock limit")
        self.assertEqual(d.state, AvoidState.TIMEOUT)
        self.assertEqual(d.action, AvoidAction.STOP)
        self.assertTrue(d.terminal)
        self.assertEqual(sm.tick(1.0, snapshot(), 0.5, 0.0).state, AvoidState.TIMEOUT)


if __name__ == "__main__":
    unittest.main()
