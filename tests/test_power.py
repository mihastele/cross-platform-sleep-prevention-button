from types import SimpleNamespace

import pytest

from stay_awake.power import SleepController


class Mode:
    def __init__(self, fail_enter=False, real_success=True, fail_exit=False):
        self.result = SimpleNamespace(real_success=real_success)
        self.fail_enter = fail_enter
        self.fail_exit = fail_exit
        self.entered = 0
        self.exited = 0

    def __enter__(self):
        if self.fail_enter:
            raise RuntimeError("inhibitor unavailable")
        self.entered += 1
        return self

    def __exit__(self, *args):
        if self.fail_exit:
            raise RuntimeError("release failed")
        self.exited += 1


def test_repeated_enable_holds_one_inhibitor_and_disable_releases_it():
    mode = Mode()
    power = SleepController(lambda: mode)
    assert not power.enabled
    power.enable()
    power.enable()
    assert power.enabled and mode.entered == 1
    power.disable()
    power.disable()
    assert not power.enabled and mode.exited == 1


def test_failed_activation_keeps_sleep_allowed_and_can_retry():
    mode = Mode(fail_enter=True)
    power = SleepController(lambda: mode)
    with pytest.raises(RuntimeError, match="unavailable"):
        power.enable()
    assert not power.enabled
    mode.fail_enter = False
    power.enable()
    assert power.enabled
    power.disable()


def test_fake_success_is_released_and_never_shown_as_active():
    mode = Mode(real_success=False)
    power = SleepController(lambda: mode)
    with pytest.raises(RuntimeError, match="No operating-system"):
        power.enable()
    assert not power.enabled and mode.exited == 1


def test_failed_release_retains_owner_for_retry():
    mode = Mode(fail_exit=True)
    power = SleepController(lambda: mode)
    power.enable()
    with pytest.raises(RuntimeError, match="release failed"):
        power.disable()
    assert power.enabled
    mode.fail_exit = False
    power.disable()
    assert not power.enabled
