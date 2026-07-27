import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Radio,
  Play,
  Pause,
  PlayCircle,
  Trash2,
  RefreshCw,
  X,
  AlertCircle,
  CheckCircle2,
  Plus,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type TriggerInfo,
  type WatcherSpec,
  type WatcherView,
  type TestRunResult,
} from "@/lib/api";

/** Empty spec used to seed the create form + the "Wire new" flow from Agent Builder. */
function blankSpec(overrides: Partial<WatcherSpec> = {}): WatcherSpec {
  return {
    name: "",
    trigger_type: "",
    handler: { agent: "", chain: [], input: {} },
    filter: {},
    domain: "",
    enabled: true,
    poll_seconds: 0,
    description: "",
    ...overrides,
  };
}

export function Watchers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [triggers, setTriggers] = useState<TriggerInfo[]>([]);
  const [editing, setEditing] = useState<WatcherSpec | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [testResult, setTestResult] = useState<TestRunResult | null>(null);
  const [testing, setTesting] = useState(false);

  const listFetcher = useCallback(() => api.listWatchers(), []);
  const { data: watchers, refresh } = usePolling<WatcherView[]>(listFetcher, 15000);

  useEffect(() => {
    api.listTriggers().then(setTriggers).catch(() => setTriggers([]));
  }, []);

  // Deep-link: /watchers?new=1&agent=my-agent opens the form pre-filled.
  useEffect(() => {
    if (searchParams.get("new") === "1" && editing === null) {
      const agent = searchParams.get("agent") || "";
      const domain = searchParams.get("domain") || "";
      setEditing(blankSpec({ handler: { agent, chain: [], input: {} }, domain }));
    }
  }, [searchParams, editing]);

  const openCreate = () => {
    setSaveError("");
    setTestResult(null);
    setEditing(blankSpec());
  };
  const openEdit = (view: WatcherView) => {
    setSaveError("");
    setTestResult(null);
    setEditing({ ...view.spec });
  };
  const closeEditor = () => {
    setEditing(null);
    setTestResult(null);
    setSaveError("");
    // clear deep-link params
    if (searchParams.get("new")) {
      const next = new URLSearchParams(searchParams);
      next.delete("new");
      next.delete("agent");
      next.delete("domain");
      setSearchParams(next, { replace: true });
    }
  };

  const currentTrigger = useMemo(
    () => triggers.find((t) => t.name === editing?.trigger_type) || null,
    [triggers, editing?.trigger_type]
  );

  const saveSpec = async () => {
    if (!editing) return;
    setSaving(true);
    setSaveError("");
    try {
      const existing = watchers?.some((v) => v.spec.name === editing.name);
      const saved = existing
        ? await api.updateWatcher(editing)
        : await api.createWatcher(editing);
      await refresh();
      // Keep editor open so the user can Test run immediately.
      setEditing({ ...saved.spec });
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    if (!editing) return;
    if (!watchers?.some((v) => v.spec.name === editing.name)) {
      setSaveError("Save the watcher first (Test run polls the saved spec).");
      return;
    }
    setTesting(true);
    setSaveError("");
    try {
      const result = await api.testRunWatcher(editing.name);
      setTestResult(result);
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
            <Radio className="h-7 w-7 text-blue-500" />
            Watchers
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Turn agents into event-driven workflows. A watcher polls an external source
            (Bitbucket, Jira, Confluence…) and fires a handler agent when its filter matches.
            On app open, watchers do a 3-day catch-up scan for anything missed.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
          </Button>
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-1.5" /> New watcher
          </Button>
        </div>
      </div>

      {/* List */}
      <section className="space-y-2">
        {!watchers ? (
          <div className="flex justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
          </div>
        ) : watchers.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-8 text-center">
            <p className="font-medium text-gray-500">No watchers yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Create one to wire an agent to Bitbucket PR review requests.
            </p>
          </div>
        ) : (
          watchers.map((view) => (
            <WatcherRow
              key={view.spec.name}
              view={view}
              triggerLabel={triggers.find((t) => t.name === view.spec.trigger_type)?.label
                ?? view.spec.trigger_type}
              onEdit={() => openEdit(view)}
              onDelete={async () => {
                if (!confirm(`Delete watcher '${view.spec.name}'?`)) return;
                await api.deleteWatcher(view.spec.name);
                refresh();
              }}
              onToggle={async () => {
                if (view.spec.enabled) await api.pauseWatcher(view.spec.name);
                else await api.resumeWatcher(view.spec.name);
                refresh();
              }}
            />
          ))
        )}
      </section>

      {/* Editor drawer */}
      {editing !== null && (
        <div className="fixed inset-0 z-40 bg-black/40" onClick={closeEditor}>
          <div
            className="absolute right-0 top-0 h-full w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-5 py-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Radio className="h-5 w-5 text-blue-500" />
                {watchers?.some((v) => v.spec.name === editing.name) ? "Edit watcher" : "New watcher"}
              </h2>
              <button onClick={closeEditor} aria-label="Close" className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                <X className="h-5 w-5" />
              </button>
            </div>
            <WatcherForm
              spec={editing}
              triggers={triggers}
              currentTrigger={currentTrigger}
              onChange={setEditing}
            />
            <div className="border-t border-gray-200 dark:border-gray-800 px-5 py-4 flex items-center gap-2 sticky bottom-0 bg-white dark:bg-gray-900">
              <Button onClick={saveSpec} disabled={saving || !editing.name || !editing.trigger_type || !editing.handler.agent}>
                {saving ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : null}
                Save
              </Button>
              <Button variant="outline" onClick={runTest} disabled={testing}>
                {testing ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <PlayCircle className="h-4 w-4 mr-1.5" />}
                Test run
              </Button>
              {saveError && (
                <span className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {saveError}
                </span>
              )}
            </div>
            {testResult && <TestResultPanel result={testResult} />}
          </div>
        </div>
      )}
    </div>
  );
}

