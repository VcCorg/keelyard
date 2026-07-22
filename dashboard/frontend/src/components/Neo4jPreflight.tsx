import { useCallback } from "react";
import { CheckCircle2, XCircle, Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { cn } from "@/lib/utils";

/**
 * Live Neo4j readiness — surfaces exactly WHICH piece of Neo4j readiness is
 * blocking KG ingest (driver, config, reachability, auth) so users don't
 * guess. Renders quietly when everything is OK.
 */

interface Preflight {
  driver_available: boolean;
  configured: boolean;
  reachable: boolean;
  auth_ok: boolean;
  ok: boolean;
  uri: string;
  message: string;
}

const fetchPreflight = (): Promise<Preflight> =>
  fetch("/api/kg/neo4j/preflight").then((r) => r.json());

export function Neo4jPreflight() {
  const fetcher = useCallback(fetchPreflight, []);
  const { data, loading, refresh } = usePolling<Preflight>(fetcher, 30000);

  // Silent when healthy — no need to yell at a working system.
  if (data?.ok) return null;

  const steps: { label: string; on: boolean }[] = data ? [
    { label: "Driver installed", on: data.driver_available },
    { label: "Configured", on: data.configured },
    { label: `Reachable${data.uri ? ` at ${data.uri}` : ""}`, on: data.reachable },
    { label: "Authenticated", on: data.auth_ok },
  ] : [];

  return (
    <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-4">
      <div className="flex items-start gap-2.5">
        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
              Neo4j isn't ready for KG ingest yet.
            </p>
            <button
              onClick={refresh}
              className="text-xs text-amber-700 dark:text-amber-300 hover:underline inline-flex items-center gap-1"
            >
              <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} /> Re-check
            </button>
          </div>

          {loading && !data && (
            <p className="mt-2 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking…
            </p>
          )}

          {data && (
            <>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                {steps.map((s) => (
                  <span key={s.label} className={cn(
                    "inline-flex items-center gap-1",
                    s.on ? "text-emerald-700 dark:text-emerald-400" : "text-amber-800 dark:text-amber-300"
                  )}>
                    {s.on
                      ? <CheckCircle2 className="h-3.5 w-3.5" />
                      : <XCircle className="h-3.5 w-3.5" />}
                    {s.label}
                  </span>
                ))}
              </div>
              {data.message && (
                <p className="mt-2 text-xs text-amber-900 dark:text-amber-200 whitespace-pre-line">
                  {data.message}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
