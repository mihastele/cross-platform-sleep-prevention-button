import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon

from stay_awake.app import Window
from stay_awake.power import SleepController
from test_power import Mode


@pytest.fixture
def window(app, monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    mode = Mode()
    widget = Window(SleepController(lambda: mode))
    widget._notified = True
    widget.show()
    app.processEvents()
    yield widget, mode
    widget.controller.disable()
    widget.tray_timer.stop()
    widget.tray.hide()
    widget._quitting = True
    widget.close()


def test_switch_and_tray_menu_share_state(window):
    widget, mode = window
    QTest.mouseClick(widget.switch, Qt.MouseButton.LeftButton)
    assert widget.controller.enabled
    assert widget.toggle_action.isChecked()
    widget.toggle_action.trigger()
    assert not widget.controller.enabled
    assert not widget.switch.isChecked()
    assert mode.exited == 1


def test_close_hides_without_releasing_prevention(window, app):
    widget, mode = window
    widget.switch.click()
    widget.close()
    app.processEvents()
    assert not widget.isVisible()
    assert widget.controller.enabled and mode.exited == 0
    widget.show_window()
    assert widget.isVisible()


def test_no_tray_keeps_window_accessible(window, monkeypatch):
    widget, mode = window
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: False)
    widget.close()
    assert widget.isVisible()
    assert not widget.hide_button.isEnabled()
    widget.hide()
    widget.update_tray_availability()
    assert widget.isVisible()


def test_failed_enable_resets_both_controls_and_reports_error(window, monkeypatch):
    widget, mode = window
    mode.fail_enter = True
    dialogs = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: dialogs.append(box.text()))
    widget.switch.click()
    assert not widget.switch.isChecked()
    assert not widget.toggle_action.isChecked()
    assert not widget.controller.enabled
    assert dialogs == ["Could not change sleep prevention."]


def test_exit_releases_inhibitor_and_removes_tray(window, app):
    widget, mode = window
    widget.switch.click()
    widget.quit_app()
    assert not widget.controller.enabled
    assert mode.exited == 1
    assert not widget.tray.isVisible()
    assert not widget.isVisible()


def test_exit_still_quits_when_explicit_release_raises(window):
    widget, mode = window
    widget.switch.click()
    mode.fail_exit = True
    widget.quit_app()
    assert widget._quitting
    assert not widget.tray.isVisible()
    mode.fail_exit = False
