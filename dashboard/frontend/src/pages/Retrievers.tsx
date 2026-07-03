import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Search,
  Plus,
  Trash2,
  X,
  Loader2,
  Cpu,
  Database as DbIcon,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface RetrieverInstance {
  id: string;
  name: string;
  description: string;
  backend: string;
  embedding_model?: string | null;
  source?: string | null;
  created_at: string;
}

interface Backend {
  id: string;
  name: string;
  description?: string;
  type?: string | null;
}

type Toast = { type: "success" | "error"; message: string };

const BACKEND_OPTIONS = [
  { value: "faiss", label: "Vector (FAISS)" },
  { value: "fts", label: "Full-text (FTS)" },
  { value: "kg", label: "Knowledge graph" },
  { value: "hybrid", label: "Hybrid" },
];

const EMBEDDING_MODELS = ["gemini-embedding-001", "text-embedding-004"];

const BACKEND_CHIP: Record<string, string> = {
  faiss: "bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
  fts: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  kg: "bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  hybrid: "bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
};

export function Retrievers() {
  const [instances, setInstances] = useState<RetrieverInstance[]>([]);
  const [backends, setBackends] = useState<Backend[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const showToast = useCallback((t: Toast) => {
    setToast(t);
    window.setTimeout(() => setToast(null), 3500);
  }, []);

  const loadInstances = useCallback(async () => {
    const res = await fetch("/api/build/retrievers/instances");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).items ?? [];
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [inst, be] = await Promise.all([
          loadInstances(),
          fetch("/api/build/retrievers").then((r) => (r.ok ? r.json() : { items: [] })),
        ]);
        if (!cancelled) {
          setInstances(inst);
          setBackends(be.items ?? []);
        }
      } catch {
        if (!cancelled) showToast({ type: "error", message: "Failed to load retrievers" });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadInstances, showToast]);

  const refresh = useCallback(async () => {
    try {
      setInstances(await loadInstances());
    } catch {
      /* non-fatal */
    }
  }, [loadInstances]);

  const remove = useCallback(
    async (id: string) => {
      const res = await fetch(`/api/build/retrievers/instances/${id}`, { method: "DELETE" });
      if (res.ok) {
        showToast({ type: "success", message: "Retriever deleted" });
        refresh();
      } else {
        showToast({ type: "error", message: "Failed to delete retriever" });
      }
    },
    [refresh, showToast]
  );

  const counts = useMemo(() => {
    const c = { total: instances.length, faiss: 0, fts: 0 } as Record<string, number>;
    instances.forEach((i) => {
      if (i.backend === "faiss") c.faiss += 1;
      if (i.backend === "fts") c.fts += 1;
    });
    return c;
  }, [instances]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-cyan-50 dark:bg-cyan-900/30 flex items-center justify-center">
            <Search className="h-5 w-5 text-cyan-600 dark:text-cyan-300" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Retrievers</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Named semantic / full-text indexes agents can bind to for retrieval.
            </p>
          </div>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" /> New retriever
        </button>
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

      {/* Stat tiles */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total retrievers", value: counts.total },
          { label: "FAISS", value: counts.faiss },
          { label: "FTS", value: counts.fts },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Instances */}
      {loading ? (
        <div className="flex items-center justify-center h-40 text-gray-500">
          <Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading retrievers…
        </div>
      ) : instances.length === 0 ? (
        <div className="text-center py-16 rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
          <Search className="h-10 w-10 mx-auto text-gray-300 dark:text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">No retrievers yet. Create one to index a data source.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {instances.map((r) => (
            <div key={r.id} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
              <div className="flex items-start gap-2">
                <span className="font-medium text-sm truncate flex-1">{r.name}</span>
                <button
                  onClick={() => remove(r.id)}
                  className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  title="Delete retriever"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              {r.description && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{r.description}</p>}
              <div className="flex flex-wrap items-center gap-1 mt-2">
                <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium", BACKEND_CHIP[r.backend] ?? "bg-gray-100 dark:bg-gray-800 text-gray-500")}>
                  {r.backend.toUpperCase()}
                </span>
                {r.embedding_model && (
                  <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500">
                    <Cpu className="h-2.5 w-2.5" /> {r.embedding_model}
                  </span>
                )}
                {r.source && (
                  <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500">
                    <DbIcon className="h-2.5 w-2.5" /> {r.source}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Supported backends reference */}
      {backends.length > 0 && (
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2">Supported backends</h2>
          <div className="flex flex-wrap gap-2">
            {backends.map((b) => (
              <span
                key={b.id}
                title={b.description}
                className="text-xs px-2.5 py-1 rounded-full border border-gray-200 dark:border-gray-800 text-gray-500"
              >
                {b.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {createOpen && (
        <CreateRetrieverDialog
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            refresh();
            showToast({ type: "success", message: "Retriever created" });
          }}
          onError={(m) => showToast({ type: "error", message: m })}
        />
      )}
    </div>
  );
}

function CreateRetrieverDialog({
  onClose,
  onCreated,
  onError,
}: {
  onClose: () => void;
  onCreated: () => void;
  onError: (m: string) => void;
}) {
  const [name, setName] = useState("");
  const [backend, setBackend] = useState("faiss");
  const [embedding, setEmbedding] = useState(EMBEDDING_MODELS[0]);
  const [source, setSource] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const needsEmbedding = backend === "faiss" || backend === "hybrid";

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const res = await fetch("/api/build/retrievers/instances", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          backend,
          embedding_model: needsEmbedding ? embedding : null,
          source: source.trim() || null,
          description: description.trim(),
        }),
      });
      if (res.ok) {
        onCreated();
      } else {
        const data = await res.json().catch(() => ({}));
        onError(data.detail || "Failed to create retriever");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-sm">New retriever</h2>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <label className="block">
            <span className="text-xs font-medium text-gray-500">Name</span>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="docs_retriever"
              className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-blue-500/40"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-medium text-gray-500">Backend</span>
              <select
                value={backend}
                onChange={(e) => setBackend(e.target.value)}
                className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
              >
                {BACKEND_OPTIONS.map((b) => (
                  <option key={b.value} value={b.value}>
                    {b.label}
                  </option>
                ))}
              </select>
            </label>
            <label className={cn("block", !needsEmbedding && "opacity-50")}>
              <span className="text-xs font-medium text-gray-500">Embedding model</span>
              <select
                value={embedding}
                onChange={(e) => setEmbedding(e.target.value)}
                disabled={!needsEmbedding}
                className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
              >
                {EMBEDDING_MODELS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="text-xs font-medium text-gray-500">Data source (optional)</span>
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="confluence-space, gcs-bucket, …"
              className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-500">Description (optional)</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
            />
          </label>
        </div>
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300">
            Cancel
          </button>
          <button
            onClick={create}
            disabled={busy || !name.trim()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create
          </button>
        </div>
      </div>
    </div>
  );
}
