# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_all

datas_ctk, binaries_ctk, hiddenimports_ctk = collect_all('customtkinter')
datas_pystray, binaries_pystray, hiddenimports_pystray = collect_all('pystray')

a = Analysis(
    ['obf\\lucid.py'],
    pathex=['obf'],
    binaries=binaries_ctk + binaries_pystray,
    datas=[('obf\\assets', 'assets'), ('obf\\pyarmor_runtime_000000', 'pyarmor_runtime_000000'), ('obf\\core', 'core'), ('obf\\ui', 'ui')] + datas_ctk + datas_pystray,
    hiddenimports=[
        'tkinter', '_tkinter', 'tkinter.ttk', 'tkinter.messagebox',
        'customtkinter', 'darkdetect',
        'core', 'core.awake', 'core.timer', 'core.updater', 'core.icon',
        'ui', 'ui.widget', 'ui.tray',
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFilter', 'PIL.ImageTk', 'PIL.IcoImagePlugin', 'PIL.PngImagePlugin',
        'pystray', 'pystray._win32', 'pystray._util', 'pystray._base',
        'win32api', 'win32con', 'win32gui', 'win32process', 'win32event',
        'ctypes', 'ctypes.wintypes', 'urllib.request', 'json', 'threading', 'logging', 'os', 'sys', 'math', 'pathlib'
    ] + hiddenimports_ctk + hiddenimports_pystray,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Lucid',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)
