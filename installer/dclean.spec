# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Spec for DClean Standalone Executable

import os

block_cipher = None
PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_submodules

datas = [
    (os.path.join(PROJECT_ROOT, "pipeline"), "pipeline"),
    (os.path.join(PROJECT_ROOT, "models"), "models"),
    (os.path.join(PROJECT_ROOT, "config"), "config"),
    (os.path.join(PROJECT_ROOT, "installer", "assets"), "installer/assets"),
]

if os.path.exists(os.path.join(PROJECT_ROOT, "dashboard.py")):
    datas.append((os.path.join(PROJECT_ROOT, "dashboard.py"), "."))

datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")

hiddenimports = [
    "pandas",
    "numpy",
    "sqlite3",
    "sklearn",
    "sklearn.pipeline",
    "sklearn.feature_extraction.text",
    "sklearn.linear_model",
    "sklearn.neighbors",
    "sklearn.utils",
    "scipy",
    "scipy.sparse",
    "scipy.sparse.csgraph",
    "openpyxl",
    "phonenumbers",
    "pydantic",
    "yaml",
    "joblib",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "uvicorn",
    "tornado",
    "altair",
    "pyarrow"
] + collect_submodules("streamlit")

a = Analysis(
    [os.path.join(PROJECT_ROOT, "installer", "dclean_launcher.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DClean",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, "installer", "assets", "dclean_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DClean",
)
