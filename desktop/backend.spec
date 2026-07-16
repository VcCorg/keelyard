# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — freeze the Keel FastAPI backend + agentic_cli into a
self-contained sidecar the Electron app spawns. Build ON each target OS
(PyInstaller does not cross-compile): macOS build -> mac sidecar, Windows -> win.

Entry: dashboard/backend/run_desktop.py (loopback uvicorn server; also a
multi-call binary — `keel-backend cli <args>` runs the keel CLI, and wrappers in
~/.keel/bin expose it as plain `keel` inside the app's terminal).
Output: desktop/resources/backend/keel-backend/ (onedir) for electron-builder.

FIRST-PARTY collection (agentic_cli + the dashboard `src` package) is done by
WALKING THE FILESYSTEM, not PyInstaller's collect_* helpers. The workspace
installs both packages editable (`uv pip install -e …`), and PyInstaller cannot
harvest PEP 660 editable installs — that is exactly the "app can't initialize
the keel package" failure seen on macOS. Enumerating every module explicitly as
hiddenimports (with pathex pointing at the source roots) is install-mode-proof
and also pulls in the many lazy, in-function imports static analysis misses.

Third-party deps stay on collect_all so their data files/hidden imports come
along (grpc/protobuf via google-cloud-aiplatform, pydantic-core, uvicorn's
optional websockets/httptools, mcp, neo4j, and the Windows-only pywinpty that
powers the terminal PTY).
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

_SKIP_DIRS = {"__pycache__", "tests", ".pytest_cache"}


def walk_modules(src_root, pkg_name):
    """Enumerate every module in a source tree as dotted names.

    Filesystem-driven so it works no matter how (or whether) the package is
    installed — the fix for editable-install collection failures.
    """
    pkg_dir = os.path.join(src_root, *pkg_name.split("."))
    mods = [pkg_name]
    for dirpath, dirnames, filenames in os.walk(pkg_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        rel = os.path.relpath(dirpath, pkg_dir)
        prefix = pkg_name if rel == "." else pkg_name + "." + rel.replace(os.sep, ".")
        if rel != "." and os.path.isfile(os.path.join(dirpath, "__init__.py")):
            mods.append(prefix)
        for f in filenames:
            if f.endswith(".py") and f != "__init__.py":
                mods.append(prefix + "." + f[:-3])
    return mods


def walk_datas(src_root, pkg_name):
    """Bundle a package's non-.py resource files (templates, static assets)."""
    pkg_dir = os.path.join(src_root, *pkg_name.split("."))
    out = []
    for dirpath, dirnames, filenames in os.walk(pkg_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for f in filenames:
            if f.endswith((".py", ".pyc")):
                continue
            full = os.path.join(dirpath, f)
            dest = os.path.join(pkg_name.replace(".", os.sep),
                                os.path.relpath(dirpath, pkg_dir))
            out.append((full, os.path.normpath(dest)))
    return out


datas, binaries, hiddenimports = [], [], []

# ── First-party: filesystem-driven, editable-install-proof ───────────────────
hiddenimports += walk_modules(CLI_SRC, "agentic_cli")
hiddenimports += walk_modules(BACKEND_DIR, "src")
datas += walk_datas(CLI_SRC, "agentic_cli")

# ── Third-party: collect_all for hidden imports + data files ─────────────────
_COLLECT = [
    "fastapi", "starlette", "uvicorn", "sse_starlette", "anyio",
    "pydantic", "pydantic_core", "mcp", "yaml", "dotenv",
    "rich", "typer", "click", "httpx", "httpcore",
    "google.cloud.aiplatform", "grpc", "neo4j",
    # Optional [chat] extra — chat degrades to 503 when absent, but desktop
    # builds install it so the packaged app keeps the chat feature.
    "google.adk", "google.genai",
    # Built-in tiny model runtime (weights download on first use, never
    # bundled). Optional: absence degrades to the test-mode provider.
    "llama_cpp",
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
    hiddenimports=sorted(set(hiddenimports)),
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
