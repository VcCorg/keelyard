import { useCallback, useState } from "react";
import { Server, Play, Square, Eye, Wrench, KeyRound, ShieldCheck, ShieldAlert } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type MCPServerInfo } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { LogViewer } from "@/components/LogViewer";

export function MCPServers() {
  const fetcher = useCallback(() => api.listMCPServers(), []);
  const { data: servers, loading, refresh } = usePolling<MCPServerInfo[]>(fetcher, 10000);
  const [viewLogs, setViewLogs] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">MCP Servers</h1>
        <p className="text-sm text-gray-500 mt-1">
          Model Context Protocol servers providing tools to agents
        </p>
      </div>

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
                      {renderAuth(server)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Server details */}
              <div className="mt-3 space-y-1 text-xs text-gray-500">
                {server.port && <div>Port: <span className="font-mono">{server.port}</span></div>}
                {server.url && <div className="font-mono truncate text-gray-400">{server.url}</div>}
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
              <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center gap-2">
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
                  </>
                )}
                <button
                  onClick={() => setViewLogs(viewLogs === server.name ? null : server.name)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 transition-colors"
                >
                  <Eye className="h-3 w-3" /> Logs
                </button>
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
