"""Verify real Windows API activation and release, without changing power plans."""
import sys

import pytest

from stay_awake.power import SleepController


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native API")
def test_native_windows_inhibitor_is_released(monkeypatch):
    import wakepy.methods.windows as native

    calls = []
    original = native._call_set_thread_execution_state

    def record_native_call(flags):
        previous = original(flags)
        calls.append((flags, previous))
        return previous

    monkeypatch.setattr(native, "_call_set_thread_execution_state", record_native_call)
    power = SleepController()
    try:
        power.enable()
        assert power.enabled
        assert calls[0][0] == native.Flags.KEEP_RUNNING.value
    finally:
        power.disable()
    assert calls[-1][0] == native.Flags.RELEASE.value
    assert calls[-1][1] & native.ES_SYSTEM_REQUIRED
    assert not power.enabled
