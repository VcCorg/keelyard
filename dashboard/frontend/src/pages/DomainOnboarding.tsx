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
} from "@/lib/api";
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
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!url) return;
    setLines([]);
    setRunning(true);
    const es = new EventSource(url);
    es.addEventListener("log", (e: MessageEvent) =>
      setLines((p) => [...p, e.data])
    );
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
        <span className="text-xs text-gray-400 font-mono">CLI output</span>
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

const STEPS = [
  { key: "domain", label: "Domain", icon: Boxes },
  { key: "repos", label: "Repos", icon: GitBranch },
  { key: "docs", label: "Docs", icon: FileText },
  { key: "skills", label: "Skills", icon: Sparkles },
  { key: "scaffold", label: "Scaffold", icon: FolderGit2 },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

export function DomainOnboarding() {
  const [step, setStep] = useState<StepKey>("domain");
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [active, setActive] = useState<DomainDetail | null>(null);
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
          Drive the <code className="text-xs">dva domain</code> workflow from the UI.
          The dashboard is a thin proxy — all logic runs in the CLI core.
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const disabled = s.key !== "domain" && !active;
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

      {step === "skills" && active && <SkillsStep slug={active.name} />}

      {step === "scaffold" && active && <ScaffoldStep slug={active.name} />}
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

  const remove = async (p: ProductInfo) => {
    if (p.domain_count > 0) return;
    if (!window.confirm(`Remove product "${p.name}"? This cannot be undone.`)) return;
    setBusy(p.name);
    try {
      await api.deleteProduct(p.name);
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
                  onClick={() => remove(p)}
                  disabled={p.domain_count > 0 || busy === p.name}
                  title={
                    p.domain_count > 0
                      ? `Reassign or delete its ${p.domain_count} domain(s) first`
                      : "Remove product"
                  }
                >
                  <Trash2 className={cn("h-4 w-4", p.domain_count > 0 ? "text-gray-300" : "text-red-500")} />
                </Button>
              </div>
            </div>

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
    confluence_space: domain.confluence_space ?? "",
    confluence_url: domain.confluence_url ?? "",
  });

  const save = async () => {
    if (!form.bitbucket_project.trim() && !form.bitbucket_url.trim()) {
      onError("A Bitbucket project key or a Bitbucket repo/project URL is required.");
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
            <Field label="Bitbucket project key *" value={form.bitbucket_project} onChange={(v) => setForm({ ...form, bitbucket_project: v })} />
            <Field label="Bitbucket URL *" value={form.bitbucket_url} onChange={(v) => setForm({ ...form, bitbucket_url: v })} />
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
    confluence_space: "",
    confluence_url: "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!form.product || !form.domain) {
      onError("Product and Domain name are required.");
      return;
    }
    if (!form.bitbucket_project.trim() && !form.bitbucket_url.trim()) {
      onError("A Bitbucket project key or a Bitbucket repo/project URL is required.");
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

  const loadCandidates = async () => {
    setLoading(true);
    setErr(null);
    try {
      setCandidates(await api.getBitbucketCandidates(domain.name, filter || undefined));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
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
          Bitbucket: {domain.bitbucket_project || domain.bitbucket_url || "— (set it in step 1)"}
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
            placeholder="Filter (optional)"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <Button variant="outline" onClick={loadCandidates} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>
        {err && <p className="text-xs text-red-600 mb-2">{err}</p>}
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {candidates === null && (
            <p className="text-sm text-gray-500">
              Click refresh to preview repos from the domain's Bitbucket project.
            </p>
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

  const run = () => {
    const q = filter ? `?filter=${encodeURIComponent(filter)}` : "";
    setStreamUrl(api.streamUrl(`/domains/${domain.name}/add-docs/stream${q}`));
  };

  const loadCandidates = async () => {
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
        <div className="flex gap-2 mb-1">
          <Input
            placeholder="Filter page titles (optional)"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <Button variant="outline" onClick={loadCandidates} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
          <Button onClick={run}>Track all</Button>
        </div>
        <p className="text-xs text-gray-400 mb-3">
          Preview pages to select individually, or "Track all" to run{" "}
          <code>dva domain add-docs {domain.name} --all</code> (includes cross-space scan).
        </p>
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

/* ── Step 4: skills ──────────────────────────────────────────────────────── */
function SkillsStep({ slug }: { slug: string }) {
  const [role, setRole] = useState("");
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  const run = () => {
    const q = role ? `?role=${encodeURIComponent(role)}` : "";
    setStreamUrl(api.streamUrl(`/domains/${slug}/gen-skills/stream${q}`));
  };

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <h2 className="font-semibold mb-3">Generate persona skills</h2>
      <div className="flex gap-2 items-center">
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All roles</option>
          <option value="domain">Domain overview</option>
          <option value="dev">Developer</option>
          <option value="qa">QA</option>
          <option value="sm">Scrum Master</option>
          <option value="ba">Business Analyst</option>
        </select>
        <Button onClick={run}>Generate</Button>
      </div>
      <p className="text-xs text-gray-400 mt-2">
        Runs <code>dva domain gen-skills {slug}</code> via the CLI.
      </p>
      <StreamConsole url={streamUrl} />
    </div>
  );
}

/* ── Step 5: scaffold ────────────────────────────────────────────────────── */
function ScaffoldStep({ slug }: { slug: string }) {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <h2 className="font-semibold mb-3">Scaffold repos</h2>
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={() => setStreamUrl(api.streamUrl(`/domains/${slug}/init-context/stream`))}
        >
          Init context repo
        </Button>
        <Button
          variant="outline"
          onClick={() => setStreamUrl(api.streamUrl(`/domains/${slug}/init-meta/stream`))}
        >
          Init meta repo
        </Button>
      </div>
      <p className="text-xs text-gray-400 mt-2">
        Runs <code>dva domain init-context / init-meta {slug}</code> via the CLI.
      </p>
      <StreamConsole url={streamUrl} />
    </div>
  );
}
