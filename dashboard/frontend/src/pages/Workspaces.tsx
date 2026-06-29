import { useEffect, useMemo, useState } from "react";
import {
  Boxes,
  Building2,
  Code2,
  ExternalLink,
  FolderOpen,
  Loader2,
  Play,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamConsole } from "@/components/StreamConsole";
import {
  api,
  type DomainInfo,
  type RepoInfo,
  type WorkspaceInfo,
  type WorkspaceTarget,
} from "@/lib/api";

type PersonaId = "solutions-architect" | "tech-lead" | "dev";

const PERSONAS: {
  id: PersonaId;
  label: string;
  tier: string;
  icon: typeof Boxes;
  blurb: string;
}[] = [
  {
    id: "solutions-architect",
    label: "Solutions Architect",
    tier: "Product tier",
    icon: Building2,
    blurb:
      "Cross-domain solution design from tracker rollups. Opens the product meta-repo. No code checkout.",
  },
  {
    id: "tech-lead",
    label: "Tech Lead",
    tier: "Domain tier",
    icon: Boxes,
    blurb:
      "Federated cross-repo graph reasoning across the domain. Opens the domain meta-repo. No code checkout.",
  },
  {
    id: "dev",
    label: "Developer",
    tier: "Repo tier",
    icon: Code2,
    blurb:
      "Single-repo coding with an editable git worktree + graphify navigation.",
  },
];

const EDITOR_LABELS: Record<string, string> = {
  devin: "Devin",
  windsurf: "Windsurf",
  cursor: "Cursor",
  code: "VS Code",
};

