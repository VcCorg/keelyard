# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — freeze the Keel FastAPI backend + agentic_cli into a
self-contained sidecar the Electron app spawns. Build ON each target OS
(PyInstaller does not cross-compile): macOS build -> mac sidecar, Windows -> win.

Entry: dashboard/backend/run_desktop.py (loopback uvicorn server).
Output: desktop/resources/backend/keel-backend/ (onedir) for electron-builder.

Heavy/native deps are pulled in wholesale via collect_all so their hidden
imports + data files come along (grpc/protobuf via google-cloud-aiplatform,
pydantic-core, uvicorn's optional websockets/httptools, mcp, neo4j, and the
Windows-only pywinpty that powers the terminal PTY).
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# spec dir = desktop/ ; repo root is its parent.
ROOT = os.path.abspath(os.path.join(os.getcwd(), "."))
if os.path.basename(ROOT) != "desktop":
    # Allow `pyinstaller desktop/backend.spec` run from repo root.
    ROOT = os.path.abspath(os.path.join(ROOT, "desktop"))
REPO = os.path.abspath(os.path.join(ROOT, os.pardir))

BACKEND_DIR = os.path.join(REPO, "dashboard", "backend")
CLI_SRC = os.path.join(REPO, "agentic-cli", "src")
ENTRY = os.path.join(BACKEND_DIR, "run_desktop.py")

datas, binaries, hiddenimports = [], [], []

# Packages whose hidden imports / data files PyInstaller tends to miss.
_COLLECT = [
    "fastapi", "starlette", "uvicorn", "sse_starlette", "anyio",
    "pydantic", "pydantic_core", "mcp", "yaml", "dotenv",
    "rich", "typer", "click", "httpx", "httpcore",
    "google", "google.cloud.aiplatform", "grpc", "neo4j",
    "agentic_cli",
]
for pkg in _COLLECT:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        # Not every package is present on every platform; keep going.
        pass

# uvicorn's protocol implementations are imported lazily by string.
hiddenimports += collect_submodules("uvicorn")
hiddenimports += ["websockets", "websockets.legacy", "httptools"]

# The dashboard backend is imported as the `src` package from BACKEND_DIR.
hiddenimports += collect_submodules("src") if os.path.isdir(os.path.join(BACKEND_DIR, "src")) else []

# Windows terminal PTY backend.
if sys.platform.startswith("win"):
    try:
        d, b, h = collect_all("winpty")
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    [ENTRY],
    pathex=[BACKEND_DIR, CLI_SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide6", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="keel-backend",
    console=True,          # keep stdout/stderr so Electron can capture logs
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="keel-backend",   # -> dist/keel-backend/  (copied to resources/backend)
)
