import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Radio, AlertTriangle, Database, Server, Search as SearchIcon } from "lucide-react";
import { api, type SessionLedger, type TraceSessionRef, type ContextRead } from "@/lib/api";

/** Bytes in the units a human reads budgets in. */
function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/** Sources are a small fixed set; give each a stable colour and icon so a
 *  ledger can be scanned by shape rather than read line by line. */
const SOURCE_STYLE: Record<string, { bar: string; chip: string; Icon: typeof Server }> = {
  mcp: {
    bar: "bg-blue-500",
    chip: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    Icon: Server,
  },
  kg: {
    bar: "bg-violet-500",
    chip: "bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
    Icon: Database,
  },
  retriever: {
    bar: "bg-emerald-500",
    chip: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    Icon: SearchIcon,
  },
};
const styleFor = (s: string) =>
  SOURCE_STYLE[s] ?? {
    bar: "bg-gray-400",
    chip: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
    Icon: Server,
  };

function SourceChip({ source }: { source: string }) {
  const { chip, Icon } = styleFor(source);
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium ${chip}`}>
      <Icon className="h-3 w-3" />
      {source}
    </span>
  );
}

/** Where the context budget went, as one proportional bar. */
function BudgetBar({ ledger }: { ledger: SessionLedger }) {
  if (!ledger.bytes) return null;
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
      {ledger.by_source.map((s) => (
        <div
          key={s.source}
          className={styleFor(s.source).bar}
          style={{ width: `${(s.bytes / ledger.bytes) * 100}%` }}
          title={`${s.source}: ${fmtBytes(s.bytes)} across ${s.reads} read${s.reads === 1 ? "" : "s"}`}
        />
      ))}
    </div>
  );
}

function LedgerRow({ entry, index, maxBytes }: { entry: ContextRead; index: number; maxBytes: number }) {
  const failed = entry.status !== "success";
  return (
    <tr className="border-b border-gray-100 dark:border-gray-800 last:border-0">
      <td className="py-2 pr-3 text-xs text-gray-400 tabular-nums align-top">{index}</td>
      <td className="py-2 pr-3 align-top"><SourceChip source={entry.source} /></td>
      <td className="py-2 pr-3 align-top">
        <div className="text-sm font-medium">{entry.operation}</div>
        {entry.entity_id && (
          <div className="text-[11px] text-gray-400 font-mono truncate max-w-[22rem]" title={entry.entity_id}>
            {entry.entity_id}
          </div>
        )}
      </td>
      <td className="py-2 pr-3 align-top w-40">
        <div className="text-xs tabular-nums text-right">{fmtBytes(entry.bytes)}</div>
        {maxBytes > 0 && (
          <div className="mt-1 h-1 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
            <div className={styleFor(entry.source).bar} style={{ width: `${(entry.bytes / maxBytes) * 100}%` }} />
          </div>
        )}
      </td>
      <td className="py-2 pr-3 text-xs tabular-nums text-right text-gray-500 align-top">
        {entry.duration_ms == null ? "—" : `${entry.duration_ms} ms`}
      </td>
      <td className="py-2 text-right align-top">
        {failed ? (
          <span className="inline-flex items-center gap-1 text-[11px] text-red-600 dark:text-red-400">
            <AlertTriangle className="h-3 w-3" /> {entry.status}
          </span>
        ) : (
          <span className="text-[11px] text-emerald-600 dark:text-emerald-400">ok</span>
        )}
      </td>
    </tr>
  );
}

export function ContextTrace() {
  const [params, setParams] = useSearchParams();
  const selected = params.get("session") ?? "";
  const [sessions, setSessions] = useState<TraceSessionRef[] | null>(null);
  const [ledger, setLedger] = useState<SessionLedger | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api.listTraceSessions()
      .then((s) => alive && setSessions(s))
      .catch((e) => alive && setError(e instanceof Error ? e.message : String(e)));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!selected) { setLedger(null); return; }
    let alive = true;
    api.getSessionLedger(selected)
      .then((l) => alive && setLedger(l))
      .catch((e) => alive && setError(e instanceof Error ? e.message : String(e)));
    return () => { alive = false; };
  }, [selected]);

  const select = useCallback((id: string) => {
    setParams(id ? { session: id } : {});
  }, [setParams]);

  const maxBytes = ledger?.entries.reduce((m, e) => Math.max(m, e.bytes), 0) ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Context Trace</h1>
        <p className="text-sm text-gray-500 mt-1">
          What an agent actually read during a session — every retrieval, in order, with what it cost.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[19rem_1fr]">
        {/* Sessions */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-sm font-semibold">Sessions</h2>
            <p className="text-[11px] text-gray-400 mt-0.5">Most recent first</p>
          </div>

          {sessions === null && (
            <div className="px-4 py-8 text-center text-sm text-gray-400 animate-pulse">Loading…</div>
          )}

          {sessions?.length === 0 && (
            <div className="px-4 py-8 text-center">
              <Radio className="h-7 w-7 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No traced sessions yet.</p>
              <p className="text-[11px] text-gray-400 mt-1">
                Retrieval is recorded once a session runs. Start one from Build Sessions,
                or inspect one from the CLI with{" "}
                <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">keel context trace</code>.
              </p>
            </div>
          )}

          <div className="divide-y divide-gray-100 dark:divide-gray-800 max-h-[34rem] overflow-y-auto">
            {sessions?.map((s) => (
              <button
                key={s.session_id}
                onClick={() => select(s.session_id)}
                className={
                  "w-full text-left px-4 py-3 transition-colors " +
                  (s.session_id === selected
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800/50")
                }
              >
                <div className="font-mono text-xs truncate">{s.session_id}</div>
                <div className="mt-1 flex items-center gap-2 flex-wrap">
                  <span className="text-[11px] text-gray-500 tabular-nums">
                    {s.reads} read{s.reads === 1 ? "" : "s"} · {fmtBytes(s.bytes)}
                  </span>
                  {s.errors > 0 && (
                    <span className="text-[11px] text-red-500">{s.errors} failed</span>
                  )}
                </div>
                <div className="mt-1 flex gap-1 flex-wrap">
                  {s.sources.map((src) => <SourceChip key={src} source={src} />)}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Ledger */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          {!selected && (
            <div className="px-6 py-16 text-center">
              <Radio className="h-9 w-9 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">Select a session to see its context ledger.</p>
            </div>
          )}

          {selected && ledger && (
            <>
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 space-y-3">
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <h2 className="font-mono text-sm">{ledger.session_id}</h2>
                  <div className="flex items-baseline gap-3 text-xs text-gray-500 tabular-nums">
                    <span><span className="font-semibold text-gray-900 dark:text-gray-100">{ledger.reads}</span> reads</span>
                    <span><span className="font-semibold text-gray-900 dark:text-gray-100">{fmtBytes(ledger.bytes)}</span> context</span>
                    {ledger.errors > 0 && <span className="text-red-500">{ledger.errors} failed</span>}
                  </div>
                </div>
                <BudgetBar ledger={ledger} />
                <div className="flex gap-3 flex-wrap">
                  {ledger.by_source.map((s) => (
                    <span key={s.source} className="inline-flex items-center gap-1.5 text-[11px] text-gray-500">
                      <SourceChip source={s.source} />
                      <span className="tabular-nums">{fmtBytes(s.bytes)} · {s.reads}×</span>
                    </span>
                  ))}
                </div>
              </div>

              {ledger.entries.length === 0 ? (
                <div className="px-6 py-14 text-center">
                  <p className="text-sm text-gray-500">This session read nothing.</p>
                  <p className="text-[11px] text-gray-400 mt-1">
                    Either it needed no context, or its retrieval ran outside a session scope.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left min-w-[46rem]">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-wider text-gray-400 border-b border-gray-200 dark:border-gray-800">
                        <th className="py-2 pl-6 pr-3 font-medium w-10">#</th>
                        <th className="py-2 pr-3 font-medium">Source</th>
                        <th className="py-2 pr-3 font-medium">Operation</th>
                        <th className="py-2 pr-3 font-medium text-right">Size</th>
                        <th className="py-2 pr-3 font-medium text-right">Latency</th>
                        <th className="py-2 pr-6 font-medium text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="[&_td:first-child]:pl-6 [&_td:last-child]:pr-6">
                      {ledger.entries.map((e, i) => (
                        <LedgerRow key={e.id || i} entry={e} index={i + 1} maxBytes={maxBytes} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
