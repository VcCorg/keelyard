/**
 * Keel desktop — Electron main process.
 *
 * Supervises a bundled Python backend sidecar: pick a free loopback port, spawn
 * the PyInstaller-frozen FastAPI server (which also serves the built SPA), wait
 * for /api/health, then open a window pointed at it. The sidecar is always
 * terminated on quit. In dev (KEEL_DEV=1) we skip the sidecar and load the Vite
 * dev server instead (which proxies /api to a separately-run backend).
 */
import { app, BrowserWindow, Menu, shell, dialog, ipcMain } from "electron";
import { spawn, ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import http from "node:http";
import path from "node:path";
import fs from "node:fs";

const isDev = process.env.KEEL_DEV === "1";
const DEV_URL = process.env.KEEL_DEV_SERVER_URL || "http://localhost:5173";

let backend: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;
let logStream: fs.WriteStream | null = null;

function logFilePath(): string {
  const dir = app.getPath("logs");
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, "backend.log");
}

function log(line: string): void {
  const msg = `[${new Date().toISOString()}] ${line}\n`;
  try {
    if (!logStream) logStream = fs.createWriteStream(logFilePath(), { flags: "a" });
    logStream.write(msg);
  } catch {
    /* best-effort */
  }
  process.stdout.write(msg);
}

/** Ask the OS for a free TCP port on loopback. */
function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const addr = srv.address();
      const port = typeof addr === "object" && addr ? addr.port : 0;
      srv.close(() => resolve(port));
    });
  });
}

/** Locate the frozen backend executable and the bundled frontend dir. */
function resolveBackend(): { exe: string; frontendDir: string } {
  const resources = process.resourcesPath;
  const exeName = process.platform === "win32" ? "keel-backend.exe" : "keel-backend";
  return {
    exe: path.join(resources, "backend", "keel-backend", exeName),
    frontendDir: path.join(resources, "frontend"),
  };
}

/** Spawn the backend sidecar on the given port; pipe its output to the log. */
function startBackend(port: number): void {
  const { exe, frontendDir } = resolveBackend();
  if (!fs.existsSync(exe)) {
    throw new Error(`Backend executable not found: ${exe}`);
  }
  log(`Starting backend: ${exe} --port ${port}`);
  backend = spawn(exe, ["--host", "127.0.0.1", "--port", String(port)], {
    env: {
      ...process.env,
      KEEL_SERVE_FRONTEND: frontendDir,
      KEEL_AUTH_MODE: "dev",
      // Force UTF-8 stdio + file I/O for the frozen Python sidecar. On
      // Windows Python otherwise defaults to cp1252, which makes any CLI
      // output containing a checkmark or box-drawing char die with
      // UnicodeEncodeError. PYTHONUTF8=1 only takes effect when set BEFORE
      // the interpreter starts, so setting it here (before spawn) is exactly
      // what we need. See PEP 540.
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  backend.stdout?.on("data", (d) => log(`[backend] ${d.toString().trimEnd()}`));
  backend.stderr?.on("data", (d) => log(`[backend] ${d.toString().trimEnd()}`));
  backend.on("exit", (code, signal) => {
    log(`Backend exited (code=${code}, signal=${signal})`);
    backend = null;
  });
}

/** Poll GET /api/health until it responds 200 or we time out. */
function waitForHealth(port: number, timeoutMs = 60000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  const url = `http://127.0.0.1:${port}/api/health`;
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      });
      req.on("error", retry);
      req.setTimeout(2000, () => req.destroy());
    };
    const retry = () => {
      if (Date.now() > deadline) return reject(new Error("Backend health check timed out"));
      setTimeout(tick, 400);
    };
    tick();
  });
}

function createWindow(loadUrl: string): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    backgroundColor: "#0b0f17",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.once("ready-to-show", () => mainWindow?.show());
  mainWindow.on("closed", () => (mainWindow = null));
  // External links open in the system browser, not a new Electron window.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.loadURL(loadUrl);
}

function showFatal(message: string): void {
  dialog.showErrorBox(
    "Keel could not start",
    `${message}\n\nBackend log:\n${logFilePath()}`
  );
}

function buildMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    ...(process.platform === "darwin"
      ? [{ role: "appMenu" as const }]
      : []),
    { role: "fileMenu" },
    { role: "editMenu" },
    { role: "viewMenu" },
    {
      role: "help",
      submenu: [
        { label: "Open backend logs", click: () => shell.showItemInFolder(logFilePath()) },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function registerIpc(): void {
  ipcMain.handle("keel:version", () => app.getVersion());
  ipcMain.handle("keel:open-logs", () => shell.showItemInFolder(logFilePath()));
  ipcMain.handle("keel:restart-backend", async () => {
    if (isDev) return false;
    stopBackend();
    const port = await getFreePort();
    startBackend(port);
    await waitForHealth(port);
    mainWindow?.loadURL(`http://127.0.0.1:${port}/`);
    return true;
  });
}

async function boot(): Promise<void> {
  buildMenu();
  if (isDev) {
    log(`Dev mode — loading ${DEV_URL} (run the backend separately)`);
    createWindow(DEV_URL);
    mainWindow?.webContents.openDevTools({ mode: "detach" });
    return;
  }
  try {
    const port = await getFreePort();
    startBackend(port);
    await waitForHealth(port);
    log(`Backend healthy on ${port}`);
    createWindow(`http://127.0.0.1:${port}/`);
  } catch (err) {
    log(`Fatal: ${(err as Error).message}`);
    showFatal((err as Error).message);
    app.quit();
  }
}

function stopBackend(): void {
  if (!backend) return;
  log("Stopping backend…");
  try {
    if (process.platform === "win32" && backend.pid) {
      spawn("taskkill", ["/pid", String(backend.pid), "/f", "/t"]);
    } else {
      backend.kill("SIGTERM");
    }
  } catch {
    /* best-effort */
  }
  backend = null;
}

// Single-instance: a second launch focuses the existing window.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
  app.whenReady().then(() => {
    registerIpc();
    boot();
  });
}

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) boot();
});
app.on("before-quit", stopBackend);
app.on("will-quit", stopBackend);
process.on("exit", stopBackend);
