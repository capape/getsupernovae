# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for getsupernovae
# Compatible with PyInstaller 3.6+

block_cipher = None

a = Analysis(
    ['getsupernovae.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('locales', 'locales'),
        ('fonts', 'fonts'),
        ('sites.json', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'astropy',
        'astropy.coordinates',
        'astropy.time',
        'astropy.units',
        'astropy.tests.runner',
        'astroquery',
        'bs4',
        'lxml',
        'lxml._elementpath',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'i18n',
        'snparser',
        'snvisibility',
        'snmodels',
        'snconfig',
        'report_pdf',
        'report_text',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib.tests', 'numpy.tests', 'PIL.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='getsupernovae',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
