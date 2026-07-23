# Keel Desktop

Ships Keel — the React dashboard **plus** its FastAPI backend and `agentic_cli` —
as a double-click desktop app (macOS `.dmg`, Windows `.exe`). Recipients need **no
Python, no uv, no setup**: the backend is frozen into a self-contained sidecar that
the Electron shell launches and supervises.

## How it works

```
Keel.app / Keel.exe
├─ Electron main   picks a free 127.0.0.1 port, spawns the backend sidecar,
│                  waits for /api/health, opens a window on http://127.0.0.1:<port>/,
│                  and kills the sidecar on quit
├─ resources/frontend/   built React SPA  (served by the backend)
└─ resources/backend/    PyInstaller onedir — FastAPI + agentic_cli, no Python needed
```

The backend serves the SPA itself (`KEEL_SERVE_FRONTEND`), so the UI's relative
`/api`, SSE, and terminal/chat WebSockets all resolve to it with no CORS.

## Prerequisites (build machine only)

- Node 22+ (the project is validated on Node 22 via nvm; system Node 18 will fail
  the frontend build with `SyntaxError: The requested module 'node:util' does not
  provide an export named 'styleText'`):
  ```bash
  nvm install 22
  nvm use 22
  ```
- Python 3.12 with the backend installed into the active environment. If the
  repo was set up with `uv`/`install-agentic-cli.sh`, install PyInstaller the same
  way:
  ```bash
  uv pip install --native-tls pyinstaller
  # Windows also: uv pip install --native-tls pywinpty
  ```
  (If your venv has `pip`, you can use `pip install -e ../agentic-cli -e ../dashboard/backend pyinstaller` instead.)
- **PyInstaller does not cross-compile** — build the macOS app on macOS and the
  Windows app on Windows.

## Build & package

```bash
cd desktop
npm install
npm run package:mac     # -> release/*.dmg   (run on macOS)
npm run package:win     # -> release/*.exe   (run on Windows)
```

`package:*` runs, in order: compile Electron TS → build the frontend and copy it
into `resources/frontend` → freeze the backend into `resources/backend` → run
electron-builder. Installers land in `desktop/release/`.

### End-to-end prep scripts

For a fresh checkout, use the platform prep scripts instead — they activate the
repo `.venv`, install PyInstaller (and `pywinpty` on Windows), gate on Node 22,
sweep stale sidecar processes and bundles, then run the full package pipeline
into `release/`, teeing a build log for troubleshooting:

```bash
# macOS
./scripts/package-mac.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File .\scripts\package-win.ps1
```

CI builds both in `.github/workflows/desktop-build.yml` (macOS + Windows runners;
artifacts on `workflow_dispatch` or a `v*` tag).

## Develop

```bash
# Terminal 1 — backend (from repo root)
./start-backend.sh
# Terminal 2 — Vite dev server
npm --prefix ../dashboard/frontend run dev
# Terminal 3 — Electron against the dev server
cd desktop && npm run dev
```

`KEEL_DEV=1` makes Electron load the Vite dev server (which proxies `/api`) instead
of spawning the sidecar.

## Install

Installers are produced by CI and land in `desktop/release/` (or as workflow artifacts). Pick the one for your OS.

### macOS

1. Download the `Keel-x.x.x.dmg` (arm64 or x64).
2. Open the `.dmg` and drag **Keel** into `/Applications`.
3. Launch **Keel** from `/Applications`.
4. On first run macOS warns the app is unsigned. Right-click the app → **Open** → **Open** to allow it.

### Windows

1. Download the `Keel-x.x.x.exe` installer.
2. Run it and step through the NSIS wizard.
3. Launch **Keel** from the Start menu or desktop shortcut.
4. On first run Windows Defender / SmartScreen warns the app is unsigned. Click **More info** → **Run anyway**.

### After install

- Keel creates `~/.keel/` on first run for settings, env store, and role/persona data.
- The tracker SQLite DB is created on first run.
- Updating is just installing the newer build over the old one; your `~/.keel` data is preserved.

## Distribution (v1 = unsigned)

