# Build on Windows to produce a Windows executable (onedir, no console).
from pathlib import Path
import sys

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'launcher.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'assets'), 'assets'), (str(root / 'templates'), 'templates')],
    hiddenimports=['sqlalchemy.dialects.sqlite', 'PIL.PngImagePlugin', 'PIL.JpegImagePlugin'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'tkinter', 'matplotlib', 'pandas', 'scipy'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Product-QC-Daily',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    icon=str(root / 'assets' / 'icons' / 'app.ico'),
    version=str(root / 'scripts' / 'version_info.txt') if sys.platform == 'win32' else None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Product-QC-Daily')
