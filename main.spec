# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('index.html', '.'), ('dashboard.html', '.'), ('proveedores.html', '.'), ('reportes.html', '.'), ('procesos.html', '.'), ('optimizador.html', '.'), ('sostenibilidad.html', '.'), ('factores.html', '.'), ('optimizador.js', '.'), ('sostenibilidad.js', '.'), ('factores.js', '.'), ('styles.css', '.'), ('script.js', '.'), ('gyh_local.db', '.'), ('vendor', 'vendor')],
    hiddenimports=['pywebview', 'flask', 'flask_cors', 'jwt', 'xlsxwriter', 'werkzeug', 'werkzeug.security'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'scipy', 'sklearn', 'matplotlib', 'cv2', 'numba', 'numpy', 'pandas', 'IPython', 'notebook'],
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
