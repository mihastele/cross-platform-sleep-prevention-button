"""Hold a temporary OS sleep inhibitor; never edit a power plan.

All calls happen on the GUI thread, including release, so wakepy's context
is entered and exited on the same thread. Wakepy manages native worker threads.
"""

from wakepy import keep


class SleepController:
    def __init__(self, factory=None):
        self._factory = factory or (lambda: keep.running(on_fail="error"))
        self._mode = None

    @property
    def enabled(self):
        return self._mode is not None

    def enable(self):
        if self.enabled:
            return
        mode = self._factory()
        mode.__enter__()
        # Do not let WAKEPY_FAKE_SUCCESS make the UI claim protection.
        if not mode.result.real_success:
            mode.__exit__(None, None, None)
            raise RuntimeError("No operating-system sleep inhibitor was activated.")
        self._mode = mode

    def disable(self):
        if self._mode is not None:
            self._mode.__exit__(None, None, None)
            self._mode = None
