import { useCallback, useState } from "react";
import { Bot, Play, Square, MessageSquare, Eye } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type AgentInfo } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { LogViewer } from "@/components/LogViewer";

export function Agents() {
  const fetcher = useCallback(() => api.listAgents(), []);
  const { data: agents, loading, refresh } = usePolling<AgentInfo[]>(fetcher, 5000);
  const [viewLogs, setViewLogs] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleStop = async (name: string) => {
    setActionLoading(name);
    try {
      await api.stopAgent(name);
      refresh();
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
          <p className="text-sm text-gray-500 mt-1">Manage running agent instances</p>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-pulse text-gray-400">Loading agents...</div>
        </div>
      )}

      {!loading && (!agents || agents.length === 0) && (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-10 text-center">
          <Bot className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No agents tracked yet.</p>
          <p className="text-xs text-gray-400 mt-1">
            Start an agent with <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">dva agent start</code>
          </p>
        </div>
      )}

      {agents && agents.length > 0 && (
        <div className="grid gap-4">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/30">
                    <Bot className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{agent.name}</h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <StatusBadge status={agent.status} />
                      <span className="text-xs text-gray-400 capitalize">{agent.agent_type}</span>
                      {agent.pid && <span className="text-xs text-gray-400">PID {agent.pid}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {agent.agent_type === "interactive" && agent.status === "running" && (
                    <a
                      href={`/chat?agent=${agent.name}`}
                      target="_blank"
                      rel="noopener"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-900/50 transition-colors"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                      Chat
                    </a>
                  )}

                  <button
                    onClick={() => setViewLogs(viewLogs === agent.name ? null : agent.name)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    Logs
                  </button>

                  {agent.status === "running" ? (
                    <button
                      onClick={() => handleStop(agent.name)}
                      disabled={actionLoading === agent.name}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
                    >
                      <Square className="h-3.5 w-3.5" />
                      Stop
                    </button>
                  ) : (
                    <button
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300 dark:hover:bg-emerald-900/50 transition-colors"
                    >
                      <Play className="h-3.5 w-3.5" />
                      Start
                    </button>
                  )}
                </div>
              </div>

              {/* Agent details */}
              {agent.path && (
                <div className="mt-3 text-xs text-gray-400 font-mono truncate">{agent.path}</div>
              )}
              {(agent.review_mode || agent.poll_interval) && (
                <div className="mt-2 flex gap-4 text-xs text-gray-500">
                  {agent.review_mode && <span>Mode: {agent.review_mode}</span>}
                  {agent.poll_interval && <span>Poll: {agent.poll_interval}s</span>}
                </div>
              )}

              {/* Log viewer */}
              {viewLogs === agent.name && (
                <div className="mt-4">
                  <LogViewer url={`/api/agents/${agent.name}/logs`} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
