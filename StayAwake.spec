# Build on each target OS: python -m PyInstaller --noconfirm StayAwake.spec
import sys
import os
from PyInstaller.utils.hooks import collect_submodules

if sys.platform == 'win32':
    # Avoid bundling unrelated ICU/UCRT DLLs from Anaconda, Poppler or other
    # tools on PATH. Qt uses the Windows system ICU and its wheel's runtimes.
    windows = os.environ.get('SystemRoot', r'C:\Windows')
    os.environ['PATH'] = os.pathsep.join([
        sys.base_prefix, os.path.join(sys.base_prefix, 'DLLs'),
        os.path.join(windows, 'System32'), windows,
    ])

a = Analysis(
    ['launcher.py'], pathex=[], binaries=[], datas=[],
    hiddenimports=collect_submodules('wakepy'),
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtQml', 'PySide6.QtQuick'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StayAwake',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=bool(os.environ.get('STAY_AWAKE_DEBUG')))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StayAwake')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='StayAwake.app',
                 bundle_identifier='org.stayawake.widget',
                 info_plist={'LSUIElement': True, 'NSHighResolutionCapable': True})
