"""Qt widget and system-tray lifecycle."""

import hashlib
import logging
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QRectF, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QFrame, QHBoxLayout, QLabel, QMenu,
    QMessageBox, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .power import SleepController


def make_icon(enabled=False):
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#67e8b3" if enabled else "#a6b5d0")
    painter.setBrush(QColor("#172337"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 18, 18)
    painter.setPen(QPen(color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(16, 16, 32, 34), 135 * 16, 270 * 16)
    painter.drawLine(32, 12, 32, 30)
    painter.end()
    return QIcon(pixmap)


class Switch(QAbstractButton):
    def __init__(self):
        super().__init__()
        self.setCheckable(True)
        self.setFixedSize(64, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Prevent computer from sleeping")
        self.setToolTip("Prevent automatic sleep (Space to toggle)")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff"), 2) if self.hasFocus() else Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#67e8b3" if self.isChecked() else "#46516a"))
        painter.drawRoundedRect(QRectF(2, 2, 60, 32), 16, 16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#10251e" if self.isChecked() else "#ffffff"))
        painter.drawEllipse(QRectF(34 if self.isChecked() else 6, 6, 24, 24))


class Window(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller or SleepController()
        self._quitting = False
        self._notified = False
        self.setWindowTitle("Stay Awake")
        self.setMinimumWidth(390)
        self.setWindowIcon(make_icon())
        self.setStyleSheet("""
            QWidget { background: #101827; color: #eef3fb; font-size: 14px; }
            QLabel#eyebrow { color: #9faec5; font-size: 11px; font-weight: 600; }
            QLabel#title { font-size: 30px; font-weight: 700; }
            QLabel#description, QLabel#footer { color: #a6b5cc; }
            QLabel#status { font-size: 20px; font-weight: 600; }
            QFrame#card { background: #1b273b; border-radius: 16px; }
            QFrame#card QLabel { background: transparent; }
            QPushButton { background: #26364f; border: 1px solid #3a4b65;
                border-radius: 8px; padding: 9px 14px; }
            QPushButton:hover { background: #344a67; }
            QPushButton:disabled { color: #697b98; background: #172337; border-color: #26364f; }
            QPushButton:focus { border: 2px solid #67e8b3; }
            QMenu { background: #1b273b; padding: 5px; }
            QMenu::item { padding: 7px 22px; }
            QMenu::item:selected { background: #344a67; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)
        eyebrow = QLabel("A LITTLE SWITCH. AWAKE WHEN YOU NEED IT.")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        title = QLabel("Stay Awake")
        title.setObjectName("title")
        layout.addWidget(title)
        description = QLabel("Choose when your computer can take a break.")
        description.setObjectName("description")
        description.setWordWrap(True)
        layout.addWidget(description)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        row = QHBoxLayout()
        row.addWidget(QLabel("Prevent sleep"))
        row.addStretch()
        self.switch = Switch()
        self.switch.toggled.connect(self.set_enabled)
        row.addWidget(self.switch)
        card_layout.addLayout(row)
        card_layout.addSpacing(16)
        self.status = QLabel()
        self.status.setObjectName("status")
        card_layout.addWidget(self.status)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setMinimumHeight(48)
        self.detail.setObjectName("description")
        card_layout.addWidget(self.detail)
        layout.addWidget(card)
        self.footer = QLabel()
        self.footer.setObjectName("footer")
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)
        buttons = QHBoxLayout()
        self.hide_button = QPushButton("Hide to tray")
        self.hide_button.clicked.connect(self.close)
        buttons.addWidget(self.hide_button)
        buttons.addStretch()
        quit_button = QPushButton("Exit")
        quit_button.clicked.connect(self.quit_app)
        buttons.addWidget(quit_button)
        layout.addLayout(buttons)

        self.menu = QMenu(self)
        show_action = QAction("Open Stay Awake", self)
        show_action.triggered.connect(self.show_window)
        self.menu.addAction(show_action)
        self.toggle_action = QAction("Prevent sleep", self)
        self.toggle_action.setCheckable(True)
        self.toggle_action.toggled.connect(self.set_enabled)
        self.menu.addAction(self.toggle_action)
        self.menu.addSeparator()
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)
        self.tray = QSystemTrayIcon(make_icon(), self)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.messageClicked.connect(self.show_window)
        self.tray.show()
        self.sync_state()
        self.tray_timer = QTimer(self)
        self.tray_timer.timeout.connect(self.update_tray_availability)
        self.tray_timer.start(2000)
        self.update_tray_availability()

    def sync_state(self):
        enabled = self.controller.enabled
        for control in (self.switch, self.toggle_action):
            control.blockSignals(True)
            control.setChecked(enabled)
            control.blockSignals(False)
        self.switch.update()
        self.status.setText("Keeping you awake" if enabled else "Sleep is allowed")
        self.status.setStyleSheet("color: #67e8b3;" if enabled else "color: #eef3fb;")
        self.detail.setText(
            "Your computer stays awake. The screen can still dim or lock."
            if enabled else "Your system's normal idle sleep settings apply."
        )
        icon = make_icon(enabled)
        self.tray.setIcon(icon)
        self.setWindowIcon(icon)
        self.tray.setToolTip("Stay Awake — " + ("preventing sleep" if enabled else "sleep allowed"))
        self.adjustSize()

    def set_enabled(self, enabled):
        try:
            if enabled:
                self.controller.enable()
            else:
                self.controller.disable()
        except Exception as error:
            self.sync_state()
            self.show_window()
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Sleep control unavailable")
            box.setText("Could not change sleep prevention.")
            box.setInformativeText(
                "Prevention is still enabled. Try switching it off again, or exit the app."
                if self.controller.enabled else
                "Sleep is allowed. Your desktop may not provide a supported sleep inhibitor."
            )
            box.setDetailedText(str(error))
            box.exec()
        self.sync_state()

    def update_tray_availability(self):
        available = QSystemTrayIcon.isSystemTrayAvailable()
        self.hide_button.setEnabled(available)
        self.footer.setText(
            "Closing this window keeps the app in your tray. Exit releases sleep prevention."
            if available else
            "No system tray is available. Keep this window open, or use Exit to quit."
        )
        self.adjustSize()
        if not available and not self.isVisible() and not self._quitting:
            self.show_window()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def closeEvent(self, event):
        if self._quitting:
            event.accept()
            return
        event.ignore()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            if not self._notified:
                self.tray.showMessage("Stay Awake is still running", "Open or exit it from the tray menu.")
                self._notified = True
        else:
            self.update_tray_availability()

    def quit_app(self):
        # Even if explicit release fails, terminating the owner releases the OS
        # request. Never leave a hidden application alive after selecting Exit.
        try:
            self.controller.disable()
        except Exception:
            logging.exception("Could not explicitly release the sleep inhibitor during exit")
        finally:
            self._quitting = True
            self.tray_timer.stop()
            self.tray.hide()
            self.close()
            QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Stay Awake")
    app.setOrganizationName("StayAwake")
    app.setQuitOnLastWindowClosed(False)

    # One owner per user session: launching again opens the existing widget.
    state_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(state_dir / "instance.lock"))
    server_name = "stay-awake-" + hashlib.sha256(str(state_dir).encode()).hexdigest()[:24]
    if not lock.tryLock(0):
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(2000):
            socket.write(b"show")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            QMessageBox.information(None, "Stay Awake", "Stay Awake is already running. Open it from the tray.")
        return 0
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    window = Window()

    def open_existing():
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            window.show_window()
            connection.disconnectFromServer()
            connection.deleteLater()

    server.newConnection.connect(open_existing)
    if not server.listen(server_name):
        QMessageBox.warning(window, "Stay Awake", "Could not create the local app connection. Relaunching may not reopen this window.")

    app.aboutToQuit.connect(window.controller.disable)
    signal.signal(signal.SIGINT, lambda *_: window.quit_app())
    signal.signal(signal.SIGTERM, lambda *_: window.quit_app())
    # Allow Python to process termination signals while Qt owns the event loop.
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(500)
    window.show()
    try:
        return app.exec()
    finally:
        try:
            window.controller.disable()
        finally:
            server.close()
            lock.unlock()
