import { useEffect, useRef, useState } from "react";
import {
  Boxes,
  GitBranch,
  FileText,
  Sparkles,
  FolderGit2,
  Check,
  Loader2,
  Plus,
  Trash2,
  RefreshCw,
  Pencil,
  X,
  Package,
  ShieldCheck,
  AlertTriangle,
  ClipboardCheck,
  Gauge,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  api,
  type ProductInfo,
  type DomainInfo,
  type DomainDetail,
  type BitbucketRepoCandidate,
  type ConfluencePageCandidate,
  type GovernanceInfo,
  type ExceptionInfo,
  type ScaffoldPaths,
} from "@/lib/api";
import { PersonaSkillsPanel } from "@/components/PersonaSkillsPanel";
import { DomainReviewPanel } from "@/components/DomainReviewPanel";
import { DomainReadinessPanel } from "@/components/DomainReadinessPanel";
import { OpenInIdeButton } from "@/components/OpenInIdeButton";
import { cn } from "@/lib/utils";

/* ── Streaming console (handles both `log` and `done` SSE events) ─────────── */
function StreamConsole({
  url,
  onDone,
}: {
  url: string | null;
  onDone?: (code: string) => void;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [exitCode, setExitCode] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number>(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!url) return;
    setLines([]);
    setExitCode(null);
    setElapsed(0);
    setRunning(true);
    startRef.current = Date.now();
    const es = new EventSource(url);
    es.addEventListener("log", (e: MessageEvent) =>
      setLines((p) => [...p, e.data])
    );
    es.addEventListener("done", (e: MessageEvent) => {
      setRunning(false);
      setExitCode(e.data);
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

  // Tick an elapsed-time counter while the command runs so long-running steps
  // (clones, KG ingest, doc fetches) show forward progress, not a frozen UI.
  useEffect(() => {
    if (!running) return;
    const id = setInterval(
      () => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)),
      500
    );
    return () => clearInterval(id);
  }, [running]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  if (!url) return null;

  const fmt = (s: number) =>
    s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
  const failed = exitCode !== null && exitCode !== "0";

  return (
    <div className="bg-gray-950 rounded-lg border border-gray-800 mt-3">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <span className="text-xs text-gray-400 font-mono">
          CLI output
          <span className="ml-2 text-gray-500">
            {fmt(elapsed)} · {lines.length} lines
          </span>
        </span>
        <span
          className={cn(
            "text-xs flex items-center gap-1",
            running
              ? "text-amber-400"
              : failed
              ? "text-red-400"
              : "text-emerald-400"
          )}
        >
          {running ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" /> running…
            </>
          ) : failed ? (
            <>
              <AlertTriangle className="h-3 w-3" /> failed (exit {exitCode})
            </>
          ) : (
            <>
              <Check className="h-3 w-3" /> done
            </>
          )}
        </span>
      </div>
      {/* Indeterminate progress bar while running — honest about unknown ETA. */}
      {running && (
        <div className="h-0.5 w-full overflow-hidden bg-gray-800">
          <div className="h-full w-1/3 animate-pulse bg-amber-400" />
        </div>
      )}
      <div className="p-3 max-h-72 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
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

/** A domain needs one source-control coordinate, on either host.
 *
 *  It stays required — a domain with no repository anywhere has nothing to
 *  onboard — but it stopped being Bitbucket-specific, which was blocking
 *  GitHub-hosted teams from creating a domain at all. */
function hasRepoCoordinate(form: {
  bitbucket_project: string;
  bitbucket_url: string;
  github_org: string;
  github_url: string;
}): boolean {
  return [form.bitbucket_project, form.bitbucket_url, form.github_org, form.github_url]
    .some((v) => v.trim().length > 0);
}

const STEPS = [
  { key: "product", label: "Product", icon: Package },
  { key: "domain", label: "Domain", icon: Boxes },
  { key: "repos", label: "Repos", icon: GitBranch },
  { key: "docs", label: "Docs", icon: FileText },
  { key: "skills", label: "Skills", icon: Sparkles },
  { key: "scaffold", label: "Scaffold", icon: FolderGit2 },
  // Review and Readiness come last because both read the meta-repo the
  // scaffold step creates: extraction writes its proposal there, and the
  // score is over what review put into .domain/.
  { key: "review", label: "Review", icon: ClipboardCheck },
  { key: "readiness", label: "Readiness", icon: Gauge },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

export function DomainOnboarding() {
  const [step, setStep] = useState<StepKey>("product");
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [active, setActive] = useState<DomainDetail | null>(null);
  const [activeProduct, setActiveProduct] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshLists = async () => {
    try {
      const [p, d] = await Promise.all([api.listProducts(), api.listDomains()]);
      setProducts(p);
      setDomains(d);
    } catch (e) {
      setError(String(e));
    }
  };

  const refreshActive = async (slug: string) => {
    try {
      setActive(await api.getDomain(slug));
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    refreshLists();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Domain Onboarding</h1>
        <p className="text-sm text-gray-500 mt-1">
          Drive the <code className="text-xs">keel domain</code> workflow from the UI.
          The dashboard is a thin proxy — all logic runs in the CLI core.
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const disabled =
            s.key !== "product" && s.key !== "domain" && !active;
          const isActive = step === s.key;
          return (
            <button
              key={s.key}
              disabled={disabled}
              onClick={() => setStep(s.key)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-600 text-white"
                  : disabled
                  ? "text-gray-400 cursor-not-allowed"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200"
              )}
            >
              <span className="text-xs opacity-70">{i + 1}</span>
              <Icon className="h-4 w-4" />
              {s.label}
            </button>
          );
        })}
      </div>

      {active && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Active domain:</span>
          <Badge>{active.name}</Badge>
          <span className="text-gray-400">
            {active.repo_count} repos · {active.doc_count} docs
          </span>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {step === "product" && (
        <ProductStep
          products={products}
          activeProduct={activeProduct}
          onSelectProduct={setActiveProduct}
          onChanged={refreshLists}
          onError={setError}
          onContinue={() => setStep("domain")}
        />
      )}

      {step === "domain" && (
        <DomainStep
          products={products}
          domains={domains}
          activeSlug={active?.name ?? null}
          onSelect={async (slug) => {
            await refreshActive(slug);
            setStep("repos");
          }}
          onCreated={async (slug) => {
            await refreshLists();
            await refreshActive(slug);
            setStep("repos");
          }}
          onChanged={async (deletedSlug?: string) => {
            if (deletedSlug && active?.name === deletedSlug) setActive(null);
            await refreshLists();
          }}
          onError={setError}
        />
      )}

      {step === "repos" && active && (
        <ReposStep domain={active} onChanged={() => refreshActive(active.name)} />
      )}

      {step === "docs" && active && (
        <DocsStep domain={active} onChanged={() => refreshActive(active.name)} />
      )}

      {step === "skills" && active && (
        <SkillsStep slug={active.name} product={active.product} />
      )}

      {step === "scaffold" && active && (
        <ScaffoldStep slug={active.name} product={active.product} />
      )}

      {step === "review" && active && (
        <DomainReviewPanel
          slug={active.name}
          onFinalized={() => setStep("readiness")}
        />
      )}

      {step === "readiness" && active && <DomainReadinessPanel slug={active.name} />}
    </div>
  );
}

/* ── Products management (list / create / edit / delete) ─────────────────── */
function ProductsPanel({
  products,
  onChanged,
  onError,
}: {
  products: ProductInfo[];
  onChanged: () => void;
  onError: (e: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [tags, setTags] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editDesc, setEditDesc] = useState("");
  const [editTags, setEditTags] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const [wipeMeta, setWipeMeta] = useState(false);

  const parseTags = (s: string) =>
    s.split(",").map((t) => t.trim()).filter(Boolean);

  const create = async () => {
    if (!name.trim()) {
      onError("Product name is required.");
      return;
    }
    setBusy("__create__");
    try {
      await api.createProduct({
        name: name.trim(),
        description: desc.trim() || undefined,
        tags: parseTags(tags),
      });
      setName("");
      setDesc("");
      setTags("");
      setAdding(false);
      onChanged();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const beginEdit = (p: ProductInfo) => {
    setEditing(p.name);
    setEditDesc(p.description ?? "");
    setEditTags((p.tags ?? []).join(", "));
  };

  const saveEdit = async (productName: string) => {
    setBusy(productName);
    try {
      await api.updateProduct(productName, {
        description: editDesc.trim(),
        tags: parseTags(editTags),
      });
      setEditing(null);
      onChanged();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const openConfirm = (p: ProductInfo) => {
    setEditing(null);
    setWipeMeta(false);
    setConfirmDel((cur) => (cur === p.name ? null : p.name));
  };

  const remove = async (p: ProductInfo) => {
    setBusy(p.name);
    try {
      await api.deleteProduct(p.name, { cascade: true, wipeMeta });
      setConfirmDel(null);
      setWipeMeta(false);
      onChanged();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold flex items-center gap-2">
          <Package className="h-4 w-4" /> Products ({products.length})
        </h2>
        <Button variant="outline" size="sm" onClick={() => setAdding((v) => !v)}>
          {adding ? <X className="h-4 w-4 mr-1" /> : <Plus className="h-4 w-4 mr-1" />}
          {adding ? "Cancel" : "New product"}
        </Button>
      </div>

      {adding && (
        <div className="rounded-md border border-dashed border-gray-300 dark:border-gray-700 p-3 mb-3 grid grid-cols-1 sm:grid-cols-3 gap-2 items-end">
          <div>
            <label className="text-xs text-gray-500">Name * (e.g. CWOW)</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="CWOW" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Description</label>
            <Input value={desc} onChange={(e) => setDesc(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500">Tags (comma-separated)</label>
            <div className="flex gap-2">
              <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="healthcare, gcp" />
              <Button onClick={create} disabled={busy === "__create__"}>
                {busy === "__create__" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2 max-h-72 overflow-y-auto">
        {products.length === 0 && (
          <p className="text-sm text-gray-500">No products yet. Create one to onboard domains.</p>
        )}
        {products.map((p) => (
          <div
            key={p.name}
            className="rounded-md border border-gray-200 dark:border-gray-800 px-3 py-2"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="font-medium text-sm flex items-center gap-2">
                  {p.name}
                  <Badge variant="secondary">{p.domain_count} domains</Badge>
                </div>
                {p.description && (
                  <div className="text-xs text-gray-500 truncate">{p.description}</div>
                )}
                {(p.tags?.length ?? 0) > 0 && (
                  <div className="text-xs text-gray-400 mt-0.5">{p.tags.join(", ")}</div>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => (editing === p.name ? setEditing(null) : beginEdit(p))}
                  title="Edit product"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => openConfirm(p)}
                  disabled={busy === p.name}
                  title={p.domain_count > 0 ? "Force delete product + domains" : "Remove product"}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            </div>

            {confirmDel === p.name && (
              <div className="mt-2 rounded-md border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/30 p-3 space-y-2">
                <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-300">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  <div>
                    {p.domain_count > 0 ? (
                      <>
                        This will remove <strong>{p.name}</strong> and its{" "}
                        <strong>{p.domain_count} domain(s)</strong> from the tracker.
                      </>
                    ) : (
                      <>
                        This will remove <strong>{p.name}</strong> from the tracker.
                      </>
                    )}{" "}
                    This cannot be undone.
                  </div>
                </div>
                <label className="flex items-center gap-2 text-xs text-red-700 dark:text-red-300">
                  <input
                    type="checkbox"
                    checked={wipeMeta}
                    onChange={(e) => setWipeMeta(e.target.checked)}
                  />
                  Also delete on-disk meta-repos (<code>domain-*-meta</code>, <code>product-*-meta</code>) —
                  for a clean re-onboard
                </label>
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => remove(p)}
                    disabled={busy === p.name}
                  >
                    {busy === p.name ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <Trash2 className="h-4 w-4 mr-1" />
                    )}
                    {p.domain_count > 0 ? "Force delete" : "Delete"}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setConfirmDel(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {editing === p.name && (
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 items-end">
                <div>
                  <label className="text-xs text-gray-500">Description</label>
                  <Input value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Tags (comma-separated)</label>
                  <Input value={editTags} onChange={(e) => setEditTags(e.target.value)} />
                </div>
                <Button onClick={() => saveEdit(p.name)} disabled={busy === p.name}>
                  {busy === p.name ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Check className="h-4 w-4 mr-1" />}
                  Save
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── A single existing-domain row with select / edit / delete ────────────── */
function DomainRow({
  domain,
  products,
  active,
  onSelect,
  onChanged,
  onError,
}: {
  domain: DomainInfo;
  products: ProductInfo[];
  active: boolean;
  onSelect: (slug: string) => void;
  onChanged: (deletedSlug?: string) => void;
  onError: (e: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    product: domain.product,
    description: domain.description ?? "",
    jira_project: domain.jira_project ?? "",
    bitbucket_project: domain.bitbucket_project ?? "",
    bitbucket_url: domain.bitbucket_url ?? "",
    github_org: domain.github_org ?? "",
    github_url: domain.github_url ?? "",
    confluence_space: domain.confluence_space ?? "",
    confluence_url: domain.confluence_url ?? "",
  });

  const save = async () => {
    if (!hasRepoCoordinate(form)) {
      onError("A source-control coordinate is required: a Bitbucket project key or URL, or a GitHub org or repo URL.");
      return;
    }
    setBusy(true);
    try {
      await api.updateDomain(domain.name, {
        product: form.product || undefined,
        description: form.description,
        jira_project: form.jira_project,
        bitbucket_project: form.bitbucket_project,
        bitbucket_url: form.bitbucket_url,
        github_org: form.github_org,
        github_url: form.github_url,
        confluence_space: form.confluence_space,
        confluence_url: form.confluence_url,
      });
      setEditing(false);
      onChanged();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (
      !window.confirm(
        `Delete domain "${domain.name}"? This also removes its ${domain.repo_count} linked repo(s) and ${domain.doc_count} tracked doc(s).`
      )
    )
      return;
    setBusy(true);
    try {
      await api.deleteDomain(domain.name);
      onChanged(domain.name);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2 transition-colors",
        active
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-800"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <button onClick={() => onSelect(domain.name)} className="text-left min-w-0 flex-1">
          <div className="font-medium text-sm truncate">{domain.name}</div>
          <div className="text-xs text-gray-500">
            {domain.product} · {domain.repo_count} repos · {domain.doc_count} docs
          </div>
        </button>
        <div className="flex items-center gap-1 shrink-0">
          <Badge variant="secondary">{domain.product}</Badge>
          <Button variant="ghost" size="icon" onClick={() => setEditing((v) => !v)} title="Edit domain">
            {editing ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={remove} disabled={busy} title="Delete domain">
            <Trash2 className="h-4 w-4 text-red-500" />
          </Button>
        </div>
      </div>

      {editing && (
        <div className="mt-3 space-y-2">
          <div>
            <label className="text-xs text-gray-500">Product</label>
            <select
              value={form.product}
              onChange={(e) => setForm({ ...form, product: e.target.value })}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              {products.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <Field label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
          <Field label="Jira project" value={form.jira_project} onChange={(v) => setForm({ ...form, jira_project: v })} />
          <div className="grid grid-cols-2 gap-2">
            <Field label="Bitbucket project key" value={form.bitbucket_project} onChange={(v) => setForm({ ...form, bitbucket_project: v })} />
            <Field label="Bitbucket URL" value={form.bitbucket_url} onChange={(v) => setForm({ ...form, bitbucket_url: v })} />
            <Field label="GitHub org/owner" value={form.github_org} onChange={(v) => setForm({ ...form, github_org: v })} />
            <Field label="GitHub repo/org URL" value={form.github_url} onChange={(v) => setForm({ ...form, github_url: v })} />
          </div>
          <p className="text-xs text-gray-400">Provide a Bitbucket project key or a repo/project URL.</p>
          <Field label="Confluence space" value={form.confluence_space} onChange={(v) => setForm({ ...form, confluence_space: v })} />
          <Field label="Confluence URL" value={form.confluence_url} onChange={(v) => setForm({ ...form, confluence_url: v })} />
          <Button onClick={save} disabled={busy} size="sm">
            {busy ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Check className="h-4 w-4 mr-1" />}
            Save changes
          </Button>
          <p className="text-xs text-gray-400">
            Note: the slug ({domain.name}) does not change when reassigning the product.
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Step 1: select or create domain ─────────────────────────────────────── */
function DomainStep({
  products,
  domains,
  activeSlug,
  onSelect,
  onCreated,
  onChanged,
  onError,
}: {
  products: ProductInfo[];
  domains: DomainInfo[];
  activeSlug: string | null;
  onSelect: (slug: string) => void;
  onCreated: (slug: string) => void;
  onChanged: (deletedSlug?: string) => void;
  onError: (e: string) => void;
}) {
  const [form, setForm] = useState({
    product: "",
    domain: "",
    description: "",
    jira_project: "",
    bitbucket_project: "",
    bitbucket_url: "",
    github_org: "",
    github_url: "",
    confluence_space: "",
    confluence_url: "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!form.product || !form.domain) {
      onError("Product and Domain name are required.");
      return;
    }
    if (!hasRepoCoordinate(form)) {
      onError("A source-control coordinate is required: a Bitbucket project key or URL, or a GitHub org or repo URL.");
      return;
    }
    setSaving(true);
    try {
      const created = await api.createDomain({
        product: form.product,
        domain: form.domain,
        description: form.description || undefined,
        jira_project: form.jira_project || undefined,
        bitbucket_project: form.bitbucket_project || undefined,
        bitbucket_url: form.bitbucket_url || undefined,
        github_org: form.github_org || undefined,
        github_url: form.github_url || undefined,
        confluence_space: form.confluence_space || undefined,
        confluence_url: form.confluence_url || undefined,
      });
      onCreated(created.name);
    } catch (e) {
      onError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <ProductsPanel products={products} onChanged={onChanged} onError={onError} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Existing domains */}
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <h2 className="font-semibold mb-3">Continue / manage existing domains</h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {domains.length === 0 && (
              <p className="text-sm text-gray-500">No domains yet. Create one →</p>
            )}
            {domains.map((d) => (
              <DomainRow
                key={d.name}
                domain={d}
                products={products}
                active={activeSlug === d.name}
                onSelect={onSelect}
                onChanged={onChanged}
                onError={onError}
              />
            ))}
          </div>
        </div>

      {/* Create new */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-3 flex items-center gap-2">
          <Plus className="h-4 w-4" /> Onboard a new domain
        </h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500">Product *</label>
            <select
              value={form.product}
              onChange={(e) => setForm({ ...form, product: e.target.value })}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">Select product…</option>
              {products.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name} ({p.domain_count} domains)
                </option>
              ))}
            </select>
          </div>
          <Field label="Domain name * (e.g. Imaging)" value={form.domain}
            onChange={(v) => setForm({ ...form, domain: v })} />
          <Field label="Description" value={form.description}
            onChange={(v) => setForm({ ...form, description: v })} />
          <Field label="Jira project" value={form.jira_project}
            onChange={(v) => setForm({ ...form, jira_project: v })} />
          <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3 space-y-2">
            <p className="text-xs font-medium text-gray-600 dark:text-gray-300">
              Bitbucket * <span className="font-normal text-gray-400">— provide a project key or a repo/project URL</span>
            </p>
            <Field label="Bitbucket project key (e.g. CGF)" value={form.bitbucket_project}
              onChange={(v) => setForm({ ...form, bitbucket_project: v })} />
            <Field label="Bitbucket repo/project URL" value={form.bitbucket_url}
              onChange={(v) => setForm({ ...form, bitbucket_url: v })} />
            <Field label="GitHub org/owner (e.g. acme)" value={form.github_org}
              onChange={(v) => setForm({ ...form, github_org: v })} />
            <Field label="GitHub repo/org URL" value={form.github_url}
              onChange={(v) => setForm({ ...form, github_url: v })} />
          </div>
          <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3 space-y-2">
            <p className="text-xs font-medium text-gray-600 dark:text-gray-300">
              Confluence <span className="font-normal text-gray-400">— optional, space key or page/space URL</span>
            </p>
            <Field label="Confluence space" value={form.confluence_space}
              onChange={(v) => setForm({ ...form, confluence_space: v })} />
            <Field label="Confluence URL" value={form.confluence_url}
              onChange={(v) => setForm({ ...form, confluence_url: v })} />
          </div>
          <Button onClick={submit} disabled={saving} className="w-full">
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Create & continue
          </Button>
          <p className="text-xs text-gray-400">
            Slug is auto-generated as <code>product-domain</code> (matches the CLI).
          </p>
        </div>
      </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="text-xs text-gray-500">{label}</label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

/* ── Step 2: repos ───────────────────────────────────────────────────────── */
function ReposStep({
  domain,
  onChanged,
}: {
  domain: DomainDetail;
  onChanged: () => void;
}) {
  const [candidates, setCandidates] = useState<BitbucketRepoCandidate[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [savingSrc, setSavingSrc] = useState(false);

  // The filter input doubles as a repo-name substring, but users often paste a
  // full Bitbucket project/repo URL here expecting it to scope the fetch. A URL
  // is never a repo slug, so it silently matches nothing. Detect that case and
  // offer to set it as the domain's Bitbucket source instead.
  const filterIsUrl = /^https?:\/\//i.test(filter.trim());

  const loadCandidates = async (q: string = filter) => {
    setLoading(true);
    setErr(null);
    try {
      setCandidates(await api.getBitbucketCandidates(domain.name, q || undefined));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const useAsBitbucketSource = async () => {
    setSavingSrc(true);
    setErr(null);
    try {
      await api.updateDomain(domain.name, { bitbucket_url: filter.trim(), bitbucket_project: "" });
      onChanged();
      setFilter("");
      setCandidates(null);
      await loadCandidates("");
    } catch (e) {
      setErr(String(e));
    } finally {
      setSavingSrc(false);
    }
  };

  const link = async (c: BitbucketRepoCandidate) => {
    setBusy(c.slug);
    try {
      await api.linkRepo(domain.name, {
        repo_slug: c.slug,
        repo_name: c.name,
        clone_url: c.clone_url,
      });
      onChanged();
      setCandidates((prev) =>
        prev?.map((x) => (x.slug === c.slug ? { ...x, already_linked: true } : x)) ?? null
      );
    } finally {
      setBusy(null);
    }
  };

  const unlink = async (slug: string) => {
    setBusy(slug);
    try {
      await api.unlinkRepo(domain.name, slug);
      onChanged();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-1">Linked repos ({domain.repos.length})</h2>
        <p className="text-xs text-gray-500 mb-3">
          Code host: {domain.bitbucket_project || domain.bitbucket_url ||
            domain.github_org || domain.github_url || "— (set it in step 1)"}
        </p>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {domain.repos.length === 0 && (
            <p className="text-sm text-gray-500">No repos linked yet.</p>
          )}
          {domain.repos.map((r) => (
            <div
              key={r.repo_slug}
              className="flex items-center justify-between rounded-md border border-gray-200 dark:border-gray-800 px-3 py-2"
            >
              <div className="text-sm font-medium">{r.repo_slug}</div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => unlink(r.repo_slug)}
                disabled={busy === r.repo_slug}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-3">Add repos from Bitbucket</h2>
        <div className="flex gap-2 mb-3">
          <Input
            placeholder="Filter repo names, or paste a Bitbucket project/repo URL"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-invalid={filterIsUrl}
          />
          <Button variant="outline" onClick={() => loadCandidates()} disabled={loading || filterIsUrl}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>

        {filterIsUrl && (
          <div className="mt-2 mb-3 rounded-md border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3 space-y-2">
            <div className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                That looks like a <strong>URL</strong>, not a repo name. Filtering by a
                URL never matches, so no repos are found. Set it as this domain's
                Bitbucket source to fetch repos from that project.
              </span>
            </div>
            <Button size="sm" onClick={useAsBitbucketSource} disabled={savingSrc}>
              {savingSrc ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Check className="h-4 w-4 mr-1" />
              )}
              Set as Bitbucket source &amp; load
            </Button>
          </div>
        )}
        {err && <p className="text-xs text-red-600 mb-2">{err}</p>}
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {candidates === null && (
            <p className="text-sm text-gray-500">
              Click refresh to preview repos from the domain's Bitbucket project.
            </p>
          )}
          {candidates?.length === 0 && !filterIsUrl && (
            <p className="text-sm text-gray-500">No repos found.</p>
          )}
          {candidates?.map((c) => (
            <div
              key={c.slug}
              className="flex items-center justify-between rounded-md border border-gray-200 dark:border-gray-800 px-3 py-2"
            >
              <div className="text-sm">{c.name || c.slug}</div>
              {c.already_linked ? (
                <Badge variant="secondary">linked</Badge>
              ) : (
                <Button size="sm" onClick={() => link(c)} disabled={busy === c.slug}>
                  {busy === c.slug ? <Loader2 className="h-4 w-4 animate-spin" /> : "Link"}
                </Button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Step 3: docs ────────────────────────────────────────────────────────── */
function DocsStep({
  domain,
  onChanged,
}: {
  domain: DomainDetail;
  onChanged: () => void;
}) {
  const [filter, setFilter] = useState("");
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ConfluencePageCandidate[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [savingSrc, setSavingSrc] = useState(false);

  // The single input doubles as the `--filter` (title substring). Users often
  // paste a full Confluence page/space URL here expecting it to scope the
  // fetch — but a URL is never a page *title*, so it silently matches nothing.
  // Detect that case and steer them to set it as the domain's Confluence
  // source instead (which fetches the page + all descendants recursively).
  const filterIsUrl = /^https?:\/\//i.test(filter.trim());
  const hasConfluenceSource = Boolean(domain.confluence_space || domain.confluence_url);

  const run = () => {
    if (filterIsUrl) return; // guarded in the UI; never send a URL as --filter
    const q = filter ? `?filter=${encodeURIComponent(filter)}` : "";
    setStreamUrl(api.streamUrl(`/domains/${domain.name}/add-docs/stream${q}`));
  };

  const loadCandidates = async () => {
    if (filterIsUrl) return;
    setLoading(true);
    setErr(null);
    try {
      setCandidates(await api.getConfluenceCandidates(domain.name, filter || undefined));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  // Correction path: treat the pasted URL as the domain's Confluence source,
  // persist it, then run `add-docs --all` (no --filter) so the CLI parses the
  // URL into a space key + page id and walks descendants recursively.
  const useAsConfluenceSource = async () => {
    setSavingSrc(true);
    setErr(null);
    try {
      await api.updateDomain(domain.name, { confluence_url: filter.trim() });
      onChanged();
      setFilter("");
      setCandidates(null);
      setStreamUrl(api.streamUrl(`/domains/${domain.name}/add-docs/stream`));
    } catch (e) {
      setErr(String(e));
    } finally {
      setSavingSrc(false);
    }
  };

  const track = async (c: ConfluencePageCandidate) => {
    setBusy(c.page_id);
    try {
      await api.addDoc(domain.name, {
        source_page_id: c.page_id,
        source_space_key: c.space_key,
        title: c.title,
        source_version: c.version,
      });
      onChanged();
      setCandidates((prev) =>
        prev?.map((x) => (x.page_id === c.page_id ? { ...x, already_tracked: true } : x)) ?? null
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-1">Tracked docs ({domain.docs.length})</h2>
        <p className="text-xs text-gray-500 mb-3">
          Confluence: {domain.confluence_space || domain.confluence_url || "— (set it in step 1)"}
        </p>
        <div className="space-y-2 max-h-72 overflow-y-auto">
          {domain.docs.length === 0 && (
            <p className="text-sm text-gray-500">No docs tracked yet.</p>
          )}
          {domain.docs.map((d) => (
            <div
              key={d.source_page_id}
              className="flex items-center justify-between rounded-md border border-gray-200 dark:border-gray-800 px-3 py-2"
            >
              <div className="text-sm">
                {d.title || d.source_page_id}
                <span className="text-xs text-gray-400 ml-2">{d.source_space_key}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={async () => {
                  await api.removeDoc(domain.name, d.source_page_id);
                  onChanged();
                }}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-3">Fetch & track docs</h2>
        {!hasConfluenceSource && !filterIsUrl && (
          <div className="mb-3 flex items-start gap-2 rounded-md border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              No Confluence source set for this domain. Paste a Confluence space or
              page URL below to set it, or configure it in step 1.
            </span>
          </div>
        )}
        <div className="flex gap-2 mb-1">
          <Input
            placeholder="Filter page titles, or paste a Confluence page/space URL"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-invalid={filterIsUrl}
          />
          <Button variant="outline" onClick={loadCandidates} disabled={loading || filterIsUrl}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
          <Button onClick={run} disabled={filterIsUrl}>Track all</Button>
        </div>

        {filterIsUrl ? (
          <div className="mt-2 mb-3 rounded-md border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3 space-y-2">
            <div className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                That looks like a <strong>URL</strong>, not a page title. Filtering by a
                URL never matches, so no pages are found. Set it as this domain's
                Confluence source to fetch that page and all its descendants.
              </span>
            </div>
            <Button size="sm" onClick={useAsConfluenceSource} disabled={savingSrc}>
              {savingSrc ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Check className="h-4 w-4 mr-1" />
              )}
              Set as Confluence source &amp; fetch
            </Button>
          </div>
        ) : (
          <p className="text-xs text-gray-400 mb-3">
            Preview pages to select individually, or "Track all" to run{" "}
            <code>keel domain add-docs {domain.name} --all</code> (includes cross-space scan).
          </p>
        )}
        {err && <p className="text-xs text-red-600 mb-2">{err}</p>}

        {candidates !== null && (
          <div className="space-y-2 max-h-72 overflow-y-auto mb-3">
            {candidates.length === 0 && (
              <p className="text-sm text-gray-500">No pages found.</p>
            )}
            {candidates.map((c) => (
              <div
                key={c.page_id}
                className="flex items-center justify-between rounded-md border border-gray-200 dark:border-gray-800 px-3 py-2"
              >
                <div className="text-sm">
                  {c.title || c.page_id}
                  <span className="text-xs text-gray-400 ml-2">{c.space_key}</span>
                </div>
                {c.already_tracked ? (
                  <Badge variant="secondary">tracked</Badge>
                ) : (
                  <Button size="sm" onClick={() => track(c)} disabled={busy === c.page_id}>
                    {busy === c.page_id ? <Loader2 className="h-4 w-4 animate-spin" /> : "Track"}
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        <StreamConsole url={streamUrl} onDone={onChanged} />
      </div>
    </div>
  );
}

/* ── Step 4: skills (review + role-aware regeneration) ────────────────────── */
function SkillsStep({ slug, product }: { slug: string; product: string }) {
  return <PersonaSkillsPanel slug={slug} product={product} />;
}

/* ── Step 6: scaffold ────────────────────────────────────────────────────── */
function ScaffoldStep({ slug, product }: { slug: string; product: string }) {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [productMetaPath, setProductMetaPath] = useState<string | null>(null);
  const [linkProduct, setLinkProduct] = useState(true);
  const [overwrite, setOverwrite] = useState(true);
  const [skipKg, setSkipKg] = useState(false);
  const [paths, setPaths] = useState<ScaffoldPaths | null>(null);

  // Resolve the product meta-repo path (if it was scaffolded) so we can thread
  // it into the domain meta as a submodule (the outer-loop shared tier).
  useEffect(() => {
    let cancelled = false;
    api
      .getProductGovernance(product)
      .then((g) => {
        if (!cancelled) setProductMetaPath(g.found ? g.path ?? null : null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [product]);

  // Resolve the on-disk context/meta repo paths so we can offer "Open in IDE"
  // to review generated files. Refreshed whenever a scaffold step finishes.
  const refreshPaths = () => {
    api
      .getScaffoldPaths(slug)
      .then(setPaths)
      .catch(() => {});
  };
  useEffect(refreshPaths, [slug]);

  const initUrl = () => {
    const params = new URLSearchParams();
    if (linkProduct && productMetaPath) {
      params.set("product_meta", productMetaPath);
    }
    if (overwrite) {
      params.set("force", "true");
    }
    if (skipKg) {
      params.set("no_kg", "true");
    }
    const qs = params.toString();
    return api.streamUrl(`/domains/${slug}/init/stream${qs ? `?${qs}` : ""}`);
  };

  // Post-cutover: context + meta live in ONE <slug>-context-meta repo. Both
  // scaffold-path entries resolve to it, so show it once.
  const repo = paths?.context ?? paths?.meta ?? null;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <h2 className="font-semibold mb-3">Generate context-meta repo</h2>
      <div className="flex gap-2 flex-wrap">
        <Button onClick={() => setStreamUrl(initUrl())}>
          <FolderGit2 className="h-4 w-4 mr-1" /> Generate context-meta
        </Button>
      </div>

      <label className="flex items-center gap-2 mt-3 text-sm text-gray-600 dark:text-gray-300">
        <input
          type="checkbox"
          checked={linkProduct}
          onChange={(e) => setLinkProduct(e.target.checked)}
          disabled={!productMetaPath}
        />
        Link product meta-repo (outer-loop shared tier)
        {productMetaPath ? (
          <Badge className="ml-1">{product} meta found</Badge>
        ) : (
          <span className="text-xs text-amber-500">
            no product meta — scaffold it in the Product step first
          </span>
        )}
      </label>

      <label className="flex items-center gap-2 mt-2 text-sm text-gray-600 dark:text-gray-300">
        <input
          type="checkbox"
          checked={overwrite}
          onChange={(e) => setOverwrite(e.target.checked)}
        />
        Overwrite if the repo already exists (--force)
      </label>

      <label className="flex items-center gap-2 mt-2 text-sm text-gray-600 dark:text-gray-300">
        <input
          type="checkbox"
          checked={skipKg}
          onChange={(e) => setSkipKg(e.target.checked)}
        />
        Skip Knowledge Graph query (faster; placeholder content)
      </label>

      <p className="text-xs text-gray-400 mt-2">
        Runs <code>keel domain init {slug}</code> — one repo (<code>{slug}-context-meta</code>)
        with KG context, skills, governance, personas, and repo submodules. Skills
        are auto-registered with your IDE (Windsurf/Cascade, Cursor, or Devin).
        When linked, it references the product meta as a submodule (shared
        governance + crosswalk + exceptions ledger).
      </p>

      {/* Review generated files: open the unified repo in an IDE. */}
      <div className="mt-4 border-t border-gray-200 dark:border-gray-800 pt-3 space-y-3">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Review generated files
        </h3>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm w-36 shrink-0">Context-meta repo</span>
          {repo?.exists ? (
            <>
              <OpenInIdeButton path={repo.path} size="sm" label="Open in IDE" />
              <code className="text-xs text-gray-400 break-all">{repo.path}</code>
            </>
          ) : (
            <span className="text-xs text-amber-500">
              not generated yet — run “Generate context-meta” above
            </span>
          )}
        </div>
      </div>

      <StreamConsole url={streamUrl} onDone={refreshPaths} />
    </div>
  );
}

/* ── Step 1 (NEW): product — scaffold product meta + governance + exceptions ── */
function ProductStep({
  products,
  activeProduct,
  onSelectProduct,
  onChanged,
  onError,
  onContinue,
}: {
  products: ProductInfo[];
  activeProduct: string | null;
  onSelectProduct: (name: string) => void;
  onChanged: () => Promise<void> | void;
  onError: (e: string) => void;
  onContinue: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [overwrite, setOverwrite] = useState(true);

  const create = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await api.createProduct({ name: name.trim(), description: description.trim() || undefined });
      setName("");
      setDescription("");
      await onChanged();
      onSelectProduct(name.trim().toUpperCase());
    } catch (e) {
      onError(String(e));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Create product */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-3">Register a product</h2>
        <div className="flex flex-col sm:flex-row gap-2">
          <Input
            placeholder="Product name (e.g. ABC)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="sm:w-48"
          />
          <Input
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="flex-1"
          />
          <Button onClick={create} disabled={creating || !name.trim()}>
            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create
          </Button>
        </div>
      </div>

      {/* Select product */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-3">Select a product</h2>
        {products.length === 0 ? (
          <p className="text-sm text-gray-400">No products yet — create one above.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {products.map((p) => (
              <button
                key={p.name}
                onClick={() => onSelectProduct(p.name)}
                className={cn(
                  "px-3 py-2 rounded-lg text-sm border transition-colors",
                  activeProduct === p.name
                    ? "bg-blue-600 text-white border-blue-600"
                    : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                )}
              >
                <Package className="h-4 w-4 inline mr-1" />
                {p.name}
                <span className="ml-2 text-xs opacity-70">{p.domain_count} domains</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {activeProduct && (
        <>
          {/* Scaffold product meta */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <h2 className="font-semibold mb-3">Scaffold product meta-repo</h2>
            <p className="text-xs text-gray-400 mb-3">
              Creates <code>product-{activeProduct.toLowerCase()}-meta</code> with the
              shared outer-loop governance, the inner↔outer crosswalk, and the
              exceptions ledger. Pins the org-wide methodology (inner loop) as a submodule.
            </p>
            <Button
              variant="outline"
              onClick={() =>
                setStreamUrl(
                  api.productInitMetaStreamUrl(activeProduct, undefined, overwrite)
                )
              }
            >
              <FolderGit2 className="h-4 w-4" /> Init product meta
            </Button>
            <label className="flex items-center gap-2 mt-3 text-sm text-gray-600 dark:text-gray-300">
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(e) => setOverwrite(e.target.checked)}
              />
              Overwrite if it already exists (--force)
            </label>
            <StreamConsole url={streamUrl} />
          </div>

          <GovernancePanel product={activeProduct} reloadKey={streamUrl} />
          <ExceptionsPanel product={activeProduct} onError={onError} />

          <div className="flex justify-end">
            <Button onClick={onContinue}>Continue to Domain →</Button>
          </div>
        </>
      )}
    </div>
  );
}

/* ── Governance viewer (gates + crosswalk) ───────────────────────────────── */
function GovernancePanel({
  product,
  reloadKey,
}: {
  product: string;
  reloadKey?: string | null;
}) {
  const [info, setInfo] = useState<GovernanceInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getProductGovernance(product)
      .then((g) => !cancelled && setInfo(g))
      .catch(() => !cancelled && setInfo(null));
    return () => {
      cancelled = true;
    };
  }, [product, reloadKey]);

  if (!info) return null;
  if (!info.found) {
    return (
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-1 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" /> Governance
        </h2>
        <p className="text-sm text-amber-500">
          No product meta-repo yet — scaffold it above to define governance.
        </p>
      </div>
    );
  }

  const g = info.governance ?? {};
  const crosswalk = info.crosswalk?.checkpoint_gate_map ?? g.checkpoint_gate_map ?? [];
  const promotion = info.crosswalk?.promotion_path ?? g.promotion_path ?? [];

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <h2 className="font-semibold flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" /> Governance (product tier)
        </h2>
        {info.path && <OpenInIdeButton path={info.path} size="sm" label="Review & edit in IDE" />}
      </div>

      {info.path && (
        <p className="text-xs text-gray-400 font-mono break-all">{info.path}</p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
        <Gate label="CI gates" on={!!g.require_ci_gates} />
        <Gate label="Code review" on={!!g.require_code_review} />
        <Gate label="Tests" on={!!g.require_tests} />
        <div className="text-gray-500">
          Min reviewers: <span className="text-gray-800 dark:text-gray-200">{g.min_reviewers ?? "—"}</span>
        </div>
        <div className="text-gray-500">
          Coverage min: <span className="text-gray-800 dark:text-gray-200">{g.test_coverage_min ?? "—"}%</span>
        </div>
      </div>

      {promotion.length > 0 && (
        <div className="text-sm">
          <span className="text-gray-500">Promotion path: </span>
          <span className="font-mono">{promotion.join(" → ")}</span>
        </div>
      )}

      {crosswalk.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-1">Inner ↔ Outer crosswalk</div>
          <table className="w-full text-sm border border-gray-200 dark:border-gray-800 rounded">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-200 dark:border-gray-800">
                <th className="px-2 py-1">Checkpoint (inner)</th>
                <th className="px-2 py-1">Gate (outer)</th>
                <th className="px-2 py-1">Blocking</th>
              </tr>
            </thead>
            <tbody>
              {crosswalk.map((c, i) => (
                <tr key={i} className="border-b border-gray-100 dark:border-gray-900">
                  <td className="px-2 py-1 font-mono">{c.checkpoint}</td>
                  <td className="px-2 py-1 font-mono">{c.gate}</td>
                  <td className="px-2 py-1">{c.blocking ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {info.path && (
        <div className="rounded-md bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800 p-3 text-xs space-y-1">
          <p className="text-gray-500">
            To cover more (e.g. integration workflows), open the meta-repo and edit:
          </p>
          <ul className="font-mono text-gray-600 dark:text-gray-300 space-y-0.5">
            <li>.platform/config/governance.yaml <span className="text-gray-400">— gates, coverage, inner-loop floor</span></li>
            <li>.platform/config/crosswalk.yaml <span className="text-gray-400">— checkpoint ↔ promotion-gate map</span></li>
            <li>outer-loop/product/pipeline-standards.md <span className="text-gray-400">— CI/CD + integration standards</span></li>
            <li>outer-loop/product/definition-of-done.md <span className="text-gray-400">— DoD across both loops</span></li>
          </ul>
          <p className="text-gray-400 pt-1">
            Edits are saved at the working location above; commit them in the meta-repo to take effect.
          </p>
        </div>
      )}
    </div>
  );
}

function Gate({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center gap-1">
      {on ? (
        <Check className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        <X className="h-3.5 w-3.5 text-gray-400" />
      )}
      <span className={on ? "" : "text-gray-400"}>{label}</span>
    </div>
  );
}

/* ── Exceptions ledger (override-with-justification) ─────────────────────── */
function ExceptionsPanel({
  product,
  onError,
}: {
  product: string;
  onError: (e: string) => void;
}) {
  const [items, setItems] = useState<ExceptionInfo[]>([]);
  const [rule, setRule] = useState("");
  const [reason, setReason] = useState("");
  const [scope, setScope] = useState("");
  const [owner, setOwner] = useState("");
  const [expires, setExpires] = useState("");
  const [saving, setSaving] = useState(false);

  const reload = async () => {
    try {
      setItems(await api.listProductExceptions(product));
    } catch (e) {
      onError(String(e));
    }
  };

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product]);

  const add = async () => {
    if (!rule.trim() || !reason.trim() || !scope.trim() || !owner.trim()) return;
    setSaving(true);
    try {
      await api.addProductException(product, {
        rule: rule.trim(),
        reason: reason.trim(),
        scope: scope.trim(),
        owner: owner.trim(),
        expires: expires.trim() || undefined,
      });
      setRule("");
      setReason("");
      setScope("");
      setOwner("");
      setExpires("");
      await reload();
    } catch (e) {
      onError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
      <h2 className="font-semibold flex items-center gap-2">
        <AlertTriangle className="h-4 w-4" /> Exceptions ledger
        <span className="text-xs font-normal text-gray-400">(override with justification)</span>
      </h2>

      {/* File a waiver */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Input placeholder="Rule (e.g. tdd)" value={rule} onChange={(e) => setRule(e.target.value)} />
        <Input placeholder="Scope (e.g. domain:abc-a1)" value={scope} onChange={(e) => setScope(e.target.value)} />
        <Input placeholder="Reason / justification" value={reason} onChange={(e) => setReason(e.target.value)} />
        <Input placeholder="Owner (email)" value={owner} onChange={(e) => setOwner(e.target.value)} />
        <Input placeholder="Expires (YYYY-MM-DD)" value={expires} onChange={(e) => setExpires(e.target.value)} />
        <Button onClick={add} disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          File waiver
        </Button>
      </div>

      {/* List */}
      {items.length === 0 ? (
        <p className="text-sm text-gray-400">No exceptions recorded.</p>
      ) : (
        <table className="w-full text-sm border border-gray-200 dark:border-gray-800 rounded">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200 dark:border-gray-800">
              <th className="px-2 py-1">ID</th>
              <th className="px-2 py-1">Rule</th>
              <th className="px-2 py-1">Scope</th>
              <th className="px-2 py-1">Owner</th>
              <th className="px-2 py-1">Expires</th>
              <th className="px-2 py-1">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} className="border-b border-gray-100 dark:border-gray-900">
                <td className="px-2 py-1 font-mono">{e.id}</td>
                <td className="px-2 py-1">{e.rule}</td>
                <td className="px-2 py-1 font-mono text-xs">{e.scope}</td>
                <td className="px-2 py-1 text-xs">{e.owner}</td>
                <td className="px-2 py-1">{e.expires_at || "—"}</td>
                <td className="px-2 py-1">
                  <Badge className={e.effective ? "" : "opacity-60"}>
                    {e.effective ? "active" : e.status === "active" ? "expired" : e.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
