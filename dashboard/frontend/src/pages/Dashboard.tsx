import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Server, Activity, ArrowRight, FolderKanban, ListTodo, Lightbulb, ChevronDown, ChevronRight } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type OverviewData } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { useUser } from "@/context/UserContext";

export function Dashboard() {
  const fetcher = useCallback(() => api.getOverview(), []);
  const { data, loading, error } = usePolling<OverviewData>(fetcher, 10000);
  const { user } = useUser();
  const isLead = user.role === "lead" || user.role === "admin";
  const [recentOpen, setRecentOpen] = useState(false);

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
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">Keel — agentic product development platform overview and quick access</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Member quick links (roles without Build/Platform access) */}
        {!isLead && (
          <Link
            to="/tasks"
            className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group"
            aria-label="View my tasks"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
                  <ListTodo className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">My Tasks</p>
                  <p className="text-2xl font-bold">{d.activity.total_commands}</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
            </div>
            <div className="mt-3 text-xs text-gray-500">Jira work assigned to you</div>
          </Link>
        )}
        {!isLead && (
          <Link
            to="/ideate"
            className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group"
            aria-label="Capture requirements"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-900/30">
                  <Lightbulb className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Requirements</p>
                  <p className="text-2xl font-bold">Ideate</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
            </div>
            <div className="mt-3 text-xs text-gray-500">Capture ideas &amp; requirements</div>
          </Link>
        )}

        {/* Agents */}
        {isLead && (
        <Link
          to="/agents"
          className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group"
          aria-label="View agents"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
                <Bot className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Agents</p>
                <p className="text-2xl font-bold">{d.agents.total}</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="mt-3 flex gap-3 text-xs text-gray-500">
            <span className="text-emerald-600">{d.agents.running} running</span>
            <span>{d.agents.stopped} stopped</span>
          </div>
        </Link>
        )}

        {/* MCP Servers */}
        {isLead && (
        <Link
          to="/mcp"
          className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group"
          aria-label="View MCP servers"
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
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="mt-3 flex gap-3 text-xs text-gray-500">
            <span className="text-emerald-600">{d.mcp_servers.healthy} healthy</span>
            <span className="text-red-500">{d.mcp_servers.unhealthy} unhealthy</span>
          </div>
        </Link>
        )}

        {/* Projects */}
        {isLead && (
        <Link
          to="/projects"
          className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group"
          aria-label="View agent projects"
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
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="mt-3 flex gap-3 text-xs text-gray-500">
            <span className="text-emerald-600">{d.projects.valid} valid</span>
            <span>{d.projects.with_domain} with domain</span>
          </div>
        </Link>
        )}

        {/* Activity */}
        <Link
          to="/activity"
          className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group"
          aria-label="View activity"
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
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
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
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <button
            onClick={() => setRecentOpen((v) => !v)}
            className="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            aria-expanded={recentOpen}
          >
            {recentOpen ? (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            )}
            Recent Activity
            <span className="text-xs font-normal text-gray-500 dark:text-gray-400">
              ({d.activity.recent.length})
            </span>
          </button>
          <Link to="/activity" className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:hover:text-blue-400 transition-colors">
            View all →
          </Link>
        </div>
        {recentOpen && (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {d.activity.recent.length === 0 && (
              <div className="px-6 py-12 text-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">No activity recorded yet.</p>
                <p className="text-xs text-gray-400 mt-2">Use <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs font-mono">agent</code> CLI to generate activity.</p>
              </div>
            )}
            {d.activity.recent.map((entry) => (
              <div key={entry.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <div className="flex items-center gap-3 flex-1">
                  <StatusBadge status={entry.status} />
                  <div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {entry.command}
                      {entry.subcommand && <span className="text-gray-500 dark:text-gray-400"> / {entry.subcommand}</span>}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap ml-4">
                  {entry.duration_ms && <span>{entry.duration_ms}ms</span>}
                  {entry.duration_ms && " · "}
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
