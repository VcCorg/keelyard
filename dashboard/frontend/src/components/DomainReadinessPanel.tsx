import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, CircleSlash, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { KnowledgeFlowMap } from "@/components/KnowledgeFlowMap";
import {
  api,
  type DriftSignal,
  type KnowledgeMap,
  type ReadinessCard,
  type ReadinessDimension,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Could a new teammate ship from this domain?
 *
 * Seven of the eight dimensions are deterministic. Answerability needs an LLM
 * judge and reports "skipped" without one — rendered as an absence rather than a
 * zero, because an unconfigured environment must not read as an unready domain.
 */

const STATUS_BAR: Record<string, string> = {
  ok: "bg-green-500",
  warn: "bg-amber-500",
  fail: "bg-red-500",
  skipped: "bg-gray-300 dark:bg-gray-700",
};

const SEVERITY_STYLES: Record<string, string> = {
  ok: "border-gray-200 dark:border-gray-800",
  warn: "border-amber-300 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20",
  fail: "border-red-300 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20",
};

function DimensionRow({ dimension }: { dimension: ReadinessDimension }) {
  const skipped = dimension.score === null;
  return (
    <div className="space-y-1 py-2">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium">{dimension.label}</span>
        <span
          className={cn(
            "text-sm tabular-nums",
            skipped && "text-gray-400 dark:text-gray-500"
          )}
        >
          {skipped ? "not scored" : Math.round(dimension.score as number)}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
        <div
          className={cn("h-full rounded-full transition-all", STATUS_BAR[dimension.status])}
          style={{ width: skipped ? "100%" : `${Math.max(2, dimension.score as number)}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {dimension.detail}
        {dimension.fix && (dimension.status === "fail" || dimension.status === "warn") && (
          <span className="block text-gray-400 dark:text-gray-500">{dimension.fix}</span>
        )}
      </p>
    </div>
  );
}

export function DomainReadinessPanel({ slug }: { slug: string }) {
  const [card, setCard] = useState<ReadinessCard | null>(null);
  const [drift, setDrift] = useState<DriftSignal[]>([]);
  const [map, setMap] = useState<KnowledgeMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [readiness, signals, knowledge] = await Promise.all([
        api.getReadiness(slug),
        api.getDomainDrift(slug),
        api.getKnowledgeMap(slug),
      ]);
      setCard(readiness);
      setDrift(signals);
      setMap(knowledge);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading && !card) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Scoring {slug}…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-xl font-semibold",
                card?.ready
                  ? "bg-green-100 text-green-700 dark:bg-green-950/50 dark:text-green-300"
                  : "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
              )}
            >
              {card?.grade ?? "—"}
            </div>
            <div>
              <p className="font-medium">
                {card?.ready ? "Ready to build on" : "Not ready to build on"}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Overall {card?.overall === null ? "n/a" : Math.round(card?.overall ?? 0)} —
                could a new teammate ship from this?
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => void refresh()}>
            <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", loading && "animate-spin")} />
            Rescore
          </Button>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-x-8 sm:grid-cols-2">
          {(card?.dimensions ?? []).map((dimension) => (
            <DimensionRow key={dimension.key} dimension={dimension} />
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
        <div>
          <h3 className="font-medium">Drift</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Template, tracked docs, and the review backlog — the same question
            asked of three corpora.
          </p>
        </div>
        <div className="space-y-2">
          {drift.map((signal) => (
            <div
              key={signal.key}
              className={cn("rounded-md border px-3 py-2", SEVERITY_STYLES[signal.severity])}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-sm font-medium">
                  {signal.severity === "ok" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : signal.severity === "warn" ? (
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                  ) : (
                    <CircleSlash className="h-4 w-4 text-red-600" />
                  )}
                  {signal.label}
                </span>
                <span className="text-sm tabular-nums text-gray-500 dark:text-gray-400">
                  {signal.count}
                  {signal.total ? ` / ${signal.total}` : ""}
                </span>
              </div>
              <p className="mt-0.5 pl-6 text-xs text-gray-500 dark:text-gray-400">
                {signal.detail}
                {signal.severity !== "ok" && signal.fix && (
                  <span className="block text-gray-400 dark:text-gray-500">{signal.fix}</span>
                )}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
        <div>
          <h3 className="font-medium">Knowledge map</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            How knowledge reached this domain. Staleness travels forward, so a
            source that moved marks everything built from it.
          </p>
        </div>
        {map && <KnowledgeFlowMap map={map} />}
      </div>
    </div>
  );
}
