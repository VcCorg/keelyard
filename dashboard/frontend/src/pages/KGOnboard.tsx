import { useEffect, useMemo, useState } from "react";
import {
  Wand2, GitBranch, User, Boxes, ChevronRight, ChevronLeft, Play,
  ShieldCheck, FlaskConical, Database, FolderOpen, Globe, Package, Plus, Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StreamConsole } from "@/components/StreamConsole";
import { useUser } from "@/context/UserContext";
import {
  api,
  type IngestableDomain,
  type IngestSubmitParams,
  type ProductInfo,
} from "@/lib/api";

/**
 * KG Onboarding Wizard — guided knowledge-graph loading with three scopes:
 *
 *  - PRODUCT scope (lead activity): the first thing onboarded. A product is
 *    registered here and its product-level knowledge loaded into the shared
 *    graph, before any domain exists to govern. Registration lives here rather
 *    than in domain onboarding because knowledge comes before the governance
 *    rules written against it.
 *  - DOMAIN scope (lead activity): builds the domain's shared graph from its
 *    tracked docs — the knowledge every role in the domain queries. Loaded as
 *    part of domain onboarding.
 *  - SESSION scope (every role): a personal, isolated LightRAG workspace
 *    (`session-<user>`) any role can load before a build starts — try context
 *    without touching shared graphs, then throw it away or re-load anytime.
 */

type Scope = "product" | "domain" | "session";
type Step = "scope" | "source" | "options" | "run";

const STEPS: Step[] = ["scope", "source", "options", "run"];
const STEP_LABELS: Record<Step, string> = {
  scope: "Scope",
  source: "Source",
  options: "Options",
  run: "Load & Verify",
};

function slugify(s: string): string {
  return (s || "user").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
}

/**
 * Pick a registered product, or register one without leaving the wizard.
 *
 * This replaced a free-text field that was passed straight through to the
 * ingest as a label, so a typo produced a graph tied to a product that did not
 * exist. Registration lives here because product knowledge is onboarded before
 * the domains and governance written against it — domain onboarding selects
 * from what this created, and says so when there is nothing to select.
 */
function ProductPicker({
  products,
  value,
  onChange,
  onRegistered,
  allowCreate,
}: {
  products: ProductInfo[];
  value: string;
  onChange: (name: string) => void;
  onRegistered: () => Promise<void> | void;
  allowCreate: boolean;
}) {
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const create = async () => {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setError("");
    try {
      await api.createProduct({ name });
      await onRegistered();
      // Products are stored upper-cased; select what was actually created.
      onChange(name.toUpperCase());
      setNewName("");
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="sm:col-span-2 space-y-2">
      <label className="text-xs text-gray-500 block">Product (required)</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
      >
        <option value="">Select a product…</option>
        {products.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name}
            {p.domain_count ? ` — ${p.domain_count} domains` : " — no domains yet"}
          </option>
        ))}
      </select>

      {allowCreate && (
        <div className="flex gap-2">
          <Input
            placeholder="Or register a new product (e.g. ACME)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void create();
              }
            }}
          />
          <Button
            variant="outline"
            onClick={create}
            disabled={creating || !newName.trim()}
          >
            {creating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Register
          </Button>
        </div>
      )}
      {products.length === 0 && (
        <p className="text-[11px] text-gray-400">
          No products registered yet
          {allowCreate ? " — register one above." : " — ask a tech lead to register one."}
        </p>
      )}
      {error && <p className="text-[11px] text-red-500">{error}</p>}
    </div>
  );
}


