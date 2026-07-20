import { useCallback, useMemo, useState } from "react";
import { ScrollText, Filter, User, Globe, Boxes, RefreshCw } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type ActivityEntry } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

/**
 * Audit History — the frontend for `keel history`, exposing the central audit
 * trail's dimensions the Activity feed drops: who acted (actor), from where
 * (source: cli/dashboard), and on what (entity). Filterable and tabular so a
 * lead/admin can review governed actions across features.
 */

const COMMANDS = ["all", "domain", "code", "kg", "skill", "ideate", "project", "devin", "execution", "admin", "mcp", "data"];
const SOURCES = ["all", "cli", "dashboard", "devin"];
const STATUSES = ["all", "success", "error"];

function shortDetail(e: ActivityEntry): string {
  if (e.entity_id) return e.entity_id;
  if (e.repo_path) return e.repo_path;
  const d = e.details as Record<string, unknown> | null | undefined;
  if (d && typeof d === "object") {
    const v = (d.error ?? d.name ?? d.message ?? d.domain) as unknown;
    if (typeof v === "string") return v;
  }
  return "";
}

export function AuditHistory() {
  const [command, setCommand] = useState("all");
  const [source, setSource] = useState("all");
  const [status, setStatus] = useState("all");
  const [actor, setActor] = useState("");

  const fetcher = useCallback(
    () =>
      api.listActivity({
        command: command === "all" ? undefined : command,
        source: source === "all" ? undefined : source,
        status: status === "all" ? undefined : status,
        actor: actor.trim() || undefined,
        limit: 200,
      }),
    [command, source, status, actor]
  );
  const { data: entries, loading, refresh } = usePolling<ActivityEntry[]>(fetcher, 20000);

  const rows = entries ?? [];
  const actors = useMemo(
    () => Array.from(new Set(rows.map((r) => r.actor).filter(Boolean))) as string[],
    [rows]
  );

  const selectCls =
    "h-8 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 text-xs";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
            <ScrollText className="h-6 w-6 text-blue-500" /> Audit History
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            The central audit trail — who did what, from where, on which entity. Mirrors{" "}
            <code className="font-mono">keel history</code>.
          </p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-3">
        <Filter className="h-4 w-4 text-gray-400" />
        <label className="text-xs text-gray-500 flex items-center gap-1.5">
          Command
          <select className={selectCls} value={command} onChange={(e) => setCommand(e.target.value)}>
            {COMMANDS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="text-xs text-gray-500 flex items-center gap-1.5">
          <Globe className="h-3.5 w-3.5" /> Source
          <select className={selectCls} value={source} onChange={(e) => setSource(e.target.value)}>
            {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="text-xs text-gray-500 flex items-center gap-1.5">
          Status
          <select className={selectCls} value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="text-xs text-gray-500 flex items-center gap-1.5">
          <User className="h-3.5 w-3.5" /> Actor
          <input
            className={`${selectCls} w-44`}
            list="audit-actors"
            placeholder="any principal"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
          />
          <datalist id="audit-actors">
            {actors.map((a) => <option key={a} value={a} />)}
          </datalist>
        </label>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
        {loading && !entries && (
          <div className="p-8 text-center text-sm text-gray-400 animate-pulse">Loading…</div>
        )}
        {entries && rows.length === 0 && (
          <div className="p-10 text-center">
            <ScrollText className="h-8 w-8 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No audit entries match these filters.</p>
          </div>
        )}
        {rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-gray-400 border-b border-gray-100 dark:border-gray-800">
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium">Actor</th>
                  <th className="px-4 py-2.5 font-medium">Source</th>
                  <th className="px-4 py-2.5 font-medium">Action</th>
                  <th className="px-4 py-2.5 font-medium">Entity</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800/60">
                {rows.map((e) => (
                  <tr key={e.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                    <td className="px-4 py-2.5 text-xs text-gray-400 whitespace-nowrap">
                      {new Date(e.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {e.actor ? (
                        <span className="text-gray-700 dark:text-gray-300">{e.actor}</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                        {e.source || "cli"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="text-blue-600 dark:text-blue-400 font-medium">{e.command}</span>
                      {e.subcommand && <span className="text-gray-500"> / {e.subcommand}</span>}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">
                      {e.entity_type ? (
                        <span className="inline-flex items-center gap-1">
                          <Boxes className="h-3 w-3 text-gray-400" />
                          {e.entity_type}
                        </span>
                      ) : (
                        <span className="text-gray-300 dark:text-gray-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge status={e.status} /></td>
                    <td className="px-4 py-2.5 text-xs text-gray-400 font-mono max-w-[22rem] truncate" title={shortDetail(e)}>
                      {shortDetail(e)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {rows.length > 0 && (
        <p className="text-xs text-gray-400">Showing {rows.length} most recent matching entries.</p>
      )}
    </div>
  );
}