export function Workspaces() {
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [editors, setEditors] = useState<string[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);

  const [persona, setPersona] = useState<PersonaId>("tech-lead");
  const [product, setProduct] = useState("");
  const [domain, setDomain] = useState("");
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [repo, setRepo] = useState("");
  const [editor, setEditor] = useState("");

  const [target, setTarget] = useState<WorkspaceTarget | null>(null);
  const [resolving, setResolving] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const products = useMemo(
    () => Array.from(new Set(domains.map((d) => d.product))).sort(),
    [domains]
  );

  // Initial loads.
  useEffect(() => {
    api.listDomains().then(setDomains).catch(() => setDomains([]));
    api.listEditors().then((r) => setEditors(r.editors)).catch(() => setEditors([]));
    reloadWorkspaces();
  }, []);

  const reloadWorkspaces = () => {
    api.listWorkspaces().then(setWorkspaces).catch(() => setWorkspaces([]));
  };

  // Default selections once data arrives.
  useEffect(() => {
    if (!product && products.length) setProduct(products[0]);
  }, [products, product]);

  useEffect(() => {
    if (!domain && domains.length) setDomain(domains[0].name);
  }, [domains, domain]);

  // Load repos when the domain changes (needed for the dev persona).
  useEffect(() => {
    if (!domain) {
      setRepos([]);
      return;
    }
    api
      .getDomain(domain)
      .then((d) => {
        setRepos(d.repos);
        setRepo((cur) => (d.repos.some((r) => r.repo_slug === cur) ? cur : d.repos[0]?.repo_slug ?? ""));
      })
      .catch(() => setRepos([]));
  }, [domain]);

  // Keep product in sync with the chosen domain (so SA + others stay coherent).
  const activeDomain = domains.find((d) => d.name === domain);
  useEffect(() => {
    if (persona !== "solutions-architect" && activeDomain) setProduct(activeDomain.product);
  }, [domain, persona]); // eslint-disable-line react-hooks/exhaustive-deps

  // Resolve the target folder whenever inputs change.
  useEffect(() => {
    setError(null);
    setNotice(null);
    const params: { persona: string; product?: string; domain?: string; repo?: string } = { persona };
    if (persona === "solutions-architect") {
      if (!product) return setTarget(null);
      params.product = product;
    } else if (persona === "tech-lead") {
      if (!domain) return setTarget(null);
      params.domain = domain;
    } else {
      if (!domain || !repo) return setTarget(null);
      params.domain = domain;
      params.repo = repo;
    }
    setResolving(true);
    api
      .resolveWorkspaceTarget(params)
      .then(setTarget)
      .catch((e) => {
        setTarget(null);
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => setResolving(false));
  }, [persona, product, domain, repo]);

  const reresolve = () => {
    const params: { persona: string; product?: string; domain?: string; repo?: string } = { persona };
    if (persona === "solutions-architect") params.product = product;
    else if (persona === "tech-lead") params.domain = domain;
    else {
      params.domain = domain;
      params.repo = repo;
    }
    api.resolveWorkspaceTarget(params).then(setTarget).catch(() => {});
  };

  const effectiveEditor = editor || editors[0] || undefined;

  const runSync = () => {
    setRunning(true);
    setNotice(null);
    setStreamUrl(
      api.workspaceSyncStreamUrl(domain, { persona: "tech-lead", graphify: true, editor: effectiveEditor })
    );
  };

  const runOpen = () => {
    setRunning(true);
    setNotice(null);
    setStreamUrl(
      api.workspaceOpenStreamUrl(domain, repo, { persona: "dev", editor: effectiveEditor })
    );
  };

  const onStreamDone = () => {
    setRunning(false);
    reresolve();
    reloadWorkspaces();
  };

  const openInIde = async () => {
    if (!target?.path) return;
    try {
      const res = await api.openInIde(target.path, effectiveEditor);
      setNotice(res.message);
      reloadWorkspaces();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const needsAction = target?.needs;
  const canOpenIde = !!target?.exists;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <FolderOpen className="h-7 w-7 text-blue-500" />
          Workspaces
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Open code in your IDE scoped to your persona — product, domain, or repo tier.
        </p>
      </div>

      {/* Persona picker */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PERSONAS.map((p) => {
          const Icon = p.icon;
          const active = persona === p.id;
          return (
            <button
              key={p.id}
              onClick={() => setPersona(p.id)}
              className={`text-left rounded-xl border p-4 transition ${
                active
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30 ring-1 ring-blue-500"
                  : "border-gray-200 dark:border-gray-800 hover:border-gray-300"
              }`}
            >
              <div className="flex items-center gap-2">
                <Icon className={`h-5 w-5 ${active ? "text-blue-600" : "text-gray-500"}`} />
                <span className="font-semibold text-gray-900 dark:text-white">{p.label}</span>
              </div>
              <div className="text-[11px] uppercase tracking-wide text-gray-400 mt-1">{p.tier}</div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">{p.blurb}</p>
            </button>
          );
        })}
      </div>

      {/* Context selectors */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 p-4 space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          {persona === "solutions-architect" && (
            <Field label="Product">
              <Select value={product} onChange={setProduct} options={products.map((p) => ({ value: p, label: p }))} />
            </Field>
          )}

          {(persona === "tech-lead" || persona === "dev") && (
            <Field label="Domain">
              <Select
                value={domain}
                onChange={setDomain}
                options={domains.map((d) => ({ value: d.name, label: `${d.product} · ${d.domain}` }))}
              />
            </Field>
          )}

          {persona === "dev" && (
            <Field label="Repo">
              <Select
                value={repo}
                onChange={setRepo}
                options={repos.map((r) => ({ value: r.repo_slug, label: r.repo_slug }))}
                empty="No repos linked"
              />
            </Field>
          )}

          {editors.length > 0 && (
            <Field label="Editor / Agent">
              <Select
                value={editor}
                onChange={setEditor}
                options={[
                  { value: "", label: `${EDITOR_LABELS[editors[0]] ?? editors[0]} (default)` },
                  ...editors.map((e) => ({ value: e, label: EDITOR_LABELS[e] ?? e })),
                ]}
              />
            </Field>
          )}
        </div>

        {/* Resolved target */}
        <div className="rounded-lg bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 p-3">
          {resolving ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Resolving target folder…
            </div>
          ) : target ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-400">Folder:</span>
                <code className="text-xs bg-gray-200 dark:bg-gray-800 rounded px-1.5 py-0.5 break-all">
                  {target.path ?? "—"}
                </code>
                <span
                  className={`text-[11px] px-1.5 py-0.5 rounded ${
                    target.ready
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                      : target.exists
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                      : "bg-gray-200 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                  }`}
                >
                  {target.ready ? "ready" : target.exists ? "needs setup" : "not created"}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">{target.hint}</p>

              <div className="flex flex-wrap gap-2 pt-1">
                {persona === "tech-lead" && needsAction === "sync" && (
                  <Button size="sm" onClick={runSync} disabled={running}>
                    {running ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
                    Sync (Tech Lead)
                  </Button>
                )}
                {persona === "dev" && needsAction === "open" && (
                  <Button size="sm" onClick={runOpen} disabled={running || !repo}>
                    {running ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                    Open Worktree (Developer)
                  </Button>
                )}
                {persona === "tech-lead" && needsAction !== "sync" && needsAction !== "onboard" && (
                  <Button size="sm" variant="outline" onClick={runSync} disabled={running}>
                    <RefreshCw className="h-4 w-4 mr-1" /> Re-sync graphs
                  </Button>
                )}
                <Button size="sm" variant={canOpenIde ? "default" : "outline"} onClick={openInIde} disabled={!canOpenIde}>
                  <ExternalLink className="h-4 w-4 mr-1" /> Open in IDE
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Select the inputs above to resolve a folder.</p>
          )}
        </div>

        {error && (
          <div className="rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}
        {notice && (
          <div className="rounded-md border border-emerald-300 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
            {notice}
          </div>
        )}

        <StreamConsole url={streamUrl} title="workspace setup" onDone={onStreamDone} />
      </div>

      {/* Registered workspaces */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">Active Workspaces</h2>
          <Button size="sm" variant="ghost" onClick={reloadWorkspaces}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
        </div>
        {workspaces.length === 0 ? (
          <p className="text-sm text-gray-400 p-4">No workspaces yet. Resolve a persona above and open one.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-4 py-2">Tier</th>
                  <th className="px-4 py-2">Persona</th>
                  <th className="px-4 py-2">Product</th>
                  <th className="px-4 py-2">Domain</th>
                  <th className="px-4 py-2">Repos</th>
                  <th className="px-4 py-2">Path</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {workspaces.map((w) => (
                  <tr key={w.root_path} className="border-b border-gray-100 dark:border-gray-900">
                    <td className="px-4 py-2">{w.tier}</td>
                    <td className="px-4 py-2 font-medium">{w.persona}</td>
                    <td className="px-4 py-2">{w.product ?? "—"}</td>
                    <td className="px-4 py-2">{w.domain ?? "—"}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {w.repos.length
                        ? w.repos.map((r) => `${r.slug}[${r.mode ?? "?"}]`).join(", ")
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-400 max-w-[260px] truncate" title={w.root_path}>
                      {w.root_path}
                    </td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={async () => {
                          try {
                            const res = await api.openInIde(w.root_path, effectiveEditor);
                            setNotice(res.message);
                          } catch (e) {
                            setError(e instanceof Error ? e.message : String(e));
                          }
                        }}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── small local helpers ─────────────────────────────────────────────────── */

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-gray-500 dark:text-gray-400">{label}</label>
      {children}
    </div>
  );
}

function Select({
  value,
  onChange,
  options,
  empty,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  empty?: string;
}) {
  if (options.length === 0) {
    return <div className="text-sm text-gray-400 h-10 flex items-center">{empty ?? "—"}</div>;
  }
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="flex h-10 min-w-[180px] rounded-md border border-input bg-background px-3 py-2 text-sm"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
