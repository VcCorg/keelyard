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

- Node 20+
- Python 3.12 with the backend installed into the active environment:
  ```bash
  pip install -e ../agentic-cli -e ../dashboard/backend pyinstaller
  # Windows also: pip install pywinpty
  ```
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

## Troubleshooting

- **"Keel could not start"** — the backend failed its health check; open the log
  from the dialog. Most first-run failures are a missing PyInstaller hidden import
  (see `backend.spec`).
- **Orphan process / port in use** — the sidecar is killed on quit; if a build was
  force-terminated, quit Keel fully and relaunch (a free port is chosen each time).
