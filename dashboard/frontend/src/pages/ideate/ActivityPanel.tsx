import { useCallback, useEffect, useState } from "react";
import { History, CheckCircle2, XCircle } from "lucide-react";

interface AuditRow {
  timestamp?: string;
  subcommand?: string;
  status?: string;
  entity_id?: string;
  actor?: string;
  details?: string;
}

export function ActivityPanel({ refreshKey }: { refreshKey?: number }) {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/ideate/audit?limit=25");
      if (res.ok) setRows((await res.json()).actions ?? []);
    } catch {
      /* non-fatal */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const parseTitle = (d?: string) => {
    if (!d) return "";
    try {
      return JSON.parse(d).title ?? "";
    } catch {
      return "";
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center gap-2 mb-3">
        <History className="h-4 w-4 text-gray-400" />
        <h3 className="text-sm font-semibold">Activity</h3>
        {loading && <span className="text-xs text-gray-400">loading…</span>}
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-gray-400">No recorded actions yet.</p>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((r, i) => (
            <li key={i} className="flex items-center gap-2 text-xs">
              {r.status === "success" ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
              )}
              <span className="font-mono text-gray-500">{r.entity_id}</span>
              <span className="text-gray-600 dark:text-gray-300 truncate">{parseTitle(r.details)}</span>
              {r.actor && <span className="ml-auto text-gray-400">{r.actor}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
