import pytest

from papple2.core.emulator import APPLE_II_CYCLES_PER_SECOND, throttle_delay

ONE_SECOND = APPLE_II_CYCLES_PER_SECOND  # cycles a real Apple II runs per second


def test_ahead_of_the_apple_ii_sleeps_the_difference() -> None:
    # One Apple II second of cycles took only a quarter of a second.
    assert throttle_delay(ONE_SECOND, 0.25, 1.0) == pytest.approx(0.75)


def test_behind_the_apple_ii_does_not_sleep() -> None:
    # One Apple II second of cycles took two seconds: nothing to wait for.
    assert throttle_delay(ONE_SECOND, 2.0, 1.0) == 0.0


def test_speed_scales_the_clock() -> None:
    # At three times the real speed, three Apple II seconds of cycles
    # are due after one second.
    assert throttle_delay(3 * ONE_SECOND, 0.0, 3.0) == pytest.approx(1.0)
    assert throttle_delay(3 * ONE_SECOND, 1.0, 3.0) == pytest.approx(0.0)
