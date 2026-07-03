import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderKanban, CheckCircle2, XCircle, Globe, Shield, Play, Square, ScrollText, FlaskConical } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type AgentProject, type ProjectValidation, type AgentInfo } from "@/lib/api";
import { TestChat } from "@/components/TestChat";

function ValidationScore({ validation }: { validation: ProjectValidation }) {
  const pct = validation.total > 0 ? Math.round((validation.score / validation.total) * 100) : 0;
  const color =
    pct >= 80 ? "text-emerald-500" : pct >= 50 ? "text-amber-500" : "text-red-500";
  const bg =
    pct >= 80
      ? "bg-emerald-50 dark:bg-emerald-900/20"
      : pct >= 50
        ? "bg-amber-50 dark:bg-amber-900/20"
        : "bg-red-50 dark:bg-red-900/20";
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${color} ${bg}`}>
      <Shield className="h-3 w-3" />
      {pct}%
    </div>
  );
}

function ValidationChecks({ validation }: { validation: ProjectValidation }) {
  const entries = Object.entries(validation).filter(
    ([k]) => k !== "score" && k !== "total" && typeof validation[k as keyof ProjectValidation] === "boolean"
  );
  return (
    <div className="grid grid-cols-2 gap-2 mt-4">
      {entries.map(([key, val]) => (
        <div
          key={key}
          className="flex items-center gap-2 text-xs bg-gray-50 dark:bg-gray-800 rounded-lg px-3 py-2"
        >
          {val ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
          ) : (
            <XCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />
          )}
          <span className="font-mono">
            {key.replace(/^has_/, "").replace(/_/g, " ")}
          </span>
        </div>
      ))}
    </div>
  );
}

interface EvalStatusData {
  eval_ready: boolean;
  spec?: string | null;
  last_run?: { eval_name: string; overall_score: number; timestamp?: string; passed: boolean } | null;
}

/** Build → Eval gate: eval-readiness + latest run pass/fail for a project. */
function EvalGate({ path }: { path: string }) {
  const [status, setStatus] = useState<EvalStatusData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/build/eval-status?path=${encodeURIComponent(path)}`);
        if (!cancelled) setStatus(res.ok ? await res.json() : null);
      } catch {
        /* non-fatal */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [path]);

  if (loading || !status) return null;

  const base = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium";
  if (!status.eval_ready) {
    return (
      <span className={`${base} bg-gray-100 text-gray-500 dark:bg-gray-800`} title="No answer() entrypoint — not eval-ready">
        <FlaskConical className="h-3 w-3" /> Not eval-ready
      </span>
    );
  }
  if (status.last_run) {
    const pct = Math.round(status.last_run.overall_score * 100);
    return status.last_run.passed ? (
      <span className={`${base} bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300`} title={`Last eval: ${status.last_run.eval_name}`}>
        <CheckCircle2 className="h-3 w-3" /> Eval passed · {pct}%
      </span>
    ) : (
      <span className={`${base} bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300`} title={`Last eval: ${status.last_run.eval_name}`}>
        <XCircle className="h-3 w-3" /> Eval failed · {pct}%
      </span>
    );
  }
  return (
    <span className={`${base} bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300`} title="Eval-ready — no runs yet">
      <FlaskConical className="h-3 w-3" /> Eval-ready
    </span>
  );
}

