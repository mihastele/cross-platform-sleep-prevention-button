"""Render the actual widget for visual verification without leaving an inhibitor."""
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from stay_awake.app import Window

app = QApplication([])
# The offscreen Windows plugin does not enumerate installed system fonts.
if os.name == "nt":
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id)
    if families:
        app.setFont(QFont(families[0], 10))
window = Window()
window.show()
app.processEvents()
output = Path(__file__).resolve().parents[1] / "docs"
output.mkdir(exist_ok=True)
try:
    window.grab().save(str(output / "sleep-allowed.png"))
    window.controller.enable()
    window.sync_state()
    app.processEvents()
    window.grab().save(str(output / "stay-awake.png"))
finally:
    window.controller.disable()
    window.tray.hide()
    window.tray_timer.stop()
    window._quitting = True
    window.close()
