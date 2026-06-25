import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Search,
  Download,
  Eye,
  Server,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Plug,
  FolderGit2,
  Boxes,
  FolderKanban,
  X,
  RefreshCw,
  Settings2,
  Package,
  Bot,
  BookMarked,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useUser } from "@/context/UserContext";

interface Skill {
  name: string;
  description: string;
  tags: string[];
  mcp?: { server?: string; [k: string]: unknown } | null;
  auto_detect?: unknown;
}

interface RegistryInfo {
  exists: boolean;
  is_git_repo: boolean;
  git_remote: string | null;
  skills_count: number;
  actual_path: string | null;
}

interface IntegrationTarget {
  id: string;
  label: string;
  type: "project" | "domain" | "custom";
  path: string;
  available: boolean;
  detail: string;
}

type Toast = { type: "success" | "error"; message: string };

const TARGET_ICON: Record<string, typeof FolderKanban> = {
  project: FolderKanban,
  domain: Boxes,
  custom: FolderGit2,
};

export function Skills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [installedNames, setInstalledNames] = useState<Set<string>>(new Set());
  const [registry, setRegistry] = useState<RegistryInfo | null>(null);
  const [targets, setTargets] = useState<IntegrationTarget[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");
  const [tag, setTag] = useState("");
  const [installedOnly, setInstalledOnly] = useState(false);

  const [toast, setToast] = useState<Toast | null>(null);
  const [viewSkill, setViewSkill] = useState<{ skill: Skill; content: string } | null>(null);
  const [integrateSkill, setIntegrateSkill] = useState<Skill | null>(null);
  const [devinKeyPresent, setDevinKeyPresent] = useState(false);

  const { user } = useUser();
  const isAdmin = user.role === "admin";

  const showToast = useCallback((t: Toast) => {
    setToast(t);
    window.setTimeout(() => setToast(null), 4000);
  }, []);

  const loadSkills = useCallback(async () => {
    try {
      const res = await fetch("/api/skills/list");
      const data = await res.json();
      setSkills(data.skills ?? []);
    } catch {
      showToast({ type: "error", message: "Failed to load skills from registry" });
    }
  }, [showToast]);

  const loadRegistry = useCallback(async () => {
    try {
      const res = await fetch("/api/skills/registry/info");
      setRegistry(await res.json());
    } catch {
      /* non-fatal */
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInstalled = useCallback(async () => {
    try {
      const res = await fetch("/api/skills/project/.");
      if (res.ok) {
        const data = await res.json();
        setInstalledNames(new Set((data.installed_skills ?? []).map((s: Skill) => s.name)));
      }
    } catch {
      /* non-fatal */
    }
  }, []);

  const loadTargets = useCallback(async () => {
    try {
      const res = await fetch("/api/skills/targets");
      if (res.ok) {
        const data = await res.json();
        setTargets(data.targets ?? []);
      }
    } catch {
      /* non-fatal */
    }
  }, []);

  const loadDevinStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/devin/status");
      if (res.ok) {
        const data = await res.json();
        setDevinKeyPresent(!!data.api_key_present);
      }
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    loadSkills();
    loadRegistry();
    loadInstalled();
    loadTargets();
    loadDevinStatus();
  }, [loadSkills, loadRegistry, loadInstalled, loadTargets, loadDevinStatus]);

  const allTags = useMemo(() => {
    const set = new Set<string>();
    skills.forEach((s) => s.tags?.forEach((t) => set.add(t)));
    return Array.from(set).sort();
  }, [skills]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return skills.filter((s) => {
      if (installedOnly && !installedNames.has(s.name)) return false;
      if (tag && !s.tags?.includes(tag)) return false;
      if (q && !(`${s.name} ${s.description}`.toLowerCase().includes(q))) return false;
      return true;
    });
  }, [skills, search, tag, installedOnly, installedNames]);

  const openView = async (name: string) => {
    try {
      const res = await fetch(`/api/skills/show/${name}`);
      const data = await res.json();
      setViewSkill({ skill: data, content: data.content || "" });
    } catch {
      showToast({ type: "error", message: "Failed to load skill details" });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading skills...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Skills</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Browse Agent Skills and integrate them into your projects, domain repos, or Devin.
          </p>
        </div>
        <RegistryStatus registry={registry} onChanged={() => { loadRegistry(); loadSkills(); }} onToast={showToast} />
      </div>

      {/* Toast */}
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

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            placeholder="Search skills by name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-blue-500/40"
          />
        </div>
        <select
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
        >
          <option value="">All tags</option>
          {allTags.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <button
          onClick={() => setInstalledOnly((v) => !v)}
          className={cn(
            "px-3 py-2 text-sm rounded-lg border font-medium transition-colors",
            installedOnly
              ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
              : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400"
          )}
        >
          Installed only
        </button>
      </div>

      <p className="text-xs text-gray-500">
        {filtered.length} of {skills.length} skills
      </p>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
          <Package className="h-10 w-10 mx-auto text-gray-300 dark:text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">No skills match your filters.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800 overflow-hidden">
          {filtered.map((skill) => {
            const installed = installedNames.has(skill.name);
            return (
              <div
                key={skill.name}
                className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">{skill.name}</span>
                    {installed && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-green-600 dark:text-green-400">
                        <CheckCircle2 className="h-3 w-3" /> Installed
                      </span>
                    )}
                    {skill.mcp?.server && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-gray-400">
                        <Server className="h-3 w-3" /> {skill.mcp.server}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{skill.description}</p>
                  {skill.tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {skill.tags.slice(0, 5).map((t) => (
                        <span
                          key={t}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => openView(skill.name)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    <Eye className="h-3.5 w-3.5" /> View
                  </button>
                  <button
                    onClick={() => setIntegrateSkill(skill)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                  >
                    <Plug className="h-3.5 w-3.5" /> Integrate
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {viewSkill && <ViewDialog data={viewSkill} onClose={() => setViewSkill(null)} />}
      {integrateSkill && (
        <IntegrateDialog
          skill={integrateSkill}
          targets={targets}
          isAdmin={isAdmin}
          devinKeyPresent={devinKeyPresent}
          onClose={() => setIntegrateSkill(null)}
          onToast={showToast}
          onInstalled={() => loadInstalled()}
        />
      )}
    </div>
  );
}

/* ── Registry status (compact) ─────────────────────────────────────────── */

function RegistryStatus({
  registry,
  onChanged,
  onToast,
}: {
  registry: RegistryInfo | null;
  onChanged: () => void;
  onToast: (t: Toast) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("develop");

  const update = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/skills/registry/update", { method: "POST" });
      const data = await res.json();
      onToast(res.ok ? { type: "success", message: data.message } : { type: "error", message: data.detail });
      if (res.ok) onChanged();
    } finally {
      setBusy(false);
    }
  };

  const configure = async () => {
    if (!url.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(
        `/api/skills/registry/configure?bitbucket_url=${encodeURIComponent(url.trim())}&branch=${encodeURIComponent(branch)}`,
        { method: "POST" }
      );
      const data = await res.json();
      onToast(res.ok ? { type: "success", message: data.message } : { type: "error", message: data.detail });
      if (res.ok) {
        setShowConfig(false);
        setUrl("");
        onChanged();
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
          registry?.exists
            ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300"
            : "bg-gray-100 text-gray-500 dark:bg-gray-800"
        )}
        title={registry?.actual_path ?? ""}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", registry?.exists ? "bg-green-500" : "bg-gray-400")} />
        {registry?.exists ? `Registry · ${registry.skills_count} skills` : "No registry"}
      </span>
      {registry?.is_git_repo && (
        <button
          onClick={update}
          disabled={busy}
          className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-800 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          title="Update registry"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", busy && "animate-spin")} />
        </button>
      )}
      <button
        onClick={() => setShowConfig((v) => !v)}
        className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-800 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
        title="Configure registry"
      >
        <Settings2 className="h-3.5 w-3.5" />
      </button>

      {showConfig && (
        <Modal title="Configure skills registry" onClose={() => setShowConfig(false)}>
          <div className="space-y-3">
            <label className="block">
              <span className="text-xs font-medium text-gray-500">Bitbucket repository URL</span>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://bitbucket.example.com/scm/PROJECT/repo.git"
                className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-500">Branch</span>
              <input
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
              />
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowConfig(false)} className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-800">
                Cancel
              </button>
              <button
                onClick={configure}
                disabled={busy || !url.trim()}
                className="px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Configure"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

/* ── Integrate dialog ──────────────────────────────────────────────────── */

function IntegrateDialog({
  skill,
  targets,
  isAdmin,
  devinKeyPresent,
  onClose,
  onToast,
  onInstalled,
}: {
  skill: Skill;
  targets: IntegrationTarget[];
  isAdmin: boolean;
  devinKeyPresent: boolean;
  onClose: () => void;
  onToast: (t: Toast) => void;
  onInstalled: () => void;
}) {
  const [mode, setMode] = useState<"install" | "validate">("install");
  const [selected, setSelected] = useState<string>("cwd");
  const [customPath, setCustomPath] = useState("");
  const [extra, setExtra] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const resolvedPath = useMemo(() => {
    if (selected === "custom") return customPath.trim();
    return targets.find((t) => t.id === selected)?.path ?? "";
  }, [selected, customPath, targets]);

  const install = async () => {
    if (!resolvedPath) {
      onToast({ type: "error", message: "Choose a target path first" });
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/skills/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: skill.name, project_path: resolvedPath }),
      });
      const data = await res.json();
      if (res.ok) {
        onToast({ type: "success", message: `Integrated '${skill.name}' into ${resolvedPath}` });
        onInstalled();
        onClose();
      } else {
        onToast({ type: "error", message: data.detail || "Failed to integrate skill" });
      }
    } catch {
      onToast({ type: "error", message: "Failed to integrate skill" });
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/skills/validate-with-devin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_name: skill.name,
          target_path: resolvedPath || undefined,
          extra_instructions: extra.trim() || undefined,
          dry_run: !devinKeyPresent,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        onToast({ type: "error", message: data.detail || "Failed to start validation" });
        return;
      }
      if (data.dry_run) {
        onToast({ type: "success", message: "Dry-run preview created (no DEVIN_API_KEY on backend)." });
        onClose();
      } else {
        onToast({ type: "success", message: `Devin validation session ${data.session_id} started.` });
        onClose();
        if (data.session_id) {
          navigate(`/devin?session=${encodeURIComponent(data.session_id)}`);
        }
      }
    } catch {
      onToast({ type: "error", message: "Failed to start validation" });
    } finally {
      setBusy(false);
    }
  };

  const addToKnowledge = async () => {
    setBusy(true);
    try {
      const show = await fetch(`/api/skills/show/${skill.name}`);
      const detail = await show.json();
      const res = await fetch("/api/devin/knowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `skill:${skill.name}`,
          body: detail.content || skill.description,
          trigger_description: skill.description || `Use the '${skill.name}' skill.`,
        }),
      });
      const data = await res.json();
      onToast(
        res.ok
          ? { type: "success", message: `Pushed '${skill.name}' to Devin Knowledge` }
          : { type: "error", message: data.detail || "Failed to add to Devin Knowledge" }
      );
    } catch {
      onToast({ type: "error", message: "Failed to add to Devin Knowledge" });
    } finally {
      setBusy(false);
    }
  };

  const copyMcp = async () => {
    await navigator.clipboard.writeText(JSON.stringify(skill.mcp, null, 2));
    onToast({ type: "success", message: "MCP config copied to clipboard" });
  };

  return (
    <Modal title={`Integrate: ${skill.name}`} onClose={onClose}>
      {/* Mode tabs */}
      <div className="flex gap-1 p-1 mb-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm">
        <button
          onClick={() => setMode("install")}
          className={cn(
            "flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium",
            mode === "install" ? "bg-white dark:bg-gray-900 shadow-sm" : "text-gray-500"
          )}
        >
          <Download className="h-3.5 w-3.5" /> Install
        </button>
        <button
          onClick={() => setMode("validate")}
          className={cn(
            "flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium",
            mode === "validate" ? "bg-white dark:bg-gray-900 shadow-sm" : "text-gray-500"
          )}
        >
          <Bot className="h-3.5 w-3.5" /> Validate with Devin
        </button>
      </div>

      <p className="text-xs text-gray-500 mb-3">
        {mode === "install"
          ? "Choose where to install this skill."
          : "Run a Devin session that exercises this skill and returns a PASS/FAIL verdict. Pick an optional target repo for in-context validation."}
      </p>
      <div className="space-y-1.5 max-h-60 overflow-auto">
        {targets.map((t) => {
          const Icon = TARGET_ICON[t.type] ?? FolderKanban;
          const disabled = !t.available;
          return (
            <button
              key={t.id}
              disabled={disabled}
              onClick={() => setSelected(t.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg border text-left transition-colors",
                selected === t.id
                  ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/30"
                  : "border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              <Icon className="h-4 w-4 text-gray-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">{t.label}</p>
                <p className="text-[11px] text-gray-400 truncate">{t.path || t.detail}</p>
              </div>
            </button>
          );
        })}

        {/* Custom path */}
        <button
          onClick={() => setSelected("custom")}
          className={cn(
            "w-full flex items-center gap-3 px-3 py-2 rounded-lg border text-left transition-colors",
            selected === "custom"
              ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/30"
              : "border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40"
          )}
        >
          <FolderGit2 className="h-4 w-4 text-gray-500 shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">Custom path…</p>
            <p className="text-[11px] text-gray-400">Any project or repo on disk</p>
          </div>
        </button>
        {selected === "custom" && (
          <input
            autoFocus
            value={customPath}
            onChange={(e) => setCustomPath(e.target.value)}
            placeholder="/absolute/path/to/repo"
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
          />
        )}
      </div>

      {mode === "validate" && (
        <textarea
          value={extra}
          onChange={(e) => setExtra(e.target.value)}
          rows={2}
          placeholder="Optional: extra validation instructions or scenarios for Devin…"
          className="mt-2 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none"
        />
      )}
      {mode === "validate" && !devinKeyPresent && (
        <p className="mt-2 text-[11px] text-amber-600 dark:text-amber-400">
          No DEVIN_API_KEY on the backend — this will create a dry-run preview only.
        </p>
      )}

      <div className="flex items-center justify-between gap-2 pt-4 mt-3 border-t border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button
              onClick={addToKnowledge}
              disabled={busy}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
              title="Admin: push this skill into Devin Knowledge (reusable across sessions)"
            >
              <BookMarked className="h-3.5 w-3.5" /> Add to Devin Knowledge
            </button>
          )}
          {skill.mcp && (
            <button
              onClick={copyMcp}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Server className="h-3.5 w-3.5" /> Copy MCP
            </button>
          )}
        </div>
        {mode === "install" ? (
          <button
            onClick={install}
            disabled={busy || !resolvedPath}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Install here
          </button>
        ) : (
          <button
            onClick={validate}
            disabled={busy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
            {devinKeyPresent ? "Validate with Devin" : "Preview validation"}
          </button>
        )}
      </div>
    </Modal>
  );
}

/* ── View dialog ───────────────────────────────────────────────────────── */

function ViewDialog({ data, onClose }: { data: { skill: Skill; content: string }; onClose: () => void }) {
  return (
    <Modal title={data.skill.name} onClose={onClose} wide>
      <p className="text-sm text-gray-500 mb-3">{data.skill.description}</p>
      <pre className="whitespace-pre-wrap text-xs bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800 p-4 max-h-[60vh] overflow-auto">
        {data.content || "No SKILL.md content available."}
      </pre>
    </Modal>
  );
}

/* ── Modal primitive ───────────────────────────────────────────────────── */

function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div
        className={cn(
          "w-full rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-xl",
          wide ? "max-w-2xl" : "max-w-md"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <h2 className="font-semibold text-sm truncate">{title}</h2>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