export function Projects() {
  const navigate = useNavigate();
  const fetcher = useCallback(() => api.discoverProjects(), []);
  const { data: projects, loading } = usePolling<AgentProject[]>(fetcher, 10000);
  const agentsFetcher = useCallback(() => api.listAgents(), []);
  const { data: agents, refresh: refreshAgents } = usePolling<AgentInfo[]>(agentsFetcher, 5000);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const proj = selected ? projects?.find((p) => p.path === selected) : null;
  const runningAgent = proj ? agents?.find((a) => a.name === proj.name && a.status === "running") : undefined;

  const handleRun = async (p: AgentProject) => {
    setRunError(null);
    setBusy(true);
    try {
      await api.startAgent(p.name, { path: p.path });
      // Started as a background daemon — jump to the Agents page to watch it.
      navigate("/agents");
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleStop = async (name: string) => {
    setRunError(null);
    setBusy(true);
    try {
      await api.stopAgent(name);
      await refreshAgents();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleEvaluate = async (p: AgentProject) => {
    setRunError(null);
    try {
      const { spec } = await api.getAgentEvalSpec(p.path);
      navigate(`/eval?agent=${encodeURIComponent(spec)}&project=${encodeURIComponent(p.path)}`);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Agent Projects</h1>
        <p className="text-sm text-gray-500 mt-1">
          Validate all created agent projects and their configurations
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-pulse text-gray-400">Discovering projects...</div>
        </div>
      )}

      {!loading && (!projects || projects.length === 0) && (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-10 text-center">
          <FolderKanban className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No agent projects found.</p>
          <p className="text-xs text-gray-400 mt-1">
            Create one with{" "}
            <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">
              dva project create --use-case scrum-master
            </code>
          </p>
        </div>
      )}

      {projects && projects.length > 0 && (
        <div className="grid grid-cols-3 gap-6">
          {/* Left: project list */}
          <div className="col-span-1 space-y-2">
            {projects.map((p) => {
              return (
                <div
                  key={p.path}
                  onClick={() => setSelected(p.path)}
                  className={`rounded-xl border bg-white dark:bg-gray-900 p-4 cursor-pointer transition-colors ${
                    selected === p.path
                      ? "border-blue-500 dark:border-blue-400"
                      : "border-gray-200 dark:border-gray-800 hover:border-blue-300 dark:hover:border-blue-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm">{p.name}</h3>
                    {p.validation && <ValidationScore validation={p.validation} />}
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <span className="capitalize">{p.use_case || "basic"}</span>
                    <span>·</span>
                    <span>{p.framework || "adk"}</span>
                    {p.domain && (
                      <>
                        <span>·</span>
                        <span className="flex items-center gap-1 text-blue-500">
                          <Globe className="h-3 w-3" />
                          {p.domain}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right: detail */}
          <div className="col-span-2">
            {proj ? (
              <div className="space-y-4">
                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
                      <FolderKanban className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold">{proj.name}</h2>
                      <p className="text-xs text-gray-400 font-mono mt-0.5">{proj.path}</p>
                    </div>
                    <div className="ml-auto flex items-center gap-2">
                      {runningAgent ? (
                        <>
                          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                            <span className="h-2 w-2 rounded-full bg-emerald-500" />
                            Running{runningAgent.pid ? ` (PID ${runningAgent.pid})` : ""}
                          </span>
                          <button
                            onClick={() => navigate("/agents")}
                            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 transition-colors"
                          >
                            <ScrollText className="h-4 w-4" />
                            Logs
                          </button>
                        </>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-400">
                          <span className="h-2 w-2 rounded-full bg-gray-300 dark:bg-gray-600" />
                          Stopped
                        </span>
                      )}
                    </div>
                  </div>

                  {runError && (
                    <div className="mt-4 rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                      {runError}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4 mt-5 text-sm">
                    <div>
                      <span className="text-gray-400">Framework</span>
                      <p className="font-medium">{proj.framework || "adk"}</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Use Case</span>
                      <p className="font-medium capitalize">{proj.use_case || "basic"}</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Agent Type</span>
                      <p className="font-medium capitalize">{proj.agent_type}</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Domain</span>
                      <p className="font-medium">{proj.domain || "—"}</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Created</span>
                      <p className="font-medium">
                        {proj.created_at
                          ? new Date(proj.created_at).toLocaleDateString()
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400">Tools</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {proj.tools.length > 0
                          ? proj.tools.map((t) => (
                              <span
                                key={t}
                                className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs"
                              >
                                {t}
                              </span>
                            ))
                          : "—"}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center gap-2">
                    <button
                      onClick={() => handleEvaluate(proj)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50 transition-colors"
                    >
                      <FlaskConical className="h-4 w-4" />
                      Evaluate
                    </button>
                    <EvalGate key={proj.path} path={proj.path} />
                    {runningAgent ? (
                      <button
                        onClick={() => handleStop(runningAgent.name)}
                        disabled={busy}
                        className="ml-auto inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50"
                      >
                        <Square className="h-4 w-4" />
                        {busy ? "Stopping…" : "Stop"}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleRun(proj)}
                        disabled={busy}
                        className="ml-auto inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
                      >
                        <Play className="h-4 w-4" />
                        {busy ? "Starting…" : "Run agent"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Test agent (invokes answer() once per message) */}
                <TestChat key={proj.path} path={proj.path} />

                {/* Validation */}
                {proj.validation && (
                  <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">Validation Checks</h3>
                      <div className="text-sm text-gray-400">
                        {proj.validation.score} / {proj.validation.total} passed
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className="mt-3 w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          proj.validation.score === proj.validation.total
                            ? "bg-emerald-500"
                            : proj.validation.score / proj.validation.total >= 0.5
                              ? "bg-amber-500"
                              : "bg-red-500"
                        }`}
                        style={{
                          width: `${proj.validation.total > 0 ? (proj.validation.score / proj.validation.total) * 100 : 0}%`,
                        }}
                      />
                    </div>

                    <ValidationChecks validation={proj.validation} />
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-12 text-center text-gray-400">
                Select a project to view validation details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
