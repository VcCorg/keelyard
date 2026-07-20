import { useEffect, useState } from "react";
import { Cpu, Boxes, Loader2, FileText, AlertCircle, Play, RefreshCw } from "lucide-react";
import { api, type ExecutionEngineInfo, type PortableContextResult } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Execution & Context — the frontend for `keel execution` + `keel context`.
 * Lists the vendor-neutral execution engines and their status, and previews a
 * task's portable, engine-neutral context bundle (the same CONTEXT.md Devin
 * would receive) without writing files.
 */

export function ExecutionContext() {
  const [engines, setEngines] = useState<ExecutionEngineInfo[]>([]);
  const [enginesLoading, setEnginesLoading] = useState(true);

  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [jira, setJira] = useState("");
  const [domain, setDomain] = useState("");
  const [tags, setTags] = useState("");
  const [preview, setPreview] = useState<PortableContextResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEngines = () => {
    setEnginesLoading(true);
    api.listExecutionEngines()
      .then(setEngines)
      .catch(() => setEngines([]))
      .finally(() => setEnginesLoading(false));
  };
  useEffect(() => { loadEngines(); }, []);

  const runPreview = async () => {
    if (!prompt.trim()) return;
    setPreviewing(true);
    setError(null);
    setPreview(null);
    try {
      const res = await api.previewPortableContext({
        prompt: prompt.trim(),
        title: title.trim() || undefined,
        jira: jira.trim() || undefined,
        domain: domain.trim() || null,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setPreview(res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(
        msg.includes("403") || msg.toLowerCase().includes("permission")
          ? "You need the context:build permission (developer+) to render a context bundle."
          : msg
      );
    } finally {
      setPreviewing(false);
    }
  };

  const fieldCls =
    "w-full rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
          <Cpu className="h-6 w-6 text-blue-500" /> Execution &amp; Context
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Vendor-neutral execution engines and the portable context a build receives. Mirrors{" "}
          <code className="font-mono">keel execution</code> and <code className="font-mono">keel context</code>.
        </p>
      </div>

      {/* Engines */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Boxes className="h-5 w-5 text-blue-500" /> Execution engines
          </h2>
          <button onClick={loadEngines} className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            <RefreshCw className={cn("h-3.5 w-3.5", enginesLoading && "animate-spin")} /> Refresh
          </button>
        </div>
        {enginesLoading && engines.length === 0 ? (
          <p className="text-sm text-gray-400">Loading engines…</p>
        ) : engines.length === 0 ? (
          <p className="text-sm text-gray-400">No execution engines registered.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {engines.map((e) => (
              <div key={e.name} className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{e.name}</span>
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 uppercase">{e.kind}</span>
                  <span className={cn(
                    "ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full",
                    e.available
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                      : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                  )}>
                    {e.available ? "available" : "unavailable"}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1.5">{e.detail || e.description}</p>
              </div>
            ))}
          </div>
        )}
        <p className="text-[11px] text-gray-400 mt-3">
          Default engine: set <code className="font-mono">KEEL_EXECUTION_ENGINE</code> (defaults to <code className="font-mono">devin</code>).
        </p>
      </div>

      {/* Portable context preview */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <h2 className="text-base font-semibold flex items-center gap-2 mb-1">
          <FileText className="h-5 w-5 text-blue-500" /> Portable context preview
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Render a task's engine-neutral context bundle — the same CONTEXT.md any engine would
          receive. Preview only; nothing is written. The CLI's{" "}
          <code className="font-mono">keel context build</code> writes the files.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Task prompt</label>
            <textarea
              className={cn(fieldCls, "min-h-[72px] resize-y")}
              placeholder="Describe the task the engine should work on…"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Title (optional)</label>
            <input className={fieldCls} value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Jira key (optional)</label>
            <input className={fieldCls} placeholder="PROJ-123" value={jira} onChange={(e) => setJira(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Domain (optional)</label>
            <input className={fieldCls} placeholder="domain slug" value={domain} onChange={(e) => setDomain(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Tags (comma-separated)</label>
            <input className={fieldCls} placeholder="backend, urgent" value={tags} onChange={(e) => setTags(e.target.value)} />
          </div>
        </div>

        <button
          onClick={runPreview}
          disabled={!prompt.trim() || previewing}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {previewing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Render context bundle
        </button>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-300">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" /> {error}
          </div>
        )}

        {preview && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>engine: <code className="font-mono">{preview.engine}</code></span>
              <span>{preview.resolved} of {preview.item_count} context refs resolved</span>
              {preview.bundle_id && <span>bundle: <code className="font-mono">{preview.bundle_id}</code></span>}
            </div>
            <pre className="max-h-[520px] overflow-auto rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 p-4 text-[12px] leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-300">
              {preview.context_md || "(empty bundle)"}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
