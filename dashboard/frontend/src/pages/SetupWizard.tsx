import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Check, Circle, Wrench, Rocket, Loader2, RefreshCw, Activity,
  AlertTriangle, ChevronRight, Stethoscope,
} from "lucide-react";
import { useSetup } from "@/context/SetupContext";
import { api, type DoctorReport, type DoctorStatus, type SetupItem } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * First-run setup wizard — a guided, ordered path through the same `keel init`
 * steps the SetupPanel exposes, plus a `keel doctor` health panel so a new user
 * can self-diagnose. It doesn't re-implement the config forms: each step's
 * "Configure" opens the global SetupPanel modal (single source of truth).
 */

type Step = {
  id: string;
  title: string;
  blurb: string;
  keys: string[];      // setup-item keys that belong to this step
  optional?: boolean;  // does not block "ready"
};

const STEPS: Step[] = [
  {
    id: "workspace",
    title: "Workspace",
    blurb: "Where Keel reads code and writes docs. Required before onboarding.",
    keys: ["workspaces"],
  },
  {
    id: "llm",
    title: "LLM provider",
    blurb:
      "Pick how Keel runs models: Vertex AI, a local runtime (Ollama/LM Studio), or the " +
      "downloadable built-in model. With none configured, a deterministic test-mode answers.",
    keys: ["vertex_ai", "local_model", "builtin_model"],
  },
  {
    id: "knowledge",
    title: "Knowledge store",
    blurb: "Neo4j powers the Knowledge Graph (ingest, OKF export, graph viewers). Optional.",
    keys: ["neo4j"],
    optional: true,
  },
  {
    id: "integrations",
    title: "Integrations",
    blurb: "Connect Devin, Glean, Jira, Bitbucket and Confluence. All optional.",
    keys: ["devin", "glean", "jira", "bitbucket", "confluence"],
    optional: true,
  },
];

function stepItems(items: SetupItem[], step: Step): SetupItem[] {
  return step.keys.map((k) => items.find((i) => i.key === k)).filter(Boolean) as SetupItem[];
}

/** A step is done when every required item is configured, or (optional/any) at
 *  least one item is configured. */
function stepState(items: SetupItem[]): "done" | "partial" | "todo" {
  if (items.length === 0) return "todo";
  const required = items.filter((i) => i.required);
  if (required.length > 0) {
    return required.every((i) => i.configured) ? "done" : "todo";
  }
  const anyOn = items.some((i) => i.configured);
  return anyOn ? "done" : "todo";
}

const DOT: Record<DoctorStatus, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  fail: "bg-red-500",
  skip: "bg-gray-300 dark:bg-gray-600",
};

