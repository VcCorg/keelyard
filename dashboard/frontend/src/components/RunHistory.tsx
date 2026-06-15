import { useCallback, useEffect, useRef, useState } from "react";
import { History, Loader2, Check, X, ChevronRight } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type RunInfo, type RunDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS: Record<string, { icon: typeof Check; cls: string }> = {
  running: { icon: Loader2, cls: "text-amber-500" },
  completed: { icon: Check, cls: "text-emerald-500" },
  failed: { icon: X, cls: "text-red-500" },
  cancelled: { icon: X, cls: "text-gray-400" },
};

/** Lists recent runs of a given kind and lets you re-open captured output. */
export function RunHistory({
  kind,
  refreshKey,
  title = "Run History",
}: {
  kind: "code" | "eval" | "cli";
  refreshKey?: number;
  title?: string;
}) {
  const fetcher = useCallback(() => api.listRunHistory(kind, 25), [kind]);
  const { data: runs, refresh } = usePolling<RunInfo[]>(fetcher, 5000);

  const [selected, setSelected] = useState<RunDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (refreshKey !== undefined) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  const open = async (id: string) => {
    setLoadingDetail(true);
    try {
      setSelected(await api.getRunDetail(id));
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView();
  }, [selected]);

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <History className="h-5 w-5 text-gray-400" /> {title}
      </h2>
      <div className="grid lg:grid-cols-2 gap-4">
        {/* List */}
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {runs && runs.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-gray-400 text-sm">No runs yet.</td>
                </tr>
              )}
              {runs?.map((r) => {
                const s = STATUS[r.status] ?? STATUS.completed;
                const Icon = s.icon;
                return (
                  <tr
                    key={r.id}
                    onClick={() => open(r.id)}
                    className={cn(
                      "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors",
                      selected?.id === r.id && "bg-indigo-50 dark:bg-indigo-900/20"
                    )}
                  >
                    <td className="px-3 py-2.5 w-8">
                      <Icon className={cn("h-4 w-4", s.cls, r.status === "running" && "animate-spin")} />
                    </td>
                    <td className="px-1 py-2.5">
                      <p className="font-medium text-gray-800 dark:text-gray-200 truncate max-w-[260px]" title={r.label}>
                        {r.label}
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(r.created_at).toLocaleString()} · {r.line_count} lines
                      </p>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <ChevronRight className="h-4 w-4 text-gray-300 inline" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Detail */}
        <div className="bg-gray-950 rounded-lg border border-gray-800 min-h-[120px]">
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
            <span className="text-xs text-gray-400 font-mono truncate">
              {selected ? selected.command : "Select a run to view output"}
            </span>
            {loadingDetail && <Loader2 className="h-3 w-3 animate-spin text-gray-400" />}
          </div>
          <div className="p-3 max-h-80 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
            {selected?.lines.map((l, i) => (
              <div key={i} className="whitespace-pre-wrap break-all leading-relaxed">
                {l}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>
      </div>
    </section>
  );
}
