import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, FlaskConical, Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  api,
  type PlaygroundComparison,
  type PlaygroundSource,
  type PlaygroundVariant,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Run the session's question again with a source switched off, and watch the
 * scores move.
 *
 * A score says a session went badly; removing a source and re-running says
 * *that source was why*. That is the difference between a report and an
 * instrument, and it is the whole reason this panel exists.
 *
 * Scoring needs a judge; re-running only needs a provider. So when no judge is
 * configured the answers still change and the panel still earns its place —
 * seeing an answer lose a fact when the KG is switched off is often the finding.
 */

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function Delta({ value }: { value: number }) {
  if (Math.abs(value) < 0.005) {
    return <span className="text-gray-400 tabular-nums">±0.00</span>;
  }
  return (
    <span
      className={cn(
        "tabular-nums",
        value < 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"
      )}
    >
      {value > 0 ? "+" : ""}
      {value.toFixed(2)}
    </span>
  );
}

function VariantRow({
  variant,
  baseline,
  metrics,
}: {
  variant: PlaygroundVariant;
  baseline: PlaygroundVariant | null;
  metrics: string[];
}) {
  const isBaseline = baseline !== null && variant.label === baseline.label;
  return (
    <tr className="border-b border-gray-100 dark:border-gray-800 align-top">
      <td className="py-2.5 pr-3">
        <span className={cn("text-sm", isBaseline && "font-medium")}>{variant.label}</span>
        {variant.model && (
          <span className="block font-mono text-[10px] text-gray-400">{variant.model}</span>
        )}
      </td>
      <td className="py-2.5 pr-3 text-right tabular-nums text-sm">{variant.contexts}</td>
      {metrics.map((name) => {
        const value = variant.scores[name];
        const base = baseline?.scores[name];
        return (
          <td key={name} className="py-2.5 pr-3 text-right text-sm">
            {value === undefined ? (
              <span className="text-gray-300 dark:text-gray-600">—</span>
            ) : (
              <>
                <span className="tabular-nums">{value.toFixed(2)}</span>
                {!isBaseline && base !== undefined && (
                  <span className="block text-[11px]">
                    <Delta value={value - base} />
                  </span>
                )}
              </>
            )}
          </td>
        );
      })}
      <td className="py-2.5 pr-3 text-sm text-gray-600 dark:text-gray-300">
        {variant.answer || (
          <span className="text-amber-600 dark:text-amber-400">
            {variant.problems.join("; ") || "did not run"}
          </span>
        )}
      </td>
    </tr>
  );
}

export function ContextPlayground({ sessionId }: { sessionId: string }) {
  const [sources, setSources] = useState<PlaygroundSource[]>([]);
  const [off, setOff] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<PlaygroundComparison | null>(null);
  const [running, setRunning] = useState(false);
  const [withScores, setWithScores] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setSources(await api.listPlaygroundSources(sessionId));
      setResult(null);
      setOff(new Set());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [sessionId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const toggle = (key: string) =>
    setOff((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      // One variant per switched-off source, so each source's contribution is
      // attributable on its own rather than tangled with the others.
      setResult(
        await api.runPlayground(sessionId, {
          ablations: [...off].map((key) => [key]),
          score: withScores,
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  if (!sources.length) {
    return (
      <div className="px-6 py-10 text-center">
        <FlaskConical className="mx-auto mb-3 h-8 w-8 text-gray-300" />
        <p className="text-sm text-gray-500">No stored context for this session.</p>
        <p className="mt-1 text-[11px] text-gray-400">
          Replay needs the retrieved text. Enable{" "}
          <span className="font-mono">KEEL_PAYLOAD_STORE</span> before a session runs,
          or its payloads may have expired.
        </p>
      </div>
    );
  }

  const rows = result
    ? [...(result.baseline ? [result.baseline] : []), ...result.variants]
    : [];
  const metrics = [...new Set(rows.flatMap((r) => Object.keys(r.scores)))].sort();

  return (
    <div className="space-y-4 px-6 py-4">
      <div>
        <h3 className="flex items-center gap-2 text-sm font-semibold">
          <FlaskConical className="h-4 w-4" /> Context playground
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Switch a source off and re-run the same question. A score says the session
          went badly; this says which source was why.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {sources.map((source) => {
          const disabled = off.has(source.key);
          return (
            <button
              key={source.key}
              onClick={() => toggle(source.key)}
              className={cn(
                "rounded-md border px-2.5 py-1.5 text-left text-xs transition-colors",
                disabled
                  ? "border-amber-300 bg-amber-50 text-amber-800 line-through dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300"
                  : "border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
              )}
              title={disabled ? "Will be switched off for one variant" : "Click to switch off"}
            >
              <span className="font-mono">{source.key}</span>
              <span className="ml-2 text-gray-400">
                {source.payloads}× · {fmtBytes(source.bytes)}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" onClick={() => void run()} disabled={running || !off.size}>
          {running ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="mr-1.5 h-3.5 w-3.5" />
          )}
          Re-run {off.size ? `(${off.size} variant${off.size === 1 ? "" : "s"})` : ""}
        </Button>
        <label className="flex items-center gap-1.5 text-xs text-gray-500">
          <input
            type="checkbox"
            checked={withScores}
            onChange={(e) => setWithScores(e.target.checked)}
          />
          Score the answers (needs a judge)
        </label>
        {!off.size && (
          <span className="text-xs text-gray-400">Switch a source off to compare.</span>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {result && !result.store_enabled && (
        <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50/60 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          The payload store is disabled, so variants cannot be stored or scored.
        </div>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] text-left">
            <thead>
              <tr className="border-b border-gray-200 text-[10px] uppercase tracking-wider text-gray-400 dark:border-gray-800">
                <th className="py-2 pr-3 font-medium">Variant</th>
                <th className="py-2 pr-3 text-right font-medium">Ctx</th>
                {metrics.map((m) => (
                  <th key={m} className="py-2 pr-3 text-right font-medium">
                    {m.replace("withoutreference", "")}
                  </th>
                ))}
                <th className="py-2 pr-3 font-medium">Answer</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((variant, i) => (
                <VariantRow
                  key={`${variant.label}-${i}`}
                  variant={variant}
                  baseline={result?.baseline ?? null}
                  metrics={metrics}
                />
              ))}
            </tbody>
          </table>
          {!metrics.length && (
            <p className="mt-3 text-[11px] text-gray-400">
              No scores — re-run only. Scoring needs Ragas and a judge; the answers
              still show what each source was contributing.
            </p>
          )}
        </div>
      )}

      {result && (
        <div className="flex flex-wrap gap-2">
          {rows.map((v) =>
            v.trace_id ? (
              <Badge key={v.trace_id} variant="secondary" className="font-mono text-[10px]">
                {v.label}: {v.trace_id.slice(0, 12)}
              </Badge>
            ) : null
          )}
        </div>
      )}
    </div>
  );
}