export function KGOnboard() {
  const { user } = useUser();
  const isLead = user.role === "lead" || user.role === "admin";
  const sessionWorkspace = `session-${slugify(user.email || user.name)}`;

  const [step, setStep] = useState<Step>("scope");
  const [scope, setScope] = useState<Scope | null>(null);

  // Domain scope
  const [domains, setDomains] = useState<IngestableDomain[]>([]);
  const [domain, setDomain] = useState("");
  const [depth, setDepth] = useState(3);
  const [top, setTop] = useState<number | "">("");

    // Product + session scopes both name a product and a source.
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [sourceKind, setSourceKind] = useState<"path" | "source">("path");
  const [path, setPath] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [format, setFormat] = useState("");
  const [product, setProduct] = useState("");

  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const loadProducts = () =>
    api.listProducts().then(setProducts).catch(() => setProducts([]));

  useEffect(() => {
    api.listIngestableDomains().then(setDomains).catch(() => setDomains([]));
    loadProducts();
  }, []);

  const stepIndex = STEPS.indexOf(step);

  const canNext = useMemo(() => {
    if (step === "scope") {
      if (scope === null) return false;
      // Registering a product and loading a domain's shared graph are both
      // lead activities; a session workspace is every role's to use.
      return scope === "session" || isLead;
    }
    if (step === "source") {
      if (scope === "domain") return !!domain;
      const named = sourceKind === "path" ? !!path.trim() : !!sourceName.trim();
      return named && !!product.trim();
    }
    return true;
  }, [step, scope, domain, sourceKind, path, sourceName, product, isLead]);

  const start = () => {
    const params: IngestSubmitParams = {};
    if (scope === "domain") {
      params.domain = domain;
      params.depth = depth;
      if (top) params.top = Number(top);
    } else {
      params.product = product.trim();
      if (sourceKind === "path") params.path = path.trim();
      else params.source = sourceName.trim();
      if (format.trim()) params.format = format.trim();
      if (scope === "session") {
        // Isolated LightRAG workspace, personal to this user.
        params.workspace = sessionWorkspace;
        params.provider = "lightrag";
      }
      // Product scope deliberately sets neither: no workspace means the shared
      // graph, which is the point — product knowledge is what everyone reads.
    }
    setDone(false);
    setStreamUrl(api.kgIngestStreamUrl(params));
  };

  const cardCls = (active: boolean, disabled = false) =>
    `rounded-xl border-2 p-5 text-left transition-colors w-full ${
      disabled
        ? "border-gray-200 dark:border-gray-800 opacity-50 cursor-not-allowed"
        : active
          ? "border-blue-500 bg-blue-50/50 dark:bg-blue-900/10 cursor-pointer"
          : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 cursor-pointer"
    }`;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <Wand2 className="h-7 w-7 text-blue-500" /> KG Onboarding
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Load knowledge into the graph — shared per domain, or scoped to your session
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2 text-xs">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-full font-medium ${
                i === stepIndex
                  ? "bg-blue-600 text-white"
                  : i < stepIndex
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                    : "bg-gray-100 text-gray-500 dark:bg-gray-800"
              }`}
            >
              {i + 1}. {STEP_LABELS[s]}
            </span>
            {i < STEPS.length - 1 && <ChevronRight className="h-3.5 w-3.5 text-gray-300" />}
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 space-y-5">
        {/* ── Step 1: Scope ── */}
        {step === "scope" && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold">Who is this knowledge for?</h2>
            <div className="grid sm:grid-cols-3 gap-4">
              <button className={cardCls(scope === "product", !isLead)} onClick={() => isLead && setScope("product")}>
                <div className="flex items-center gap-2 font-semibold text-sm">
                  <Package className="h-4 w-4 text-violet-500" /> Product KG
                  <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-300 inline-flex items-center gap-1">
                    <ShieldCheck className="h-3 w-3" /> lead
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Start here. Register a product and load the knowledge that spans it,
                  into the shared graph — before any domain exists to govern.
                </p>
                {!isLead && (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-2">
                    Registering a product is a tech-lead activity.
                  </p>
                )}
              </button>
              <button className={cardCls(scope === "domain", !isLead)} onClick={() => isLead && setScope("domain")}>
                <div className="flex items-center gap-2 font-semibold text-sm">
                  <Boxes className="h-4 w-4 text-blue-500" /> Domain KG
                  <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300 inline-flex items-center gap-1">
                    <ShieldCheck className="h-3 w-3" /> lead
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  The domain's shared graph, built from its tracked docs. Every role in the
                  domain queries it. Part of domain onboarding (governance phase).
                </p>
                {!isLead && (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-2">
                    Domain KG loading is a tech-lead activity.
                  </p>
                )}
              </button>
              <button className={cardCls(scope === "session")} onClick={() => setScope("session")}>
                <div className="flex items-center gap-2 font-semibold text-sm">
                  <User className="h-4 w-4 text-emerald-500" /> Session KG
                  <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300 inline-flex items-center gap-1">
                    <FlaskConical className="h-3 w-3" /> all roles
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Your personal, isolated workspace (<code className="font-mono">{sessionWorkspace}</code>).
                  Load context before a build starts — experiment freely without touching
                  any shared graph.
                </p>
              </button>
            </div>
          </div>
        )}

        {/* ── Step 2: Source ── */}
        {step === "source" && scope === "domain" && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold">Which domain?</h2>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Select a domain…</option>
              {domains.map((d) => (
                <option key={d.slug} value={d.slug}>
                  {d.slug} — {d.doc_count} tracked docs{d.kg_ingested ? ` (${d.kg_ingested} already in KG)` : ""}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-gray-400">
              Builds from the domain's tracked docs (Confluence sync). Repos and docs were
              registered during domain onboarding.
            </p>
          </div>
        )}
        {step === "source" && (scope === "session" || scope === "product") && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold">
              {scope === "product"
                ? "Which product, and what should it load?"
                : "What should your session workspace load?"}
            </h2>
            <div className="flex gap-2">
              {(["path", "source"] as const).map((k) => (
                <button
                  key={k}
                  onClick={() => setSourceKind(k)}
                  className={`px-3 py-1.5 text-sm rounded-md border inline-flex items-center gap-1.5 ${
                    sourceKind === k
                      ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                      : "border-gray-200 dark:border-gray-700 text-gray-500"
                  }`}
                >
                  {k === "path" ? <FolderOpen className="h-3.5 w-3.5" /> : <Globe className="h-3.5 w-3.5" />}
                  {k === "path" ? "File / directory / URL" : "Configured data source"}
                </button>
              ))}
            </div>
            {sourceKind === "path" ? (
              <Input placeholder="/docs/spec.md, ./requirements/, or https://…" value={path} onChange={(e) => setPath(e.target.value)} />
            ) : (
              <Input placeholder="Data source name (keel kg config)" value={sourceName} onChange={(e) => setSourceName(e.target.value)} />
            )}
            <div className="grid sm:grid-cols-2 gap-3">
              <ProductPicker
                products={products}
                value={product}
                onChange={setProduct}
                onRegistered={loadProducts}
                allowCreate={isLead}
              />
              <div>
                <label className="text-xs text-gray-500 block mb-1">Format override (optional)</label>
                <Input placeholder="markdown | pdf | html …" value={format} onChange={(e) => setFormat(e.target.value)} />
              </div>
            </div>
          </div>
        )}

        {/* ── Step 3: Options ── */}
        {step === "options" && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold">Options</h2>
            {scope === "domain" ? (
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Crawl depth (1–10)</label>
                  <Input type="number" min={1} max={10} value={depth} onChange={(e) => setDepth(Number(e.target.value) || 3)} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Limit pages (testing, optional)</label>
                  <Input type="number" min={1} placeholder="all" value={top} onChange={(e) => setTop(e.target.value ? Number(e.target.value) : "")} />
                </div>
              </div>
            ) : (
              <div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-4 text-xs text-gray-500 space-y-1.5">
                {scope === "product" ? (
                  <>
                    <p className="flex items-center gap-1.5">
                      <Package className="h-3.5 w-3.5" /> Product:{" "}
                      <code className="font-mono">{product}</code> — loads into the
                      shared graph, not a private workspace.
                    </p>
                    <p>
                      Every role reads this. Domains registered under{" "}
                      <code className="font-mono">{product}</code> inherit it as the
                      knowledge their governance is written against.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="flex items-center gap-1.5">
                      <Database className="h-3.5 w-3.5" /> Provider: <code className="font-mono">lightrag</code> —
                      session scope uses isolated LightRAG workspaces.
                    </p>
                    <p className="flex items-center gap-1.5">
                      <User className="h-3.5 w-3.5" /> Workspace: <code className="font-mono">{sessionWorkspace}</code> —
                      private to you; shared graphs are never touched.
                    </p>
                    <p>
                      Reload anytime to replace it, or clear it with{" "}
                      <code className="font-mono">keel kg workspace</code> commands in the Terminal.
                    </p>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Step 4: Run ── */}
        {step === "run" && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold">Load & verify</h2>
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-4 text-xs text-gray-600 dark:text-gray-300 font-mono">
              {scope === "domain"
                ? `keel kg ingest submit --domain ${domain} --depth ${depth}${top ? ` --top ${top}` : ""}`
                : `keel kg ingest submit ${
                    sourceKind === "path" ? `--path ${path}` : `--source ${sourceName}`
                  } --product ${product}${
                    scope === "session"
                      ? ` --provider lightrag --workspace ${sessionWorkspace}`
                      : ""
                  }${format ? ` --format ${format}` : ""}`}
            </div>
            {!streamUrl && (
              <Button onClick={start}>
                <Play className="h-4 w-4 mr-1.5" /> Load knowledge
              </Button>
            )}
            {streamUrl && (
              <StreamConsole url={streamUrl} title="keel kg ingest" onDone={() => setDone(true)} />
            )}
            {done && (
              <div className="rounded-lg border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/60 dark:bg-emerald-900/10 p-4 text-sm text-emerald-800 dark:text-emerald-300 space-y-1">
                <p className="font-medium">Knowledge loaded.</p>
                <p className="text-xs">
                  {scope === "domain" ? (
                    <>Explore it in <a className="underline" href="/kg">KG Context</a> — every role in '{domain}' can now query it.</>
                  ) : scope === "product" ? (
                    <>
                      <code className="font-mono">{product}</code> is registered and its
                      knowledge is in the shared graph. Next, set up a domain under it in{" "}
                      <a className="underline" href="/onboarding">Domain onboarding</a>.
                    </>
                  ) : (
                    <>Your session workspace <code className="font-mono">{sessionWorkspace}</code> is ready —
                    it will serve your builds/queries until you replace or clear it.</>
                  )}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Nav buttons */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800">
          <Button
            variant="outline"
            size="sm"
            disabled={stepIndex === 0 || !!streamUrl}
            onClick={() => setStep(STEPS[stepIndex - 1])}
          >
            <ChevronLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          {step !== "run" && (
            <Button size="sm" disabled={!canNext} onClick={() => setStep(STEPS[stepIndex + 1])}>
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </div>

      <p className="text-[11px] text-gray-400 flex items-center gap-1.5">
        <GitBranch className="h-3.5 w-3.5" />
        Domain KGs are shared, governed knowledge; session workspaces are personal scratch
        graphs — the same duality the skills registry follows (domain skills vs. trial skills).
      </p>
    </div>
  );
}