function WatcherRow({
  view,
  triggerLabel,
  onEdit,
  onDelete,
  onToggle,
}: {
  view: WatcherView;
  triggerLabel: string;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: () => void;
}) {
  const s = view.spec;
  const st = view.state;
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex items-center gap-4">
      <div
        className={cn(
          "h-2 w-2 rounded-full shrink-0",
          s.enabled ? (st.last_error ? "bg-amber-500" : "bg-emerald-500") : "bg-gray-400"
        )}
        title={st.last_error || (s.enabled ? "active" : "paused")}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{s.name}</span>
          {!s.enabled && (
            <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              paused
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 truncate">
          {triggerLabel} → <span className="font-mono">{s.handler.agent || "(no agent)"}</span>
          {s.domain && (<> · {s.domain}</>)}
        </div>
        <div className="text-[11px] text-gray-400 mt-0.5 truncate">
          {st.last_fired
            ? `last fired ${new Date(st.last_fired).toLocaleString()}`
            : st.last_polled
              ? `last polled ${new Date(st.last_polled).toLocaleString()}, no matches`
              : "not yet polled"}
          {st.last_error && ` · ${st.last_error}`}
        </div>
      </div>
      <button
        onClick={onToggle}
        title={s.enabled ? "Pause" : "Resume"}
        className="p-2 rounded-md text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
      >
        {s.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </button>
      <Button size="sm" variant="outline" onClick={onEdit}>Edit</Button>
      <button
        onClick={onDelete}
        title="Delete"
        className="p-2 rounded-md text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

function WatcherForm({
  spec,
  triggers,
  currentTrigger,
  onChange,
}: {
  spec: WatcherSpec;
  triggers: TriggerInfo[];
  currentTrigger: TriggerInfo | null;
  onChange: (s: WatcherSpec) => void;
}) {
  const patch = (delta: Partial<WatcherSpec>) => onChange({ ...spec, ...delta });
  const patchHandler = (delta: Partial<WatcherSpec["handler"]>) =>
    onChange({ ...spec, handler: { ...spec.handler, ...delta } });
  const patchFilter = (key: string, value: unknown) =>
    onChange({ ...spec, filter: { ...spec.filter, [key]: value } });

  return (
    <div className="p-5 space-y-5">
      {/* Identity */}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-medium text-gray-500">Name</span>
          <Input
            value={spec.name}
            onChange={(e) => patch({ name: e.target.value })}
            placeholder="pr-review-nudge"
          />
          <span className="text-[11px] text-gray-400">
            Lowercase letters, digits, hyphens. Also the filename on disk.
          </span>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-gray-500">Domain (optional)</span>
          <Input
            value={spec.domain}
            onChange={(e) => patch({ domain: e.target.value })}
            placeholder="cwow-facility"
          />
        </label>
      </div>

      {/* Trigger */}
      <div>
        <span className="text-xs font-medium text-gray-500">Trigger</span>
        <select
          value={spec.trigger_type}
          onChange={(e) => onChange({ ...spec, trigger_type: e.target.value, filter: {} })}
          className="mt-1 w-full h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 text-sm"
        >
          <option value="">Select a trigger…</option>
          {triggers.map((t) => (
            <option key={t.name} value={t.name}>
              {t.label} {t.source_mcp && `(${t.source_mcp})`}
            </option>
          ))}
        </select>
        {currentTrigger?.description && (
          <p className="text-[11px] text-gray-400 mt-1">{currentTrigger.description}</p>
        )}
      </div>

      {/* Filter (dynamic form from schema) */}
      {currentTrigger && Object.keys(currentTrigger.filter_schema).length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
          <h3 className="text-sm font-semibold">Filter</h3>
          {Object.entries(currentTrigger.filter_schema).map(([fname, field]) => (
            <FilterField
              key={fname}
              name={fname}
              field={field}
              value={spec.filter[fname]}
              onChange={(v) => patchFilter(fname, v)}
            />
          ))}
        </div>
      )}

      {/* Handler */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
        <h3 className="text-sm font-semibold">Handler</h3>
        <label className="block">
          <span className="text-xs font-medium text-gray-500">Agent name *</span>
          <Input
            value={spec.handler.agent}
            onChange={(e) => patchHandler({ agent: e.target.value })}
            placeholder="pr-triage-agent"
          />
          <span className="text-[11px] text-gray-400">
            Must exist in the agent registry. Chain (Phase 2) will run additional
            agents after this one; for now this agent is the only one launched.
          </span>
        </label>
      </div>

      {/* Cadence */}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-medium text-gray-500">Poll every (seconds)</span>
          <Input
            type="number"
            value={spec.poll_seconds || ""}
            onChange={(e) => patch({ poll_seconds: parseInt(e.target.value || "0", 10) })}
            placeholder={String(currentTrigger?.default_poll_seconds ?? 300)}
          />
          <span className="text-[11px] text-gray-400">
            Blank = trigger default ({currentTrigger?.default_poll_seconds ?? 300}s).
          </span>
        </label>
        <label className="flex items-center gap-2 mt-6">
          <input
            type="checkbox"
            checked={spec.enabled}
            onChange={(e) => patch({ enabled: e.target.checked })}
            className="h-4 w-4 rounded border-gray-300"
          />
          <span className="text-sm">Enabled</span>
        </label>
      </div>

      {/* Description */}
      <label className="block">
        <span className="text-xs font-medium text-gray-500">Description</span>
        <Input
          value={spec.description}
          onChange={(e) => patch({ description: e.target.value })}
          placeholder="Why this watcher exists"
        />
      </label>
    </div>
  );
}

function FilterField({
  name,
  field,
  value,
  onChange,
}: {
  name: string;
  field: import("@/lib/api").TriggerField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const label = (
    <div className="flex items-baseline gap-1">
      <span className="text-xs font-medium text-gray-500">
        {field.label} {field.required && <span className="text-red-500">*</span>}
      </span>
      <span className="text-[10px] text-gray-400">{name}</span>
    </div>
  );
  if (field.type === "bool") {
    return (
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300"
        />
        <span className="text-sm">{field.label}</span>
        {field.help && <span className="text-[11px] text-gray-400 ml-2">{field.help}</span>}
      </label>
    );
  }
  if (field.type === "int") {
    return (
      <label className="block">
        {label}
        <Input
          type="number"
          value={value == null ? "" : String(value)}
          onChange={(e) => onChange(e.target.value ? parseInt(e.target.value, 10) : 0)}
        />
        {field.help && <span className="text-[11px] text-gray-400">{field.help}</span>}
      </label>
    );
  }
  return (
    <label className="block">
      {label}
      <Input
        value={value == null ? "" : String(value)}
        onChange={(e) => onChange(e.target.value)}
      />
      {field.help && <span className="text-[11px] text-gray-400">{field.help}</span>}
    </label>
  );
}

function TestResultPanel({ result }: { result: TestRunResult }) {
  return (
    <div className="p-5 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950/40">
      <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
        {result.error ? (
          <>
            <AlertCircle className="h-4 w-4 text-red-500" />
            Test run failed
          </>
        ) : (
          <>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            Test run — {result.matched} match{result.matched === 1 ? "" : "es"}
          </>
        )}
      </h3>
      {result.error && <p className="text-sm text-red-500">{result.error}</p>}
      {result.events.length > 0 && (
        <ul className="text-xs space-y-1">
          {result.events.slice(0, 20).map((ev) => (
            <li key={ev.event_id} className="font-mono truncate">
              {new Date(ev.ts).toLocaleString()} · {ev.event_id}
            </li>
          ))}
        </ul>
      )}
      {result.matched === 0 && !result.error && (
        <p className="text-xs text-gray-400">
          No matches within the 3-day window. Adjust the filter or wait for new events.
        </p>
      )}
    </div>
  );
}
