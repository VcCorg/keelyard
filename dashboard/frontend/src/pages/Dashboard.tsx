import { useCallback } from "react";
import { Link } from "react-router-dom";
import { Bot, Server, Activity, ArrowRight, FolderKanban } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type OverviewData } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

export function Dashboard() {
  const fetcher = useCallback(() => api.getOverview(), []);
  const { data, loading, error } = usePolling<OverviewData>(fetcher, 10000);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-4 text-red-700 dark:text-red-300">
        Backend unreachable: {error}
      </div>
    );
  }

  const d = data!;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">DVA Agentic Platform overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Agents */}
        <Link
          to="/agents"
          className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/30">
                <Bot className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Agents</p>
                <p className="text-2xl font-bold">{d.agents.total}</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-indigo-500 transition-colors" />
          </div>
          <div className="mt-3 flex gap-3 text-xs text-gray-500">
            <span className="text-emerald-600">{d.agents.running} running</span>
            <span>{d.agents.stopped} stopped</span>
          </div>
        </Link>

        {/* MCP Servers */}
        <Link
          to="/mcp"
          className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/30">
                <Server className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">MCP Servers</p>
                <p className="text-2xl font-bold">{d.mcp_servers.total}</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-indigo-500 transition-colors" />
          </div>
          <div className="mt-3 flex gap-3 text-xs text-gray-500">
            <span className="text-emerald-600">{d.mcp_servers.healthy} healthy</span>
            <span className="text-red-500">{d.mcp_servers.unhealthy} unhealthy</span>
          </div>
        </Link>

        {/* Projects */}
        <Link
          to="/projects"
          className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-violet-50 dark:bg-violet-900/30">
                <FolderKanban className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Agent Projects</p>
                <p className="text-2xl font-bold">{d.projects.total}</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-indigo-500 transition-colors" />
          </div>
          <div className="mt-3 flex gap-3 text-xs text-gray-500">
            <span className="text-emerald-600">{d.projects.valid} valid</span>
            <span>{d.projects.with_domain} with domain</span>
          </div>
        </Link>

        {/* Activity */}
        <Link
          to="/activity"
          className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-900/30">
                <Activity className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Activity</p>
                <p className="text-2xl font-bold">{d.activity.total_commands}</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-indigo-500 transition-colors" />
          </div>
          <div className="mt-3 text-xs text-gray-500">
            {d.activity.total_errors > 0 && (
              <span className="text-red-500">{d.activity.total_errors} errors</span>
            )}
            {d.activity.last_activity && (
              <span>Last: {new Date(d.activity.last_activity).toLocaleString()}</span>
            )}
            {!d.activity.last_activity && <span>No activity yet</span>}
          </div>
        </Link>
      </div>

      {/* Recent Activity */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Recent Activity</h2>
          <Link to="/activity" className="text-xs text-indigo-600 hover:underline">
            View all
          </Link>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {d.activity.recent.length === 0 && (
            <div className="px-5 py-8 text-center text-sm text-gray-400">
              No activity recorded yet. Use <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs">dva</code> CLI to generate activity.
            </div>
          )}
          {d.activity.recent.map((entry) => (
            <div key={entry.id} className="px-5 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <StatusBadge status={entry.status} />
                <div>
                  <span className="text-sm font-medium">
                    {entry.command}
                    {entry.subcommand && <span className="text-gray-400"> / {entry.subcommand}</span>}
                  </span>
                </div>
              </div>
              <div className="text-xs text-gray-400">
                {entry.duration_ms && <span>{entry.duration_ms}ms</span>}
                {" · "}
                {new Date(entry.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
