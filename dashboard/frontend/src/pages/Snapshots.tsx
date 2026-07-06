import { useCallback, useState } from "react";
import {
  Camera,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  CircleDashed,
  ShieldCheck,
} from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type DevinSnapshot, type DevinSnapshotState } from "@/lib/api";

const STATE_META: Record<
  DevinSnapshotState,
  { label: string; cls: string; Icon: typeof CheckCircle2 }
> = {
  ok: {
    label: "up to date",
    cls: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-900/50",
    Icon: CheckCircle2,
  },
  drift: {
    label: "stale (drift)",
    cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-900/50",
    Icon: AlertTriangle,
  },
  "meta-missing": {
    label: "meta missing",
    cls: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-900/50",
    Icon: XCircle,
  },
  "no-snapshot": {
    label: "not built",
    cls: "bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700",
    Icon: CircleDashed,
  },
  unverifiable: {
    label: "unverifiable",
    cls: "bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700",
    Icon: HelpCircle,
  },
};

function StateBadge({ state }: { state: DevinSnapshotState }) {
  const meta = STATE_META[state] ?? STATE_META.unverifiable;
  const Icon = meta.Icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-medium ${meta.cls}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {meta.label}
    </span>
  );
}

export function Snapshots() {
  const fetcher = useCallback(() => api.listDevinSnapshots(), []);
  const { data: snapshots, loading, refresh } = usePolling<DevinSnapshot[]>(fetcher, 30000);
  const [verifying, setVerifying] = useState<string | null>(null);

  const verifyOne = async (domain: string) => {
    setVerifying(domain);
    try {
      await api.verifyDevinSnapshot(domain);
      await refresh();
    } catch (err) {
      console.error("verify failed:", err);
    } finally {
      setVerifying(null);
    }
  };

  const rows = snapshots ?? [];
  const built = rows.filter((r) => r.snapshot_id).length;
  const needsAttention = rows.filter(
    (r) => r.state === "drift" || r.state === "meta-missing"
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
            <Camera className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Devin Snapshots</h1>
            <p className="text-sm text-gray-500">
              Per-domain snapshot ids and whether each still matches its meta-repo.
            </p>
          </div>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Re-verify all
        </button>
      </div>

      {/* Summary */}
      <div className="flex flex-wrap gap-3 text-sm">
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800">
          <ShieldCheck className="h-4 w-4 text-gray-500" />
          {built} snapshot{built === 1 ? "" : "s"} across {rows.length} domain
          {rows.length === 1 ? "" : "s"}
        </span>
        {needsAttention > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4" />
            {needsAttention} need{needsAttention === 1 ? "s" : ""} attention
          </span>
        )}
      </div>

      {/* Empty state */}
      {rows.length === 0 && (
        <div className="text-sm text-gray-500 border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-8 text-center">
          No domains configured yet. Build a snapshot with{" "}
          <code>keel domain build-snapshot &lt;slug&gt;</code> or register a pre-built one with{" "}
          <code>--snapshot-id &lt;id&gt;</code>.
        </div>
      )}

      {/* Table */}
      {rows.length > 0 && (
        <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900/50 text-gray-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left font-semibold px-4 py-2.5">Domain</th>
                <th className="text-left font-semibold px-4 py-2.5">Snapshot ID</th>
                <th className="text-left font-semibold px-4 py-2.5">State</th>
                <th className="text-left font-semibold px-4 py-2.5">Meta-repo commit</th>
                <th className="text-left font-semibold px-4 py-2.5">Built</th>
                <th className="text-right font-semibold px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {rows.map((s) => (
                <tr key={s.domain} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                  <td className="px-4 py-3 font-medium text-cyan-700 dark:text-cyan-300">
                    {s.domain}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {s.snapshot_id || <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <StateBadge state={s.state} />
                    <p className="mt-1 text-xs text-gray-500 max-w-md">{s.detail}</p>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {s.state === "drift" && s.recorded_sha ? (
                      <span>
                        <span className="line-through">{s.recorded_sha}</span>
                        {" → "}
                        <span className="text-amber-600 dark:text-amber-400">
                          {s.current_sha || "?"}
                        </span>
                      </span>
                    ) : (
                      s.recorded_sha || "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {s.built_at ? new Date(s.built_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {s.snapshot_id && (
                      <button
                        onClick={() => verifyOne(s.domain)}
                        disabled={verifying === s.domain}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
                      >
                        <RefreshCw
                          className={`h-3.5 w-3.5 ${verifying === s.domain ? "animate-spin" : ""}`}
                        />
                        Verify
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400">
        CLI equivalents: <code>keel devin snapshots list</code> ·{" "}
        <code>keel devin snapshots verify &lt;domain&gt;</code>. Stale snapshots should be rebuilt
        with <code>keel domain build-snapshot &lt;slug&gt;</code>.
      </p>
    </div>
  );
}