Installers are **not code-signed** yet, so recipients bypass a one-time OS prompt:

- **macOS:** right-click the app → **Open** → **Open** (once).
- **Windows:** SmartScreen → **More info** → **Run anyway** (once).

Signing + notarization and auto-update are planned follow-ups (see the icons/
entitlements note in `build/`).

## Where data lives

- `~/.keel/` — env store, `admin-settings.json`, role/persona assignments.
- Tracker SQLite DB (central audit trail) — created on first run.
- Backend log — **Help → Open backend logs** (`app.getPath('logs')/backend.log`).

Updating in v1 = install the newer build over the old one; your `~/.keel` data
is preserved.

## Validate the distributable (smoke test)

After `npm run build:backend`, prove the frozen bundle works in a clean sandbox
before packaging (this also runs automatically inside `npm run package:*` and CI):

```bash
npm run smoke:backend
```

It boots the bundle with a throwaway `HOME` and no Python env vars, then checks:
all core API endpoints return 200, a terminal session does a real PTY round-trip
over WebSocket, and the bundled `keel` CLI works end to end (`--help`,
`admin show`, `project create` + `agent add` generating real files).

## Models: cloud, local, and the built-in fallback

The provider chain means the app is usable the moment it's installed:

1. **Cloud** — Vertex AI (`keel init vertex-ai`), Anthropic, or OpenAI keys.
2. **Local models** — anything with an OpenAI-compatible API: **Ollama**
   (default, `http://localhost:11434/v1`), **LM Studio**, **llama.cpp server**,
   **vLLM**. Configure once:
   ```bash
   keel init local-model --model llama3.2            # Ollama default URL
   keel init local-model --model qwen2.5 --url http://localhost:1234/v1  # LM Studio
   keel init local-model --model llama3.2 --default  # route ALL LLM calls locally
   ```
   Use `local:<name>` anywhere a model is accepted (e.g. `local:llama3.2`).
3. **Built-in tiny model (download on first use)** — nothing ships in the
   installer; a one-time ~400MB pull of Qwen2.5-0.5B-Instruct (Apache-2.0)
   into `~/.keel/models` gives real local inference in-process (llama.cpp),
   with no Ollama and no keys:
   ```bash
   keel init builtin-model          # or the Setup panel's Download button
   keel init builtin-model --remove # reclaim the disk space
   ```
4. **Built-in test mode (no config at all)** — when nothing above is
   configured, a deterministic, clearly-labeled provider answers (story
   drafts, enrichment skeletons), so every workflow is demoable straight from
   the package. Output carries a `test-mode` marker and is never mistaken for
   a real model. Strict environments can disable it with
   `KEEL_DISABLE_TEST_MODE=1`.

Fallback chain when no provider is pinned: **vertex → local runtime →
downloaded built-in model → test mode.**

## keel CLI inside the desktop app

The frozen backend is a multi-call binary: `keel-backend cli <args>` runs the
real `keel` CLI. On every boot it writes a `keel` wrapper into `~/.keel/bin` and
prepends it to `PATH`, so terminals opened inside the app can run `keel …` even
on machines with no Python installed.

## Troubleshooting

- **"Keel could not start" / can't initialize the keel package** — the backend
  failed to boot. The classic cause: building against **editable installs**
  (`uv pip install -e …`, which `setup.sh`/`install-agentic-cli.sh` use) —
  PyInstaller cannot collect PEP 660 editable packages. The spec now collects
  first-party code by walking the filesystem, so this is fixed regardless of
  install mode; run `npm run smoke:backend` to verify a build, and check the log
  from the error dialog for anything else.
- **Chat page says unavailable (503)** — chat needs the backend's `[chat]` extra
  (`google-adk`), which currently conflicts with `agentic-cli`'s `click==8.1.7`
  pin (google-adk needs `click>=8.1.8`). Everything else works; relax the pin to
  enable chat.
- **Orphan process / port in use** — the sidecar is killed on quit; if a build was
  force-terminated, quit Keel fully and relaunch (a free port is chosen each time).
