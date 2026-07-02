import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  FlaskConical,
  Loader2,
  AlertCircle,
  Play,
  GitCompare,
  FileBarChart,
  Plus,
  ExternalLink,
} from "lucide-react";
import * as Tabs from "@radix-ui/react-tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StreamConsole } from "@/components/StreamConsole";
import { RunHistory } from "@/components/RunHistory";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type EvalConfigInfo,
  type EvalDatasetInfo,
  type EvalRunInfo,
  type EvalMetricInfo,
  type CreateEvalConfigBody,
} from "@/lib/api";

export function Eval() {
  const configsFetcher = useCallback(() => api.listEvalConfigs(), []);
  const runsFetcher = useCallback(() => api.listEvalRuns(), []);
  const datasetsFetcher = useCallback(() => api.listEvalDatasets(), []);
  const metricsFetcher = useCallback(() => api.listEvalMetrics(), []);

  const { data: configs, error: configsError, refresh: refreshConfigs } = usePolling<EvalConfigInfo[]>(configsFetcher, 20000);
  const { data: runs, refresh: refreshRuns } = usePolling<EvalRunInfo[]>(runsFetcher, 10000);
  const { data: datasets } = usePolling<EvalDatasetInfo[]>(datasetsFetcher, 30000);
  const { data: metrics } = usePolling<EvalMetricInfo[]>(metricsFetcher, 30000);

  const [frameworks, setFrameworks] = useState<string[]>([]);
  useEffect(() => {
    api.listEvalFrameworks().then(setFrameworks).catch(() => setFrameworks([]));
  }, []);

  // Run form
  const [searchParams, setSearchParams] = useSearchParams();
  const [agent, setAgent] = useState(searchParams.get("agent") || "mock:simple");
  const [projectPath, setProjectPath] = useState<string | null>(searchParams.get("project"));
  const [selectedConfig, setSelectedConfig] = useState("");
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);
  const [reportReady, setReportReady] = useState(false);

  // Create-config form
  const emptyCfg: CreateEvalConfigBody = {
    name: "",
    dataset: "",
    metrics: ["accuracy", "f1_score"],
    framework: "builtin",
    judge: "none",
    description: "",
  };
  const [showCreate, setShowCreate] = useState(false);
  const [cfg, setCfg] = useState<CreateEvalConfigBody>(emptyCfg);
  const [metricsText, setMetricsText] = useState("accuracy,f1_score");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedConfig && configs && configs.length) setSelectedConfig(configs[0].name);
  }, [configs, selectedConfig]);

  // Check whether a report already exists for the selected config.
  useEffect(() => {
    setReportReady(false);
    if (!selectedConfig) return;
    api.evalReportExists(selectedConfig).then((r) => setReportReady(r.exists)).catch(() => {});
  }, [selectedConfig]);

  const runAgent = () => {
    if (!agent.trim() || !selectedConfig) return;
    setRunning(true);
    setStreamUrl(api.evalRunAgentStreamUrl(agent.trim(), selectedConfig, 5, projectPath || undefined));
  };
  const clearProject = () => {
    setProjectPath(null);
    const next = new URLSearchParams(searchParams);
    next.delete("project");
    next.delete("agent");
    setSearchParams(next, { replace: true });
  };
  const compare = () => {
    if (!selectedConfig) return;
    setRunning(true);
    setStreamUrl(api.evalCompareStreamUrl(selectedConfig));
  };
  const report = () => {
    if (!selectedConfig) return;
    setRunning(true);
    setStreamUrl(api.evalReportStreamUrl(selectedConfig));
  };
  const onStreamDone = () => {
    setRunning(false);
    refreshRuns();
    setHistoryKey((k) => k + 1);
    if (selectedConfig) api.evalReportExists(selectedConfig).then((r) => setReportReady(r.exists)).catch(() => {});
  };

  const submitCreate = async () => {
    setCreateError(null);
    const metrics = metricsText.split(",").map((m) => m.trim()).filter(Boolean);
    if (!cfg.name.trim() || !cfg.dataset.trim() || metrics.length === 0) {
      setCreateError("Name, dataset, and at least one metric are required.");
      return;
    }
    setCreating(true);
    try {
      await api.createEvalConfig({ ...cfg, metrics });
      setShowCreate(false);
      setCfg(emptyCfg);
      setMetricsText("accuracy,f1_score");
      setSelectedConfig(cfg.name);
      refreshConfigs();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <FlaskConical className="h-7 w-7 text-blue-500" />
          Evaluation
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Run agent evaluations, compare runs, and generate reports
        </p>
      </div>

      {/* Create config form */}
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={() => setShowCreate((s) => !s)}>
          <Plus className="h-4 w-4 mr-1.5" /> New Config
        </Button>
      </div>
      {showCreate && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create Eval Config</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name *</label>
              <Input value={cfg.name} onChange={(e) => setCfg({ ...cfg, name: e.target.value })} placeholder="support-eval" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Dataset *</label>
              <select
                value={cfg.dataset}
                onChange={(e) => setCfg({ ...cfg, dataset: e.target.value })}
                className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">Select a dataset…</option>
                {(datasets ?? []).map((d) => (
                  <option key={d.name} value={d.name}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Framework</label>
              <select
                value={cfg.framework}
                onChange={(e) => setCfg({ ...cfg, framework: e.target.value })}
                className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                {(frameworks.length ? frameworks : ["builtin", "ragas"]).map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Judge</label>
              <select
                value={cfg.judge}
                onChange={(e) => setCfg({ ...cfg, judge: e.target.value })}
                className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                {["none", "vertex-ai", "anthropic", "openai"].map((j) => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Metrics (comma-separated) *</label>
            <Input value={metricsText} onChange={(e) => setMetricsText(e.target.value)} placeholder="accuracy,f1_score" />
            {metrics && metrics.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {metrics.slice(0, 12).map((m) => (
                  <button
                    key={`${m.kind}:${m.name}`}
                    type="button"
                    onClick={() => {
                      const cur = metricsText.split(",").map((x) => x.trim()).filter(Boolean);
                      if (!cur.includes(m.name)) setMetricsText([...cur, m.name].join(","));
                    }}
                    className="text-xs font-mono px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                  >
                    +{m.name}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Description</label>
            <Input value={cfg.description} onChange={(e) => setCfg({ ...cfg, description: e.target.value })} />
          </div>
          {createError && (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="h-4 w-4" /> {createError}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button size="sm" disabled={creating} onClick={submitCreate}>
              {creating ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Plus className="h-4 w-4 mr-1.5" />}
              Create
            </Button>
          </div>
        </div>
      )}

      {/* Run panel */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        {projectPath && (
          <div className="flex items-center gap-2 rounded-lg border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 px-3 py-2 text-sm text-blue-700 dark:text-blue-300">
            <FlaskConical className="h-4 w-4 shrink-0" />
            <span className="truncate">
              Evaluating agent project <span className="font-mono">{projectPath}</span> — its <span className="font-mono">src/</span> is added to PYTHONPATH.
            </span>
            <button onClick={clearProject} className="ml-auto text-xs font-medium hover:underline shrink-0">
              Clear
            </button>
          </div>
        )}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Eval config</label>
            <select
              value={selectedConfig}
              onChange={(e) => setSelectedConfig(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Select a config…</option>
              {(configs ?? []).map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} · {c.framework}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Agent spec</label>
            <Input value={agent} onChange={(e) => setAgent(e.target.value)} placeholder="module:func or mock:simple" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2 justify-end items-center">
          {reportReady && (
            <a
              href={api.evalReportViewUrl(selectedConfig)}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1.5 mr-auto"
            >
              <ExternalLink className="h-4 w-4" /> View latest report
            </a>
          )}
          <Button variant="outline" size="sm" disabled={running || !selectedConfig} onClick={compare}>
            <GitCompare className="h-4 w-4 mr-1.5" /> Compare
          </Button>
          <Button variant="outline" size="sm" disabled={running || !selectedConfig} onClick={report}>
            <FileBarChart className="h-4 w-4 mr-1.5" /> Report
          </Button>
          <Button size="sm" disabled={running || !selectedConfig || !agent.trim()} onClick={runAgent}>
            {running ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Play className="h-4 w-4 mr-1.5" />}
            Run Agent
          </Button>
        </div>
        <StreamConsole url={streamUrl} title="dva eval" onDone={onStreamDone} />
      </div>

      {configsError && (
        <div className="flex items-center gap-2 text-red-500 text-sm">
          <AlertCircle className="h-4 w-4" /> {configsError}
        </div>
      )}

      {/* Tabs: runs / configs / datasets / metrics */}
      <Tabs.Root defaultValue="runs">
        <Tabs.List className="flex gap-1 border-b border-gray-200 dark:border-gray-800 mb-4">
          {[
            { value: "runs", label: `Runs${runs ? ` (${runs.length})` : ""}` },
            { value: "configs", label: `Configs${configs ? ` (${configs.length})` : ""}` },
            { value: "datasets", label: `Datasets${datasets ? ` (${datasets.length})` : ""}` },
            { value: "metrics", label: `Metrics${metrics ? ` (${metrics.length})` : ""}` },
          ].map(({ value, label }) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className="px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent -mb-px
                         data-[state=active]:border-blue-600 data-[state=active]:text-blue-700
                         dark:data-[state=active]:text-blue-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* Runs */}
        <Tabs.Content value="runs">
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  {["Eval", "Agent", "Framework", "Rows", "Overall", "When"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {runs && runs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-gray-400 text-sm">
                      No eval runs yet.
                    </td>
                  </tr>
                )}
                {runs?.map((r) => (
                  <tr key={r.eval_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
                    <td className="px-4 py-3 font-medium">{r.eval_name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.agent}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{r.framework}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{r.num_rows}</td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-sm font-semibold text-blue-600 dark:text-blue-400">
                        {(r.overall_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {r.timestamp ? new Date(r.timestamp).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Tabs.Content>

        {/* Configs */}
        <Tabs.Content value="configs">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(configs ?? []).map((c) => (
              <div key={c.name} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
                <p className="font-semibold">{c.name}</p>
                <p className="text-xs text-gray-400 mt-0.5">dataset: {c.dataset}</p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500">{c.framework}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500">judge: {c.judge}</span>
                  {c.metrics.map((m) => (
                    <span key={m} className="text-xs px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {configs && configs.length === 0 && (
              <p className="text-sm text-gray-400">No eval configs. Create one with <code className="font-mono">dva eval create</code>.</p>
            )}
          </div>
        </Tabs.Content>

        {/* Datasets */}
        <Tabs.Content value="datasets">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(datasets ?? []).map((d) => (
              <div key={d.name} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
                <p className="font-semibold font-mono text-sm">{d.name}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {d.versions.length} version{d.versions.length !== 1 ? "s" : ""} · latest v{d.latest ?? "—"}
                </p>
              </div>
            ))}
            {datasets && datasets.length === 0 && (
              <p className="text-sm text-gray-400">No datasets registered.</p>
            )}
          </div>
        </Tabs.Content>

        {/* Metrics */}
        <Tabs.Content value="metrics">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(metrics ?? []).map((m) => (
              <div key={`${m.kind}:${m.name}`} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
                <div className="flex items-center justify-between">
                  <p className="font-semibold font-mono text-sm">{m.name}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    m.kind === "custom"
                      ? "bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-500"
                  }`}>
                    {m.kind}
                  </span>
                </div>
                {m.description && <p className="text-xs text-gray-400 mt-1 line-clamp-2">{m.description}</p>}
              </div>
            ))}
          </div>
          {frameworks.length > 0 && (
            <p className="text-xs text-gray-400 mt-4">Frameworks: {frameworks.join(", ")}</p>
          )}
        </Tabs.Content>
      </Tabs.Root>

      <RunHistory kind="eval" refreshKey={historyKey} title="Eval Run History" />
    </div>
  );
}
