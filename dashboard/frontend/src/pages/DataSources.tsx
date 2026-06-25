import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import {
  Database,
  FileText,
  GitBranch,
  Globe,
  Loader2,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Plus,
  Trash2,
  RefreshCw,
  DatabaseZap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type DataSourceInfo,
  type CreateDataSourceBody,
  type ValidationResult,
} from "@/lib/api";

const TYPE_ICON: Record<string, typeof FileText> = {
  doc: FileText,
  confluence: Globe,
  git: GitBranch,
};

function emptyForm(): CreateDataSourceBody {
  return {
    name: "",
    source_type: "doc",
    source_location: "",
    description: "",
    project: "",
    confluence_space: "",
    git_branch: "",
  };
}

export function DataSources() {
  const fetcher = useCallback(() => api.listDataSources(), []);
  const { data: sources, loading, error, refresh } = usePolling<DataSourceInfo[]>(fetcher, 15000);

  const [form, setForm] = useState<CreateDataSourceBody>(emptyForm());
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  const set = (k: keyof CreateDataSourceBody, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const validateLocation = async () => {
    if (!form.source_location.trim()) {
      setValidation(null);
      return;
    }
    setValidating(true);
    try {
      setValidation(await api.validateDataLocation(form.source_type, form.source_location));
    } catch {
      setValidation(null);
    } finally {
      setValidating(false);
    }
  };

  const submit = async () => {
    setFormError(null);
    setSubmitting(true);
    try {
      await api.createDataSource(form);
      setForm(emptyForm());
      setShowForm(false);
      refresh();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (name: string) => {
    if (!confirm(`Delete data source '${name}'?`)) return;
    try {
      await api.deleteDataSource(name);
      refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
            <Database className="h-7 w-7 text-blue-500" />
            Data Sources
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Register doc, Confluence, and git sources for KG ingestion
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
          </Button>
          <Button size="sm" onClick={() => setShowForm((s) => !s)}>
            <Plus className="h-4 w-4 mr-1.5" /> New Source
          </Button>
        </div>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name *</label>
              <Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="my-source" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Type *</label>
              <select
                value={form.source_type}
                onChange={(e) => {
                  set("source_type", e.target.value);
                  setValidation(null);
                }}
                className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="doc">doc</option>
                <option value="confluence">confluence</option>
                <option value="git">git</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Location *</label>
            <Input
              value={form.source_location}
              onChange={(e) => {
                set("source_location", e.target.value);
                setValidation(null);
              }}
              onBlur={validateLocation}
              placeholder="local path, gs:// URL, Confluence URL, or git URL"
            />
            {validating && (
              <p className="text-xs text-gray-400 mt-1 flex items-center gap-1.5">
                <Loader2 className="h-3 w-3 animate-spin" /> Validating…
              </p>
            )}
            {!validating && validation && (
              <p
                className={`text-xs mt-1 flex items-center gap-1.5 ${
                  validation.level === "error"
                    ? "text-red-500"
                    : validation.level === "warning"
                    ? "text-amber-500"
                    : "text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {validation.level === "error" ? (
                  <AlertCircle className="h-3 w-3" />
                ) : validation.level === "warning" ? (
                  <AlertTriangle className="h-3 w-3" />
                ) : (
                  <CheckCircle2 className="h-3 w-3" />
                )}
                {validation.message}
              </p>
            )}
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Project</label>
              <Input value={form.project} onChange={(e) => set("project", e.target.value)} placeholder="cwow-patient" />
            </div>
            {form.source_type === "confluence" && (
              <div>
                <label className="text-xs text-gray-500 block mb-1">Confluence Space</label>
                <Input
                  value={form.confluence_space}
                  onChange={(e) => set("confluence_space", e.target.value)}
                  placeholder="CWOW"
                />
              </div>
            )}
            {form.source_type === "git" && (
              <div>
                <label className="text-xs text-gray-500 block mb-1">Git Branch</label>
                <Input value={form.git_branch} onChange={(e) => set("git_branch", e.target.value)} placeholder="main" />
              </div>
            )}
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Description</label>
            <Input value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>

          {formError && (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="h-4 w-4" /> {formError}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={submitting || !form.name || !form.source_location || validation?.level === "error"}
              onClick={submit}
            >
              {submitting ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Plus className="h-4 w-4 mr-1.5" />}
              Create
            </Button>
          </div>
        </div>
      )}

      {/* List */}
      {loading && !sources && (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm py-3">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}
      {sources && sources.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-12 text-center">
          <Database className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="font-medium text-gray-500">No data sources yet</p>
          <p className="text-sm text-gray-400 mt-1">Create one to use it in KG Ingest by name.</p>
        </div>
      )}
      {sources && sources.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sources.map((s) => {
            const Icon = TYPE_ICON[s.type] ?? FileText;
            return (
              <div
                key={s.name}
                className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col gap-2"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <Icon className="h-4 w-4 text-blue-500 shrink-0" />
                    <span className="font-mono text-sm font-semibold truncate">{s.name}</span>
                  </div>
                  <button
                    onClick={() => remove(s.name)}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <p className="text-xs text-gray-500 break-all" title={s.location}>
                  {s.location}
                </p>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500">
                    {s.type}
                  </span>
                  {s.project && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
                      {s.project}
                    </span>
                  )}
                  {s.kg_status && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">
                      {s.kg_status}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-gray-400">
        Tip: ingest a registered source by name from{" "}
        <Link to="/kg/ingest" className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1">
          <DatabaseZap className="h-3 w-3" /> KG Ingest
        </Link>
        .
      </p>
    </div>
  );
}
