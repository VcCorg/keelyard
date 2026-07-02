import { useCallback, useMemo, useState } from "react";
import { ListTodo, AlertCircle, ExternalLink, RefreshCw, Inbox, Play } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { StartWorkDialog } from "@/components/StartWorkDialog";
import { api, type MyJiraIssuesResponse, type JiraIssue } from "@/lib/api";

/**
 * Work Items — Jira stories assigned to the current user, scoped to the Jira
 * projects of onboarded domains. Data comes from the backend `/api/jira`
 * endpoints (JQL: assignee = currentUser() AND project in (<domain projects>)).
 */

const STATUS_CATEGORY_COLORS: Record<string, string> = {
  "To Do": "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  "In Progress": "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  Done: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

const PRIORITY_COLORS: Record<string, string> = {
  Highest: "text-red-600 dark:text-red-400",
  High: "text-red-500 dark:text-red-400",
  Medium: "text-amber-600 dark:text-amber-400",
  Low: "text-gray-500",
  Lowest: "text-gray-400",
};

// Lower rank = higher priority (sorted first).
const PRIORITY_RANK: Record<string, number> = {
  Highest: 0,
  High: 1,
  Medium: 2,
  Low: 3,
  Lowest: 4,
};

function priorityRank(p: string): number {
  return PRIORITY_RANK[p] ?? 5;
}

function fmtDate(s: string): string {
  if (!s) return "—";
  const d = new Date(s);
  return isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
}

interface ProjectGroup {
  project: string;
  items: JiraIssue[];
}

export function Tasks() {
  const fetcher = useCallback(() => api.getMyJiraIssues(), []);
  const { data, loading, refresh } = usePolling<MyJiraIssuesResponse>(fetcher, 60000);
  const [startKey, setStartKey] = useState<string | null>(null);

  // Group issues by Jira project, then sort each group by priority (desc),
  // tie-broken by most-recently updated. Groups themselves are ordered by
  // their highest-priority item so the most urgent project floats to the top.
  const grouped = useMemo<ProjectGroup[]>(() => {
    const issues = data?.issues ?? [];
    const byProject = new Map<string, JiraIssue[]>();
    for (const it of issues) {
      const key = it.project || "—";
      const list = byProject.get(key) ?? [];
      list.push(it);
      byProject.set(key, list);
    }
    const groups: ProjectGroup[] = Array.from(byProject.entries()).map(([project, items]) => ({
      project,
      items: [...items].sort((a, b) => {
        const pr = priorityRank(a.priority) - priorityRank(b.priority);
        if (pr !== 0) return pr;
        return (b.updated || "").localeCompare(a.updated || "");
      }),
    }));
    groups.sort((a, b) => {
      const top = priorityRank(a.items[0]?.priority) - priorityRank(b.items[0]?.priority);
      return top !== 0 ? top : a.project.localeCompare(b.project);
    });
    return groups;
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
          <ListTodo className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">Work Items</h1>
          <p className="text-sm text-gray-500">
            Jira stories assigned to you across your onboarded domains.
          </p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Scope: which domain projects are queried */}
      {data && data.projects.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <span>Projects in scope:</span>
          {data.projects.map((p) => (
            <span key={p} className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 font-mono">
              {p}
            </span>
          ))}
        </div>
      )}

      {/* Not configured */}
      {data && !data.configured && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <strong>Jira is not configured.</strong> Set <code>JIRA_SERVER_URL</code> and{" "}
            <code>JIRA_PERSONAL_ACCESS_TOKEN</code> on the dashboard backend, then refresh. Work
            items are scoped to the Jira project key of each onboarded domain.
          </div>
        </div>
      )}

      {/* Error */}
      {data && data.configured && data.error && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{data.error}</span>
        </div>
      )}

      {/* No projects onboarded */}
      {data && data.configured && !data.error && data.projects.length === 0 && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-blue-50 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>
            No onboarded domain has a Jira project key. Add one on the Domain onboarding page to see
            your work items here.
          </span>
        </div>
      )}

      {/* Empty state */}
      {data && data.configured && !data.error && grouped.length === 0 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-12 text-center text-gray-400">
          <Inbox className="h-8 w-8 mx-auto mb-2 opacity-50" />
          No open issues assigned to you in these projects.
        </div>
      )}

      {/* Issues grouped by project, sorted by priority */}
      {data && data.configured && !data.error && grouped.map((g) => (
        <div key={g.project} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800">
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              {g.project}
            </span>
            <span className="text-xs text-gray-400">
              {g.items.length} issue{g.items.length !== 1 ? "s" : ""}
            </span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 text-left text-xs uppercase tracking-wide text-gray-400">
                <th className="px-4 py-2.5 font-medium">Key</th>
                <th className="px-4 py-2.5 font-medium">Summary</th>
                <th className="px-4 py-2.5 font-medium">Type</th>
                <th className="px-4 py-2.5 font-medium">Priority</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium whitespace-nowrap">Updated</th>
                <th className="px-4 py-2.5 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {g.items.map((t) => (
                <tr key={t.key} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <a
                      href={t.link}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-mono text-xs text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {t.key}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium max-w-md">{t.summary}</div>
                    {t.labels.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {t.labels.slice(0, 4).map((l) => (
                          <span key={l} className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-[10px] text-gray-500">
                            {l}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{t.issuetype || "—"}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`text-xs font-medium ${PRIORITY_COLORS[t.priority] ?? "text-gray-500"}`}>
                      {t.priority || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${STATUS_CATEGORY_COLORS[t.status_category] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"}`}>
                      {t.status || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{fmtDate(t.updated)}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      onClick={() => setStartKey(t.key)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                    >
                      <Play className="h-3 w-3" />
                      Start work
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {data && data.configured && !data.error && data.issues.length > 0 && (
        <p className="text-xs text-gray-400">
          {data.total} issue{data.total !== 1 ? "s" : ""} in {grouped.length} project
          {grouped.length !== 1 ? "s" : ""} · sorted by priority · assignee = currentUser()
        </p>
      )}

      {startKey && <StartWorkDialog issueKey={startKey} onClose={() => setStartKey(null)} />}
    </div>
  );
}
