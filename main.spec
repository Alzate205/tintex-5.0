# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('index.html', '.'), ('dashboard.html', '.'), ('proveedores.html', '.'), ('reportes.html', '.'), ('procesos.html', '.'), ('styles.css', '.'), ('script.js', '.'), ('gyh_local.db', '.')],
    hiddenimports=['pywebview', 'flask', 'flask_cors', 'pyjwt', 'pandas', 'xlsxwriter'],
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
    a.datas,
    [],
    name='main',
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
    icon=['Logo.ico'],
)
