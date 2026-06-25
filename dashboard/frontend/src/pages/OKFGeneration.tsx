import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileStack,
  Loader2,
  Check,
  AlertCircle,
  Play,
  RefreshCw,
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  GitFork,
  UploadCloud,
  FlaskConical,
  Trash2,
  Database,
  Search,
  Eye,
  Pencil,
  X,
  Save,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type OKFBundleInfo,
  type OKFBundleDetail,
  type IngestableDomain,
  type DevinKnowledgeList,
  type DevinKnowledgeItem,
  type DevinKnowledgeUpdate,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/* ── Streaming console (mirrors KGIngest) ─────────────────────────────────── */
function StreamConsole({
  url,
  onDone,
  label = "dva kg okf export",
}: {
  url: string | null;
  onDone?: (code: string) => void;
  label?: string;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!url) return;
    setLines([]);
    setRunning(true);
    const es = new EventSource(url);
    es.addEventListener("log", (e: MessageEvent) => setLines((p) => [...p, e.data]));
    es.addEventListener("done", (e: MessageEvent) => {
      setRunning(false);
      es.close();
      onDone?.(e.data);
    });
    es.onerror = () => {
      setRunning(false);
      es.close();
    };
    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  if (!url) return null;

  return (
    <div className="bg-gray-950 rounded-lg border border-gray-800 mt-3">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <span className="text-xs text-gray-400 font-mono">{label}</span>
        <span
          className={cn(
            "text-xs flex items-center gap-1",
            running ? "text-amber-400" : "text-emerald-400"
          )}
        >
          {running ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" /> running
            </>
          ) : (
            <>
              <Check className="h-3 w-3" /> done
            </>
          )}
        </span>
      </div>
      <div className="p-3 max-h-80 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
        {lines.map((l, i) => (
          <div key={i} className="whitespace-pre-wrap break-all leading-relaxed">
            {l}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

/* ── Bundle detail (lazy loaded on expand) ────────────────────────────────── */
function BundleDetail({ domain, source }: { domain: string; source: "authored" | "export" }) {
  const [detail, setDetail] = useState<OKFBundleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .getOKFBundle(domain, source)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setError(String(e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [domain, source]);

  if (loading)
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
      </div>
    );
  if (error)
    return (
      <div className="flex items-center gap-2 text-red-500 text-sm py-3">
        <AlertCircle className="h-4 w-4" /> {error}
      </div>
    );
  if (!detail) return null;

  const v = detail.validation;
  return (
    <div className="space-y-4 pt-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Metric label="Concepts" value={v.concepts} />
        <Metric label="Typed links" value={v.typed_links} />
        <Metric label="FREQs" value={detail.info.freqs} />
        <Metric label="Coverage gaps" value={detail.gap_count} warn={detail.gap_count > 0} />
        <Metric label="Unmapped labels" value={detail.unmapped_labels} warn={detail.unmapped_labels > 0} />
        <Metric label="Unmapped rels" value={detail.unmapped_rels} warn={detail.unmapped_rels > 0} />
        <Metric label="Quarantined triples" value={detail.quarantined_triples} warn={detail.quarantined_triples > 0} />
        <div
          className={cn(
            "rounded-lg border p-3 flex items-center gap-2",
            v.ok
              ? "border-emerald-200 bg-emerald-50 dark:border-emerald-900/40 dark:bg-emerald-900/20"
              : "border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20"
          )}
        >
          {v.ok ? (
            <ShieldCheck className="h-5 w-5 text-emerald-500" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-red-500" />
          )}
          <div>
            <p className="text-xs text-gray-500">Schema</p>
            <p className={cn("text-sm font-semibold", v.ok ? "text-emerald-600" : "text-red-600")}>
              {v.ok ? "Conformant" : `${v.error_count} errors`}
            </p>
          </div>
        </div>
      </div>

      {!v.ok && v.errors.length > 0 && (
        <div className="rounded-lg border border-red-200 dark:border-red-900/40 bg-red-50/50 dark:bg-red-900/10 p-3">
          <p className="text-xs font-semibold text-red-600 mb-1">Validation errors (first {v.errors.length})</p>
          <ul className="text-xs font-mono text-red-500 space-y-0.5 max-h-40 overflow-y-auto">
            {v.errors.map((e, i) => (
              <li key={i} className="break-all">{e}</li>
            ))}
          </ul>
        </div>
      )}

      {detail.freqs.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                {["FREQ", "Title", "Dev", "QA", "AC"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {detail.freqs.map((f) => (
                <tr key={f.freq_id}>
                  <td className="px-3 py-2 font-mono text-xs">{f.freq_id}</td>
                  <td className="px-3 py-2 max-w-[320px] truncate" title={f.title}>{f.title}</td>
                  <td className="px-3 py-2">{f.dev_gap ? <Gap /> : <Ok />}</td>
                  <td className="px-3 py-2">{f.qa_gap ? <Gap /> : <Ok />}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{f.acceptance_criteria}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={cn("text-lg font-bold", warn ? "text-amber-600" : "text-gray-900 dark:text-white")}>
        {value}
      </p>
    </div>
  );
}

const Ok = () => <Check className="h-4 w-4 text-emerald-500" />;
const Gap = () => <AlertCircle className="h-4 w-4 text-red-500" />;

/* ── Devin Knowledge management panel ─────────────────────────────────────── */
function DevinKnowledgePanel({ apiKeyPresent }: { apiKeyPresent: boolean }) {
  const [data, setData] = useState<DevinKnowledgeList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [viewing, setViewing] = useState<DevinKnowledgeItem | null>(null);
  const [editing, setEditing] = useState<DevinKnowledgeItem | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = useCallback(() => {
    if (!apiKeyPresent) return;
    setLoading(true);
    setError(null);
    api
      .listDevinKnowledge()
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [apiKeyPresent]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleOne = (id: string) =>
    setSelected((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const onBulkDelete = async () => {
    const ids = [...selected];
    if (ids.length === 0) return;
    if (!window.confirm(`Delete ${ids.length} selected Devin knowledge entr${ids.length === 1 ? "y" : "ies"}?`))
      return;
    setBulkBusy(true);
    setError(null);
    try {
      const res = await api.bulkDeleteDevinKnowledge(ids);
      const removed = new Set(res.deleted);
      setData((d) =>
        d ? { ...d, knowledge: d.knowledge.filter((k) => !removed.has(k.id)) } : d
      );
      setSelected(new Set());
      if (res.failed.length) setError(`${res.failed.length} failed: ${res.failed.map((f) => f[1]).join("; ")}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBulkBusy(false);
    }
  };

  const onDelete = async (id: string, name: string) => {
    if (!window.confirm(`Delete Devin knowledge entry "${name}"?`)) return;
    setBusyId(id);
    try {
      await api.deleteDevinKnowledge(id);
      setData((d) =>
        d ? { ...d, knowledge: d.knowledge.filter((k) => k.id !== id) } : d
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyId(null);
    }
  };

  const onMove = async (id: string, folderId: string) => {
    setBusyId(id);
    try {
      await api.moveDevinKnowledge(id, folderId || undefined);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyId(null);
    }
  };

  if (!apiKeyPresent) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-400">
        Set <code className="font-mono">DEVIN_API_KEY</code> in the backend environment to manage Devin Knowledge.
      </div>
    );
  }

  const q = filter.trim().toLowerCase();
  const rows = (data?.knowledge ?? []).filter(
    (k) =>
      !q ||
      k.name.toLowerCase().includes(q) ||
      (k.folder_name ?? "").toLowerCase().includes(q) ||
      (k.pinned_repo ?? "").toLowerCase().includes(q)
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="font-semibold text-gray-700 dark:text-gray-300">
            {data?.knowledge.length ?? 0}
          </span>{" "}
          entries ·{" "}
          <span className="font-semibold text-gray-700 dark:text-gray-300">
            {data?.folders.length ?? 0}
          </span>{" "}
          folders
        </div>
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <Button
              size="sm"
              onClick={onBulkDelete}
              disabled={bulkBusy}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              <Trash2 className={cn("h-4 w-4 mr-1.5", bulkBusy && "animate-pulse")} /> Delete selected ({selected.size})
            </Button>
          )}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter name / folder / repo"
              className="pl-7 pr-2 py-1.5 text-sm rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 w-64"
            />
          </div>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4 mr-1.5", loading && "animate-spin")} /> Refresh
          </Button>
        </div>
      </div>

      {data && data.folders.length === 0 && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50/60 dark:bg-amber-900/10 p-3 text-xs text-amber-700 dark:text-amber-300">
          No folders exist. The Devin API cannot create folders — create one named{" "}
          <code className="font-mono">&lt;domain&gt;-okf</code> in the Devin UI, then push to organize entries.
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800/50">
            <tr>
              <th className="px-3 py-2 w-8">
                <input
                  type="checkbox"
                  aria-label="Select all"
                  checked={rows.length > 0 && rows.every((k) => selected.has(k.id))}
                  ref={(el) => {
                    if (el) el.indeterminate =
                      rows.some((k) => selected.has(k.id)) && !rows.every((k) => selected.has(k.id));
                  }}
                  onChange={(e) =>
                    setSelected((s) => {
                      const next = new Set(s);
                      if (e.target.checked) rows.forEach((k) => next.add(k.id));
                      else rows.forEach((k) => next.delete(k.id));
                      return next;
                    })
                  }
                />
              </th>
              {["Name", "Folder", "Repo", "Actions"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {rows.map((k) => (
              <tr key={k.id} className={cn(busyId === k.id && "opacity-50", selected.has(k.id) && "bg-blue-50/50 dark:bg-blue-900/10")}>
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    aria-label={`Select ${k.name}`}
                    checked={selected.has(k.id)}
                    onChange={() => toggleOne(k.id)}
                  />
                </td>
                <td className="px-3 py-2 max-w-[360px] truncate" title={k.name}>
                  <button className="hover:underline text-left" onClick={() => setViewing(k)}>
                    {k.name}
                  </button>
                </td>
                <td className="px-3 py-2">
                  <select
                    value={k.parent_folder_id ?? ""}
                    onChange={(e) => onMove(k.id, e.target.value)}
                    disabled={busyId === k.id}
                    className="text-xs rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 py-1 px-1.5 max-w-[160px]"
                  >
                    <option value="">root</option>
                    {data?.folders.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-500 max-w-[220px] truncate" title={k.pinned_repo ?? ""}>
                  {k.pinned_repo ?? "-"}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setViewing(k)}
                      className="text-gray-400 hover:text-blue-500"
                      title="View"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setEditing(k)}
                      className="text-gray-400 hover:text-blue-500"
                      title="Edit"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => onDelete(k.id, k.name)}
                      disabled={busyId === k.id}
                      className="text-red-500 hover:text-red-600 disabled:opacity-50"
                      title="Delete entry"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-sm text-gray-400">
                  {data ? "No matching entries." : "—"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {viewing && <DevinViewModal item={viewing} onClose={() => setViewing(null)} />}
      {editing && (
        <DevinEditModal
          item={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}

/* ── View modal: read-only entry contents ─────────────────────────────────── */
function DevinViewModal({ item, onClose }: { item: DevinKnowledgeItem; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between p-4 border-b border-gray-100 dark:border-gray-800">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{item.name}</h3>
            <p className="text-xs text-gray-400 font-mono mt-0.5">{item.id}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto space-y-4 text-sm">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-400 mb-1">Trigger</div>
            <p className="text-gray-700 dark:text-gray-300">{item.trigger_description || "—"}</p>
          </div>
          <div className="flex gap-6">
            <div>
              <div className="text-xs font-semibold uppercase text-gray-400 mb-1">Folder</div>
              <p className="text-gray-700 dark:text-gray-300">{item.folder_name || "root"}</p>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-gray-400 mb-1">Pinned repo</div>
              <p className="text-gray-700 dark:text-gray-300 font-mono text-xs">{item.pinned_repo || "—"}</p>
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-400 mb-1">Body</div>
            <pre className="whitespace-pre-wrap break-words text-xs bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-gray-700 dark:text-gray-300">
              {item.body || "—"}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Edit modal: trigger-only or full update ──────────────────────────────── */
function DevinEditModal({
  item,
  onClose,
  onSaved,
}: {
  item: DevinKnowledgeItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(item.name);
  const [trigger, setTrigger] = useState(item.trigger_description);
  const [repo, setRepo] = useState(item.pinned_repo ?? "");
  const [body, setBody] = useState(item.body);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async (fields: DevinKnowledgeUpdate, label: string) => {
    setBusy(true);
    setErr(null);
    try {
      await api.updateDevinKnowledge(item.id, fields);
      onSaved();
    } catch (e) {
      setErr(`${label} failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Pencil className="h-4 w-4" /> Edit knowledge
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto space-y-4 text-sm">
          {err && (
            <div className="flex items-center gap-2 text-red-500">
              <AlertCircle className="h-4 w-4" /> {err}
            </div>
          )}
          <label className="block">
            <span className="text-xs font-semibold uppercase text-gray-400">Trigger description</span>
            <textarea
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2 text-sm"
            />
            <div className="mt-1.5">
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => save({ trigger_description: trigger }, "Trigger update")}
              >
                <Save className="h-3.5 w-3.5 mr-1.5" /> Update trigger only
              </Button>
            </div>
          </label>
          <label className="block">
            <span className="text-xs font-semibold uppercase text-gray-400">Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold uppercase text-gray-400">Pinned repo (repo link)</span>
            <input
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="e.g. cwow-facility-watercheck"
              className="mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2 text-sm font-mono"
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold uppercase text-gray-400">Body</span>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={14}
              className="mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2 text-xs font-mono"
            />
          </label>
        </div>
        <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-100 dark:border-gray-800">
          <Button variant="outline" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={busy}
            onClick={() =>
              save(
                { name, trigger_description: trigger, pinned_repo: repo, body },
                "Update"
              )
            }
          >
            <Save className="h-4 w-4 mr-1.5" /> Save all changes
          </Button>
        </div>
      </div>
    </div>
  );
}

export function OKFGeneration() {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [streamLabel, setStreamLabel] = useState("dva kg okf export");
  const [running, setRunning] = useState(false);
  const [mintFreqs, setMintFreqs] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [devinKey, setDevinKey] = useState(false);

  const bundlesFetcher = useCallback(() => api.listOKFBundles(), []);
  const domainsFetcher = useCallback(() => api.listIngestableDomains(), []);

  const { data: bundles, loading, refresh: refreshBundles } = usePolling<OKFBundleInfo[]>(
    bundlesFetcher,
    15000
  );
  const { data: domains } = usePolling<IngestableDomain[]>(domainsFetcher, 30000);

  useEffect(() => {
    api.getOKFDevinStatus().then((s) => setDevinKey(s.api_key_present)).catch(() => setDevinKey(false));
  }, []);

  const generate = (domain: string, product?: string) => {
    setRunning(true);
    setExpanded(null);
    setStreamLabel("dva kg okf export");
    setStreamUrl(api.okfExportStreamUrl({ domain, product, mint_freqs: mintFreqs }));
  };

  const pushDevin = (b: OKFBundleInfo, dryRun: boolean) => {
    setRunning(true);
    setStreamLabel(`dva kg okf push-devin${dryRun ? " --dry-run" : ""}`);
    setStreamUrl(
      api.okfDevinPushStreamUrl({ domain: b.domain, source: b.source, dry_run: dryRun })
    );
  };

  const onDone = () => {
    setRunning(false);
    refreshBundles();
  };

  const exportByDomain = new Map(
    (bundles ?? []).filter((b) => b.source === "export").map((b) => [b.domain, b])
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/kg"
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> KG Context
          </Link>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3 mt-2">
            <FileStack className="h-7 w-7 text-blue-500" />
            OKF Generation
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Generate schema-validated Markdown knowledge bundles from the existing graph — no re-indexing
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refreshBundles}>
          <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
        </Button>
      </div>

      {/* Generate */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Generate from a Domain</h2>
          <label className="flex items-center gap-2 text-sm text-gray-500">
            <input
              type="checkbox"
              checked={mintFreqs}
              onChange={(e) => setMintFreqs(e.target.checked)}
              className="rounded border-gray-300"
            />
            Mint FREQ concepts
          </label>
        </div>

        {domains && domains.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-8 text-center">
            <p className="font-medium text-gray-500">No domains found</p>
            <p className="text-sm text-gray-400 mt-1">
              Register a domain in{" "}
              <Link to="/onboarding" className="text-blue-600 dark:text-blue-400 hover:underline">
                Domain Onboarding
              </Link>{" "}
              and ingest it first.
            </p>
          </div>
        )}

        {domains && domains.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {domains.map((d) => {
              const b = exportByDomain.get(d.slug);
              return (
                <div
                  key={d.slug}
                  className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col gap-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="min-w-0">
                      <p className="font-mono text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
                        {d.slug}
                      </p>
                      <p className="text-xs text-gray-400">{d.product}</p>
                    </div>
                    {b ? (
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                        Bundle ({b.concepts})
                      </span>
                    ) : (
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                        No bundle
                      </span>
                    )}
                  </div>
                  <Button
                    size="sm"
                    className="w-full"
                    disabled={running}
                    onClick={() => generate(d.slug, d.product)}
                  >
                    <Play className="h-4 w-4 mr-1.5" />
                    {b ? "Re-generate" : "Generate"}
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Stream output */}
      <StreamConsole url={streamUrl} onDone={onDone} label={streamLabel} />

      {/* Existing bundles */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">OKF Bundles</h2>
          {loading && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}
        </div>

        {bundles && bundles.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-8 text-center text-gray-400 text-sm">
            No OKF bundles yet. Generate one above.
          </div>
        )}

        <div className="space-y-3">
          {bundles?.map((b) => {
            const key = `${b.source}:${b.domain}`;
            return (
            <div
              key={key}
              className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
            >
              <button
                className="w-full flex items-center justify-between text-left"
                onClick={() => setExpanded(expanded === key ? null : key)}
              >
                <div className="flex items-center gap-3">
                  <GitFork className="h-5 w-5 text-blue-400" />
                  <div>
                    <p className="font-mono text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                      {b.domain}
                      <span
                        className={cn(
                          "text-[10px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wide",
                          b.source === "export"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                            : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                        )}
                      >
                        {b.source}
                      </span>
                    </p>
                    <p className="text-xs text-gray-400">
                      {b.concepts} concepts · {b.freqs} FREQs{b.product ? ` · ${b.product}` : ""}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-blue-500">
                  {expanded === key ? "Hide" : "Details"}
                </span>
              </button>

              {/* Devin Cloud push actions */}
              <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={running}
                  onClick={() => pushDevin(b, true)}
                >
                  <FlaskConical className="h-4 w-4 mr-1.5" /> Devin dry-run
                </Button>
                <Button
                  size="sm"
                  disabled={running || !devinKey}
                  title={devinKey ? "Push to Devin Cloud Knowledge" : "Set DEVIN_API_KEY on the backend to enable live push"}
                  onClick={() => pushDevin(b, false)}
                >
                  <UploadCloud className="h-4 w-4 mr-1.5" /> Push to Devin
                </Button>
                <span className="text-xs text-gray-400">
                  {devinKey
                    ? "Pushes FREQ + Requirement concepts (idempotent)"
                    : "Live push disabled — no DEVIN_API_KEY on backend"}
                </span>
              </div>

              {expanded === key && <BundleDetail domain={b.domain} source={b.source} />}
            </div>
          );
          })}
        </div>
      </section>

      {/* Devin Knowledge management */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Database className="h-5 w-5 text-blue-400" /> Devin Knowledge
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 -mt-1">
          Inspect, move, and delete pushed Knowledge entries on Devin Cloud.
        </p>
        <DevinKnowledgePanel apiKeyPresent={devinKey} />
      </section>
    </div>
  );
}
