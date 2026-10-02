"""Smoke-test the packaged binary and its single-instance connection."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

from PySide6.QtCore import QCoreApplication, QStandardPaths
from PySide6.QtNetwork import QLocalSocket

app = QCoreApplication([])
app.setApplicationName("Stay Awake")
app.setOrganizationName("StayAwake")
state_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
server_name = "stay-awake-" + hashlib.sha256(str(state_dir).encode()).hexdigest()[:24]
socket = QLocalSocket()
socket.connectToServer(server_name)
if socket.waitForConnected(200):
    raise SystemExit("Exit the existing Stay Awake app before this smoke test.")

root = Path(__file__).resolve().parents[1]
binary = root / "dist" / "StayAwake" / ("StayAwake.exe" if sys.platform == "win32" else "StayAwake")
env = dict(os.environ)
if "--native" in sys.argv:
    env.pop("QT_QPA_PLATFORM", None)
else:
    env["QT_QPA_PLATFORM"] = "offscreen"
startup = None
if sys.platform == "win32":
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
process = subprocess.Popen([str(binary)], env=env, startupinfo=startup)
try:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Packaged app exited early: {process.returncode}")
        socket.abort()
        socket.connectToServer(server_name)
        if socket.waitForConnected(200):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Packaged app did not create its local connection")
    socket.disconnectFromServer()
    second = subprocess.run([str(binary)], env=env, startupinfo=startup, timeout=15)
    assert second.returncode == 0, "Second launch failed"
    assert process.poll() is None, "First instance exited after second launch"
    print("Packaged app starts; second launch reaches the existing instance.")
finally:
    # Default is off; this test never activates sleep prevention.
    process.terminate()
    process.wait(timeout=10)
