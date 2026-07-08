import { useCallback, useEffect, useMemo, useState } from "react";
import { Lightbulb, ChevronLeft, ChevronRight, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentEvent, EditableStory, IdeateAgent, JiraMeta, PushResult, Story } from "./ideate/types";
import { newStory } from "./ideate/types";
import { runAgent } from "./ideate/agentStream";
import { StepScope } from "./ideate/StepScope";
import { StepGather } from "./ideate/StepGather";
import { StepDraft } from "./ideate/StepDraft";
import { StepReview } from "./ideate/StepReview";
import { StepPush } from "./ideate/StepPush";

type Toast = { type: "success" | "error"; message: string };
const STEPS = ["Scope", "Gather", "Draft", "Review", "Push"] as const;

let _sid = 0;
const nextId = () => `s${Date.now()}_${_sid++}`;

export function Ideate() {
  const [step, setStep] = useState(0);
  const [maxStep, setMaxStep] = useState(0);

  const [context, setContext] = useState("");
  const [count, setCount] = useState(5);
  const [stories, setStories] = useState<EditableStory[]>([]);
  const [source, setSource] = useState<"llm" | "heuristic" | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [searchSource, setSearchSource] = useState<"glean" | "confluence">("glean");
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);

  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const [agentRunning, setAgentRunning] = useState(false);
  const [availableAgents, setAvailableAgents] = useState<IdeateAgent[]>([]);
  const [selectedAgentPaths, setSelectedAgentPaths] = useState<string[]>([]);

  const [jira, setJira] = useState<{ configured: boolean; projects: string[] } | null>(null);
  const [project, setProject] = useState("");
  const [meta, setMeta] = useState<JiraMeta | null>(null);
  const [pushing, setPushing] = useState(false);
  const [pushResults, setPushResults] = useState<Record<string, PushResult>>({});
  const [auditRefresh, setAuditRefresh] = useState(0);

  const [toast, setToast] = useState<Toast | null>(null);
  const showToast = useCallback((t: Toast) => {
    setToast(t);
    window.setTimeout(() => setToast(null), 3500);
  }, []);

  const goto = (i: number) => {
    setStep(i);
    setMaxStep((m) => Math.max(m, i));
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/ideate/jira-status");
        if (res.ok) {
          const d = await res.json();
          setJira(d);
          if (d.projects?.length) setProject(d.projects[0]);
        }
      } catch {
        /* non-fatal */
      }
    })();
    (async () => {
      try {
        const res = await fetch("/api/ideate/agents");
        if (res.ok) setAvailableAgents((await res.json()).agents ?? []);
      } catch {
        /* non-fatal */
      }
    })();
  }, []);

  const selectedAgents = useMemo(
    () => availableAgents.filter((a) => selectedAgentPaths.includes(a.path)),
    [availableAgents, selectedAgentPaths]
  );
  const toggleAgent = (path: string) =>
    setSelectedAgentPaths((prev) =>
      prev.includes(path) ? prev.filter((p) => p !== path) : [...prev, path]
    );

  // Fetch createmeta whenever the project changes.
  useEffect(() => {
    if (!project) {
      setMeta(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/ideate/jira-meta?project=${encodeURIComponent(project)}`);
        if (res.ok && !cancelled) setMeta(await res.json());
      } catch {
        /* non-fatal */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [project]);

  const runSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch("/api/ideate/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: searchSource, query: searchQuery }),
      });
      const data = await res.json();
      if (res.ok && data.text) {
        setContext((c) => (c ? `${c}\n\n--- ${searchSource}: ${searchQuery} ---\n${data.text}` : data.text));
        showToast({ type: "success", message: `Added ${data.chars} chars from ${searchSource}` });
      } else {
        showToast({ type: "error", message: data.detail || "No results from " + searchSource });
      }
    } catch {
      showToast({ type: "error", message: "Search failed" });
    } finally {
      setSearching(false);
    }
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/ideate/upload", { method: "POST", body: fd });
      const data = await res.json();
      if (res.ok && data.text) {
        setContext((c) => (c ? `${c}\n\n--- ${file.name} ---\n${data.text}` : data.text));
        showToast({ type: "success", message: `Added ${data.chars} chars from ${file.name}` });
      } else {
        showToast({ type: "error", message: data.detail || "Upload failed" });
      }
    } catch {
      showToast({ type: "error", message: "Upload failed" });
    } finally {
      setUploading(false);
    }
  };

  const draft = async () => {
    if (!context.trim()) {
      showToast({ type: "error", message: "Gather some requirements first" });
      return;
    }
    setDrafting(true);
    try {
      const res = await fetch("/api/ideate/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context, count }),
      });
      const data = await res.json();
      if (res.ok) {
        setSource(data.source);
        setStories(
          (data.stories as Story[]).map((s) => ({ ...newStory(s), ...s, _id: nextId(), keep: true }))
        );
        goto(3);
      } else {
        showToast({ type: "error", message: data.detail || "Draft failed" });
      }
    } catch {
      showToast({ type: "error", message: "Draft failed" });
    } finally {
      setDrafting(false);
    }
  };

  const pushStories = async (subset: EditableStory[]) => {
    if (!project) {
      showToast({ type: "error", message: "Pick a Jira project (Scope step)" });
      return;
    }
    if (!subset.length) {
      showToast({ type: "error", message: "Nothing to push" });
      return;
    }
    setPushing(true);
    try {
      const res = await fetch("/api/ideate/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_key: project,
          stories: subset.map(({ _id, keep, ...s }) => s),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        const merged: Record<string, PushResult> = { ...pushResults };
        subset.forEach((s, i) => {
          merged[s._id] = data.results[i];
        });
        setPushResults(merged);
        setAuditRefresh((n) => n + 1);
        showToast({ type: "success", message: `Created ${data.created} of ${subset.length}` });
      } else {
        showToast({ type: "error", message: data.detail || "Push failed" });
      }
    } catch {
      showToast({ type: "error", message: "Push failed" });
    } finally {
      setPushing(false);
    }
  };

  const runAgentGather = async () => {
    if (!context.trim()) {
      showToast({ type: "error", message: "Gather some requirements first" });
      return;
    }
    setAgentRunning(true);
    setAgentEvents([]);
    try {
      await runAgent({
        context,
        project_key: project,
        agents: selectedAgents.map((a) => ({ name: a.name, path: a.path })),
        onEvent: (ev) => {
          setAgentEvents((prev) => [...prev, ev]);
          if (ev.type === "stories" && ev.stories) {
            setSource("llm");
            setStories(
              ev.stories.map((s) => ({ ...newStory(s), ...s, _id: nextId(), keep: true }))
            );
          }
        },
      });
      goto(3);
      showToast({ type: "success", message: "Agent drafted stories" });
    } catch {
      showToast({ type: "error", message: "Agent run failed" });
    } finally {
      setAgentRunning(false);
    }
  };

  const refineStory = async (story: EditableStory, agentPath: string, instruction: string) => {
    const agent = availableAgents.find((a) => a.path === agentPath);
    if (!agent) return;
    try {
      const res = await fetch("/api/ideate/agent/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          story: (({ _id, keep, ...s }) => s)(story),
          agent: { name: agent.name, path: agent.path },
          instruction,
        }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setStories((prev) =>
          prev.map((s) => (s._id === story._id ? { ...s, ...(data.story as Story) } : s))
        );
        showToast({ type: "success", message: `Refined with ${agent.name}` });
      } else {
        showToast({ type: "error", message: data.error || "Refine failed" });
      }
    } catch {
      showToast({ type: "error", message: "Refine failed" });
    }
  };

  const kept = useMemo(() => stories.filter((s) => s.keep), [stories]);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-amber-500" />
        <h1 className="text-lg font-semibold">Ideate</h1>
      </div>

      {/* Stepper */}
      <div className="flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <button
            key={label}
            onClick={() => i <= maxStep && setStep(i)}
            disabled={i > maxStep}
            className={cn(
              "text-xs rounded-full px-3 py-1 transition-colors",
              i === step
                ? "bg-blue-600 text-white"
                : i < step
                  ? "bg-emerald-600 text-white"
                  : i <= maxStep
                    ? "bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
                    : "bg-gray-100 dark:bg-gray-900 text-gray-400 cursor-not-allowed"
            )}
          >
            {i + 1} {label}
            {i < step ? " ✓" : ""}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        {step === 0 && <StepScope projects={jira?.projects ?? []} project={project} onProject={setProject} />}
        {step === 1 && (
          <StepGather
            context={context}
            onContext={setContext}
            searchSource={searchSource}
            onSearchSource={setSearchSource}
            searchQuery={searchQuery}
            onSearchQuery={setSearchQuery}
            onSearch={runSearch}
            searching={searching}
            onUpload={uploadFile}
            uploading={uploading}
            agentEvents={agentEvents}
            agentRunning={agentRunning}
            onRunAgent={runAgentGather}
            agents={availableAgents}
            selectedAgentPaths={selectedAgentPaths}
            onToggleAgent={toggleAgent}
          />
        )}
        {step === 2 && (
          <StepDraft count={count} onCount={setCount} onDraft={draft} drafting={drafting} source={source} />
        )}
        {step === 3 && (
          <StepReview
            stories={stories}
            meta={meta}
            onStories={setStories}
            pushResults={pushResults}
            onPushOne={(s) => pushStories([s])}
            agents={availableAgents}
            onRefine={refineStory}
          />
        )}
        {step === 4 && (
          <StepPush
            project={project}
            keepCount={kept.length}
            pushing={pushing}
            onPushAll={() => pushStories(kept)}
            refreshKey={auditRefresh}
          />
        )}
      </div>

      {/* Nav */}
      <div className="flex justify-between">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4" /> Back
        </button>
        {step < STEPS.length - 1 && (
          <button
            onClick={() => goto(step + 1)}
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>

      {toast && (
        <div
          className={cn(
            "fixed bottom-6 right-6 flex items-center gap-2 rounded-lg px-4 py-2 text-sm shadow-lg",
            toast.type === "success" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
          )}
        >
          {toast.type === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {toast.message}
        </div>
      )}
    </div>
  );
}
