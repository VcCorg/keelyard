import { useCallback, useState } from "react";
import { Activity, Filter } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type ActivityEntry } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

const COMMAND_FILTERS = ["all", "agent", "code", "project", "kg", "mcp", "skill", "data"];

export function ActivityFeed() {
  const [filter, setFilter] = useState("all");
  const fetcher = useCallback(
    () => api.listActivity({ command: filter === "all" ? undefined : filter, limit: 100 }),
    [filter]
  );
  const { data: entries, loading } = usePolling<ActivityEntry[]>(fetcher, 15000);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Activity</h1>
        <p className="text-sm text-gray-500 mt-1">CLI command history and agent execution log</p>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-gray-400" />
        {COMMAND_FILTERS.map((cmd) => (
          <button
            key={cmd}
            onClick={() => setFilter(cmd)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === cmd
                ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                : "bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
            }`}
          >
            {cmd}
          </button>
        ))}
      </div>

      {/* Activity list */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        {loading && (
          <div className="p-8 text-center text-sm text-gray-400 animate-pulse">Loading...</div>
        )}

        {!loading && (!entries || entries.length === 0) && (
          <div className="p-10 text-center">
            <Activity className="h-8 w-8 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No activity found.</p>
          </div>
        )}

        {entries && entries.length > 0 && (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {entries.map((entry) => (
              <div key={entry.id} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusBadge status={entry.status} />
                  <div className="min-w-0">
                    <div className="text-sm font-medium">
                      <span className="text-indigo-600 dark:text-indigo-400">{entry.command}</span>
                      {entry.subcommand && (
                        <span className="text-gray-500"> / {entry.subcommand}</span>
                      )}
                    </div>
                    {entry.repo_path && (
                      <div className="text-xs text-gray-400 font-mono truncate mt-0.5">{entry.repo_path}</div>
                    )}
                  </div>
                </div>
                <div className="text-right text-xs text-gray-400 whitespace-nowrap ml-4">
                  {entry.duration_ms !== null && (
                    <div>{entry.duration_ms}ms</div>
                  )}
                  <div>{new Date(entry.timestamp).toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
