import { useCallback, useMemo, useRef, useState } from "react";
import {
  Lightbulb,
  FileUp,
  Sparkles,
  Loader2,
  Trash2,
  Search,
  BookText,
  FileText,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Story {
  title: string;
  description: string;
  acceptance_criteria: string[];
  priority: string;
  labels: string[];
}

interface EditableStory extends Story {
  _id: string;
  keep: boolean;
}

type Toast = { type: "success" | "error"; message: string };

const PRIORITIES = ["High", "Medium", "Low"];

const PRIORITY_CHIP: Record<string, string> = {
  High: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
  Medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300",
  Low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

let _sid = 0;

export function Ideate() {
  const [context, setContext] = useState("");
  const [count, setCount] = useState(5);
  const [stories, setStories] = useState<EditableStory[]>([]);
  const [drafting, setDrafting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [source, setSource] = useState<"llm" | "heuristic" | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const showToast = useCallback((t: Toast) => {
    setToast(t);
    window.setTimeout(() => setToast(null), 3500);
  }, []);

  const draft = async () => {
    if (!context.trim()) {
      showToast({ type: "error", message: "Add some requirements first" });
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
        setStories(
          (data.stories ?? []).map((s: Story) => ({ ...s, _id: `s${_sid++}`, keep: true }))
        );
        setSource(data.source);
        if (!data.stories?.length) showToast({ type: "error", message: "No stories drafted" });
      } else {
        showToast({ type: "error", message: data.detail || "Failed to draft stories" });
      }
    } catch {
      showToast({ type: "error", message: "Failed to draft stories" });
    } finally {
      setDrafting(false);
    }
  };

  const onUpload = async (file: File) => {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/ideate/upload", { method: "POST", body: form });
      const data = await res.json();
      if (res.ok) {
        setContext((c) => (c ? `${c}\n\n--- ${data.filename} ---\n${data.text}` : data.text));
        showToast({ type: "success", message: `Added ${data.chars} chars from ${data.filename}` });
      } else {
        showToast({ type: "error", message: data.detail || "Could not read file" });
      }
    } catch {
      showToast({ type: "error", message: "Upload failed" });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const update = (id: string, patch: Partial<EditableStory>) =>
    setStories((prev) => prev.map((s) => (s._id === id ? { ...s, ...patch } : s)));
  const removeStory = (id: string) => setStories((prev) => prev.filter((s) => s._id !== id));

  const keptCount = useMemo(() => stories.filter((s) => s.keep).length, [stories]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-yellow-50 dark:bg-yellow-900/20 flex items-center justify-center">
          <Lightbulb className="h-5 w-5 text-yellow-600 dark:text-yellow-300" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Ideate</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Gather requirements and draft Jira stories — review before anything is pushed.
          </p>
        </div>
      </div>

      {toast && (
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
            toast.type === "error"
              ? "border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
              : "border-green-200 bg-green-50 text-green-700 dark:border-green-900/50 dark:bg-green-900/20 dark:text-green-300"
          )}
        >
          {toast.type === "error" ? <AlertCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
          {toast.message}
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-5">
        {/* Sources */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold">1 · Gather requirements</h2>

          <div className="flex flex-wrap gap-2">
            <SourceChip icon={FileText} label="Free-text" active />
            <SourceChip icon={FileUp} label="File upload" active />
            <SourceChip icon={Search} label="Glean" pending />
            <SourceChip icon={BookText} label="Confluence" pending />
          </div>

          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={12}
            placeholder="Paste requirements, notes, meeting transcripts… or upload a document."
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-blue-500/40 font-mono"
          />

          <div className="flex items-center gap-2 flex-wrap">
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.pdf,.csv,.json"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
            />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
              Upload document
            </button>
            <div className="ml-auto flex items-center gap-2">
              <label className="text-xs text-gray-500">Stories</label>
              <input
                type="number"
                min={1}
                max={20}
                value={count}
                onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
                className="w-16 px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
              />
              <button
                onClick={draft}
                disabled={drafting || !context.trim()}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {drafting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Draft stories
              </button>
            </div>
          </div>
          <p className="text-[11px] text-gray-400">
            Glean & Confluence gathering and Jira push arrive in the next slice.
          </p>
        </div>

        {/* Review */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">2 · Review drafted stories</h2>
            {stories.length > 0 && (
              <span className="text-xs text-gray-400">
                {keptCount} of {stories.length} kept
                {source && <span className="ml-2 opacity-70">· {source === "llm" ? "LLM" : "heuristic"}</span>}
              </span>
            )}
          </div>

          {stories.length === 0 ? (
            <div className="text-center py-16 rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
              <Sparkles className="h-10 w-10 mx-auto text-gray-300 dark:text-gray-700 mb-3" />
              <p className="text-sm text-gray-500">Drafted stories will appear here for review.</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[70vh] overflow-auto pr-1">
              {stories.map((s) => (
                <StoryCard key={s._id} story={s} onChange={(p) => update(s._id, p)} onRemove={() => removeStory(s._id)} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SourceChip({
  icon: Icon,
  label,
  active,
  pending,
}: {
  icon: typeof FileText;
  label: string;
  active?: boolean;
  pending?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border",
        active
          ? "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
          : "border-gray-200 dark:border-gray-800 text-gray-400"
      )}
      title={pending ? "Coming in the next slice" : undefined}
    >
      <Icon className="h-3 w-3" />
      {label}
      {pending && <span className="opacity-60">· soon</span>}
    </span>
  );
}

function StoryCard({
  story,
  onChange,
  onRemove,
}: {
  story: EditableStory;
  onChange: (patch: Partial<EditableStory>) => void;
  onRemove: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-3 bg-white dark:bg-gray-900 transition-opacity",
        story.keep ? "border-gray-200 dark:border-gray-800" : "border-gray-200 dark:border-gray-800 opacity-50"
      )}
    >
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={story.keep}
          onChange={(e) => onChange({ keep: e.target.checked })}
          className="h-4 w-4 accent-blue-600"
          title="Keep this story"
        />
        <input
          value={story.title}
          onChange={(e) => onChange({ title: e.target.value })}
          className="flex-1 text-sm font-medium bg-transparent outline-none border-b border-transparent focus:border-gray-300 dark:focus:border-gray-700"
        />
        <select
          value={story.priority}
          onChange={(e) => onChange({ priority: e.target.value })}
          className={cn("text-[10px] font-semibold rounded px-1.5 py-0.5 outline-none", PRIORITY_CHIP[story.priority] ?? PRIORITY_CHIP.Medium)}
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button
          onClick={onRemove}
          className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
          title="Remove"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <textarea
        value={story.description}
        onChange={(e) => onChange({ description: e.target.value })}
        rows={2}
        className="mt-2 w-full text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800 px-2 py-1.5 outline-none"
      />
      {story.acceptance_criteria.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {story.acceptance_criteria.map((ac, i) => (
            <li key={i} className="text-[11px] text-gray-500 flex items-start gap-1.5">
              <CheckCircle2 className="h-3 w-3 mt-0.5 text-emerald-500 shrink-0" />
              {ac}
            </li>
          ))}
        </ul>
      )}
      {story.labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {story.labels.map((l) => (
            <span key={l} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400">
              {l}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