export function SetupWizard() {
  const { status, loading, refresh, openPanel } = useSetup();
  const navigate = useNavigate();
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [doctorLoading, setDoctorLoading] = useState(false);

  const loadDoctor = () => {
    setDoctorLoading(true);
    api.getDoctorReport()
      .then(setDoctor)
      .catch(() => setDoctor(null))
      .finally(() => setDoctorLoading(false));
  };
  useEffect(() => { loadDoctor(); }, []);
  // Re-check when returning from the config modal (status refreshes on init).
  useEffect(() => { if (status) loadDoctor(); /* eslint-disable-line */ }, [status?.items.map((i) => i.configured).join(",")]);

  const items = status?.items ?? [];
  const steps = useMemo(
    () => STEPS.map((s) => ({ step: s, its: stepItems(items, s), state: stepState(stepItems(items, s)) })),
    [items]
  );
  const doneCount = steps.filter((s) => s.step.optional || s.state === "done").length;
  const ready = !!status?.ready;

  const configure = () => { openPanel(); };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <Rocket className="h-7 w-7 text-blue-500" /> Get started with Keel
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          A quick guided setup. Work top to bottom — required steps unlock onboarding, the
          rest you can add anytime.
        </p>
      </div>

      {!status?.cli_available && !loading && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            The <code>keel</code> CLI is not available to the backend, so setup steps can't run.
            Install it (<code>./install-agentic-cli.sh</code>) and reload.
          </div>
        </div>
      )}

      {/* Overall progress */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium">
            {ready ? (
              <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                <Check className="h-4 w-4" /> All required steps complete
              </span>
            ) : (
              <span className="text-gray-600 dark:text-gray-300">
                {doneCount} of {STEPS.length} steps ready
              </span>
            )}
          </div>
          <button onClick={refresh} className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} /> Refresh
          </button>
        </div>
        <div className="mt-3 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all"
            style={{ width: `${(doneCount / STEPS.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <ol className="space-y-3">
        {steps.map(({ step, its, state }, idx) => (
          <li
            key={step.id}
            className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5"
          >
            <div className="flex items-start gap-4">
              <div
                className={cn(
                  "mt-0.5 h-8 w-8 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold",
                  state === "done"
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                    : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                )}
              >
                {state === "done" ? <Check className="h-4 w-4" /> : idx + 1}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{step.title}</h3>
                  {step.optional && (
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wide bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                      optional
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{step.blurb}</p>

                <ul className="mt-3 space-y-1.5">
                  {its.map((it) => (
                    <li key={it.key} className="flex items-center gap-2 text-sm">
                      {it.configured ? (
                        <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      ) : (
                        <Circle className="h-3.5 w-3.5 text-gray-300 dark:text-gray-600 shrink-0" />
                      )}
                      <span className={cn(it.configured ? "text-gray-700 dark:text-gray-300" : "text-gray-500")}>
                        {it.label}
                      </span>
                      <span className="text-xs text-gray-400 truncate">— {it.detail}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={configure}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <Wrench className="h-3.5 w-3.5" />
                  {state === "done" ? "Reconfigure" : "Configure"}
                  <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
                </button>
              </div>
            </div>
          </li>
        ))}
      </ol>

      {/* Environment health (keel doctor) */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-blue-500" /> Environment health
            <span className="text-xs font-normal text-gray-400">(keel doctor)</span>
          </h3>
          <button onClick={loadDoctor} className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            <RefreshCw className={cn("h-3.5 w-3.5", doctorLoading && "animate-spin")} /> Re-check
          </button>
        </div>

        {doctorLoading && !doctor && (
          <div className="py-6 flex items-center justify-center text-gray-400 text-sm">
            <Loader2 className="h-4 w-4 animate-spin mr-2" /> Running diagnostics…
          </div>
        )}
        {doctor && (
          <>
            <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-emerald-500" /> {doctor.summary.ok} ok</span>
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-amber-500" /> {doctor.summary.warn} warn</span>
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-red-500" /> {doctor.summary.fail} fail</span>
              <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600" /> {doctor.summary.skip} skip</span>
            </div>
            <div className="mt-3 space-y-3">
              {doctor.sections.filter((s) => s.results.length).map((s) => (
                <div key={s.name}>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">
                    {s.name}{s.required && <span className="ml-1 normal-case text-[10px] text-blue-500">required</span>}
                  </p>
                  <ul className="space-y-1">
                    {s.results.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className={cn("mt-1.5 inline-block w-2 h-2 rounded-full shrink-0", DOT[r.status])} />
                        <span className="text-gray-700 dark:text-gray-300 shrink-0">{r.name}</span>
                        <span className="text-xs text-gray-400">
                          {r.detail}
                          {(r.status === "fail" || r.status === "warn") && r.fix && (
                            <span className="block text-gray-500 dark:text-gray-500">↳ {r.fix}</span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Finish */}
      <div className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 p-5">
        <div className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-500" />
          {ready
            ? "You're set up — jump into the dashboard to start onboarding a domain."
            : "Finish the required steps above, then continue."}
        </div>
        <button
          onClick={() => navigate("/")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium",
            ready
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          )}
        >
          {ready ? "Go to dashboard" : "Skip for now"}
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
