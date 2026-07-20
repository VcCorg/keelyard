import { useCallback, useState } from "react";
import {
  Server, Play, Square, Eye, Wrench, KeyRound, ShieldCheck, ShieldAlert,
  Plus, Pencil, Trash2, Loader2, Globe,
} from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type MCPServerInfo, type MCPServerUpsert } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { LogViewer } from "@/components/LogViewer";
import { DockerMcpPanel } from "@/components/DockerMcpPanel";

/** Blank draft for the add/edit form. */
const emptyDraft: MCPServerUpsert = { name: "", url: "", type: "sse", description: "", enabled: true };

export function MCPServers() {
  const fetcher = useCallback(() => api.listMCPServers(), []);
  const { data: servers, loading, refresh } = usePolling<MCPServerInfo[]>(fetcher, 10000);
  const [viewLogs, setViewLogs] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Add/edit form state. `editing` holds the server name being edited (null = adding).
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<MCPServerUpsert>(emptyDraft);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const openAdd = () => {
    setEditing(null);
    setDraft(emptyDraft);
    setFormError(null);
    setFormOpen(true);
  };

  const openEdit = (s: MCPServerInfo) => {
    setEditing(s.name);
    setDraft({
      name: s.name,
      url: s.url ?? "",
      type: (s.type === "http" ? "http" : "sse") as "sse" | "http",
      description: s.description ?? "",
      enabled: s.enabled,
    });
    setFormError(null);
    setFormOpen(true);
  };

  const saveDraft = async () => {
    setSaving(true);
    setFormError(null);
    try {
      if (editing) await api.updateMCPServer(editing, draft);
      else await api.addMCPServer(draft);
      setFormOpen(false);
      refresh();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async (s: MCPServerInfo) => {
    setActionLoading(s.name);
    try {
      await api.updateMCPServer(s.name, {
        name: s.name,
        url: s.url ?? "",
        type: (s.type === "http" ? "http" : "sse") as "sse" | "http",
        description: s.description ?? "",
        enabled: !s.enabled,
      });
      refresh();
    } finally {
      setActionLoading(null);
    }
  };

  const removeServer = async (name: string) => {
    if (!window.confirm(`Remove MCP server '${name}' from the registry?`)) return;
    setActionLoading(name);
    try {
      await api.deleteMCPServer(name);
      refresh();
    } finally {
      setActionLoading(null);
    }
  };

  const handleStart = async (name: string) => {
    setActionLoading(name);
    try {
      await api.startMCPServer(name);
      setTimeout(refresh, 2000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (name: string) => {
    setActionLoading(name);
    try {
      await api.stopMCPServer(name);
      setTimeout(refresh, 2000);
    } finally {
      setActionLoading(null);
    }
  };

  const renderAuth = (server: MCPServerInfo) => {
    const status = server.auth_status;
    if (!status || status === "n/a" || status === "unknown") return null;
    if (status === "ok") {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
          <ShieldCheck className="h-3 w-3" /> token valid
        </span>
      );
    }
    const label =
      status === "missing" ? "token missing"
      : status === "invalid" ? "token expired/invalid"
      : status === "unreachable" ? "upstream unreachable"
      : status;
    const Icon = status === "missing" ? KeyRound : ShieldAlert;
    const tone =
      status === "unreachable"
        ? "text-amber-600 dark:text-amber-400"
        : "text-red-600 dark:text-red-400";
    return (
      <span className={`inline-flex items-center gap-1 text-xs ${tone}`} title={server.auth_message || ""}>
        <Icon className="h-3 w-3" /> {label}
      </span>
    );
  };

  const inputCls =
    "mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-2 text-sm";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">MCP Servers</h1>
          <p className="text-sm text-gray-500 mt-1">
            Model Context Protocol servers providing tools to agents
          </p>
        </div>
        <button
          onClick={openAdd}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" /> Add server
        </button>
      </div>

      {/* Docker MCP stack status — the bundled MCP servers require Docker. */}
      <DockerMcpPanel />

      {/* Add / edit form — registers remote SSE/HTTP MCP servers in the CLI
          registry (~/.keel/mcp/registry.json), same store `keel mcp add` uses.
          This is how a packaged desktop install points at a shared MCP stack
          without running Docker locally. */}
      {formOpen && (
        <div className="rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50/40 dark:bg-blue-900/10 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-blue-500" />
            <h2 className="text-sm font-semibold">
              {editing ? `Edit '${editing}'` : "Register a remote MCP server"}
            </h2>
            <span className="text-xs text-gray-400">
              SSE/HTTP endpoint — e.g. a shared team MCP stack
            </span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-gray-500">Name</span>
              <input
                value={draft.name}
                onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                disabled={!!editing}
                placeholder="team-jira"
                className={`${inputCls} disabled:opacity-60`}
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-500">URL</span>
              <input
                value={draft.url}
                onChange={(e) => setDraft((d) => ({ ...d, url: e.target.value }))}
                placeholder="https://mcp.example.com:8128/sse"
                className={inputCls}
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-500">Transport</span>
              <select
                value={draft.type}
                onChange={(e) => setDraft((d) => ({ ...d, type: e.target.value as "sse" | "http" }))}
                className={inputCls}
              >
                <option value="sse">SSE</option>
                <option value="http">HTTP</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-500">Description</span>
              <input
                value={draft.description ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
                placeholder="Shared Jira MCP (team stack)"
                className={inputCls}
              />
            </label>
          </div>
          {formError && <p className="text-xs text-red-600 dark:text-red-400">{formError}</p>}
          <div className="flex items-center gap-2">
            <button
              onClick={saveDraft}
              disabled={saving || !draft.name.trim() || !draft.url.trim()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {editing ? "Save changes" : "Register server"}
            </button>
            <button
              onClick={() => setFormOpen(false)}
              className="px-3 py-1.5 rounded-md text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-pulse text-gray-400">Loading servers...</div>
        </div>
      )}

      {servers && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {servers.map((server) => (
            <div
              key={server.name}
              className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 flex flex-col"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/30">
                    <Server className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">{server.name}</h3>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <StatusBadge status={server.health_status} />
                      <span className="text-xs text-gray-400">{server.type}</span>
                      {server.source === "registry" && (
                        <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
                          registered
                        </span>
                      )}
                      {!server.enabled && (
                        <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                          disabled
                        </span>
                      )}
                      {renderAuth(server)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Server details */}
              <div className="mt-3 space-y-1 text-xs text-gray-500">
                {server.port && <div>Port: <span className="font-mono">{server.port}</span></div>}
                {server.url && <div className="font-mono truncate text-gray-400">{server.url}</div>}
                {server.description && <div className="truncate">{server.description}</div>}
                {server.health_message && (
                  <div className="text-gray-400 truncate">{server.health_message}</div>
                )}
              </div>

              {/* Tools */}
              {server.tools.length > 0 && (
                <div className="mt-3 flex items-center gap-1.5 text-xs text-gray-400">
                  <Wrench className="h-3 w-3" />
                  {server.tools.length} tools
                </div>
              )}

              {/* Actions */}
              <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center gap-2 flex-wrap">
                {server.type === "docker" && (
                  <>
                    {server.health_status === "healthy" ? (
                      <button
                        onClick={() => handleStop(server.name)}
                        disabled={actionLoading === server.name}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 transition-colors disabled:opacity-50"
                      >
                        <Square className="h-3 w-3" /> Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => handleStart(server.name)}
                        disabled={actionLoading === server.name}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300 transition-colors disabled:opacity-50"
                      >
                        <Play className="h-3 w-3" /> Start
                      </button>
                    )}
                    <button
                      onClick={() => setViewLogs(viewLogs === server.name ? null : server.name)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 transition-colors"
                    >
                      <Eye className="h-3 w-3" /> Logs
                    </button>
                  </>
                )}
                {server.source === "registry" && (
                  <>
                    <button
                      onClick={() => openEdit(server)}
                      disabled={actionLoading === server.name}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 transition-colors disabled:opacity-50"
                    >
                      <Pencil className="h-3 w-3" /> Edit
                    </button>
                    <button
                      onClick={() => toggleEnabled(server)}
                      disabled={actionLoading === server.name}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 transition-colors disabled:opacity-50"
                    >
                      {server.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => removeServer(server.name)}
                      disabled={actionLoading === server.name}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="h-3 w-3" /> Remove
                    </button>
                  </>
                )}
              </div>

              {viewLogs === server.name && (
                <div className="mt-3">
                  <LogViewer url={`/api/mcp/servers/${server.name}/logs`} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
