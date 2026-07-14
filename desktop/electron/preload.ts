/**
 * Preload — the only bridge between the sandboxed renderer and the main process.
 * contextIsolation is on and nodeIntegration off, so the UI can touch nothing
 * beyond this minimal, explicit surface.
 */
import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("keel", {
  version: () => ipcRenderer.invoke("keel:version"),
  openLogs: () => ipcRenderer.invoke("keel:open-logs"),
  restartBackend: () => ipcRenderer.invoke("keel:restart-backend"),
});
