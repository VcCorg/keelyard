import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Database,
  FileText,
  GitBranch,
  Loader2,
  Check,
  AlertCircle,
  Play,
  RefreshCw,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SetupRequiredBanner } from "@/components/SetupRequiredBanner";
import { Neo4jPreflight } from "@/components/Neo4jPreflight";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type IngestJobInfo,
  type IngestableDomain,
  type IngestSubmitParams,
  type DataSourceInfo,
  type ProductInfo,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/* ── Streaming console (mirrors DomainOnboarding) ─────────────────────────── */
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
        <span className="text-xs text-gray-400 font-mono">keel kg ingest</span>
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

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  pending: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  cancelled: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "text-xs font-semibold px-2 py-0.5 rounded-full",
        STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600"
      )}
    >
      {status}
    </span>
  );
}

/* ── Product (required) + Domain (optional) binding for an ingest ─────────── */
function ProductDomainPicker({
  products,
  domains,
  product,
  domain,
  onProduct,
  onDomain,
}: {
  products?: ProductInfo[];
  domains?: IngestableDomain[];
  product: string;
  domain: string;
  onProduct: (v: string) => void;
  onDomain: (v: string) => void;
}) {
  const scopedDomains = (domains ?? []).filter((d) => !product || d.product === product);
  const selectCls =
    "w-full h-10 rounded-md border border-input bg-background px-3 text-sm";
  return (
    <>
      <div className="w-full sm:w-44">
        <label className="text-xs text-gray-500 block mb-1">
          Product <span className="text-red-500">*</span>
        </label>
        <select
          value={product}
          onChange={(e) => {
            onProduct(e.target.value);
            onDomain("");
          }}
          className={cn(selectCls, !product && "border-red-300 dark:border-red-800")}
        >
          <option value="">Select product…</option>
          {(products ?? []).map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      <div className="w-full sm:w-44">
        <label className="text-xs text-gray-500 block mb-1">Domain (optional)</label>
        <select
          value={domain}
          onChange={(e) => onDomain(e.target.value)}
          disabled={!product}
          className={cn(selectCls, !product && "opacity-50 cursor-not-allowed")}
        >
          <option value="">— none —</option>
          {scopedDomains.map((d) => (
            <option key={d.slug} value={d.slug}>
              {d.slug}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}

export function KGIngest() {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  // Domain ingest form
  const [depth, setDepth] = useState(3);
  const [top, setTop] = useState<string>("");

  // Path/URL ingest form
  const [path, setPath] = useState("");
  const [format, setFormat] = useState("");
  const [pathProduct, setPathProduct] = useState("");
  const [pathDomain, setPathDomain] = useState("");

  // Registered data-source ingest
  const [selectedSource, setSelectedSource] = useState("");
  const [srcProduct, setSrcProduct] = useState("");
  const [srcDomain, setSrcDomain] = useState("");

  const domainsFetcher = useCallback(() => api.listIngestableDomains(), []);
  const jobsFetcher = useCallback(() => api.listKGIngestJobs({ limit: 25 }), []);
  const sourcesFetcher = useCallback(() => api.listDataSources(), []);
  const productsFetcher = useCallback(() => api.listProducts(), []);
  const { data: sources } = usePolling<DataSourceInfo[]>(sourcesFetcher, 30000);
  const { data: products } = usePolling<ProductInfo[]>(productsFetcher, 30000);

  const {
    data: domains,
    loading: domainsLoading,
    error: domainsError,
    refresh: refreshDomains,
  } = usePolling<IngestableDomain[]>(domainsFetcher, 15000);

  const {
    data: jobs,
    loading: jobsLoading,
    refresh: refreshJobs,
  } = usePolling<IngestJobInfo[]>(jobsFetcher, 5000);

  const startStream = (params: IngestSubmitParams) => {
    setRunning(true);
    setStreamUrl(api.kgIngestStreamUrl(params));
  };

  const onStreamDone = () => {
    setRunning(false);
    refreshDomains();
    refreshJobs();
  };

  const ingestDomain = (slug: string) => {
    const t = top.trim() ? parseInt(top, 10) : undefined;
    startStream({ domain: slug, depth, top: Number.isNaN(t) ? undefined : t });
  };

  const ingestPath = () => {
    if (!path.trim() || !pathProduct) return;
    startStream({
      path: path.trim(),
      format: format.trim() || undefined,
      product: pathProduct,
      domain: pathDomain || undefined,
    });
  };

  const ingestSource = () => {
    if (!selectedSource || !srcProduct) return;
    startStream({
      source: selectedSource,
      product: srcProduct,
      domain: srcDomain || undefined,
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Link
              to="/kg"
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" /> KG Context
            </Link>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3 mt-2">
            <Database className="h-7 w-7 text-blue-500" />
            KG Ingest
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Build the knowledge graph from tracked domain docs or a direct path/URL
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { refreshDomains(); refreshJobs(); }}>
          <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
        </Button>
      </div>

      <SetupRequiredBanner requires={["workspaces", "neo4j", "vertex_ai"]} feature="KG ingest" />
      <Neo4jPreflight />

      {/* Domain ingest */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Ingest a Domain</h2>
          <div className="flex items-center gap-3 text-sm">
            <label className="flex items-center gap-1.5 text-gray-500">
              Depth
              <Input
                type="number"
                min={1}
                max={10}
                value={depth}
                onChange={(e) => setDepth(parseInt(e.target.value || "3", 10))}
                className="w-16 h-8"
              />
            </label>
            <label className="flex items-center gap-1.5 text-gray-500">
              Top
              <Input
                type="number"
                min={1}
                placeholder="all"
                value={top}
                onChange={(e) => setTop(e.target.value)}
                className="w-20 h-8"
              />
            </label>
          </div>
        </div>

        {domainsLoading && !domains && (
          <div className="flex justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
          </div>
        )}

        {domainsError && (
          <div className="flex items-center gap-2 text-red-500 text-sm py-3">
            <AlertCircle className="h-4 w-4" /> {domainsError}
          </div>
        )}

        {domains && domains.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-8 text-center">
            <p className="font-medium text-gray-500">No domains registered</p>
            <p className="text-sm text-gray-400 mt-1">
              Create a domain and track docs in{" "}
              <Link to="/onboarding" className="text-blue-600 dark:text-blue-400 hover:underline">
                Domain Onboarding
              </Link>{" "}
              first.
            </p>
          </div>
        )}

        {domains && domains.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {domains.map((d) => (
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
                  {d.kg_ingested ? (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                      Ingested
                    </span>
                  ) : (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                      Not ingested
                    </span>
                  )}
                </div>
                <div className="flex gap-4 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <FileText className="h-3 w-3" /> {d.doc_count} docs
                  </span>
                  <span className="flex items-center gap-1">
                    <GitBranch className="h-3 w-3" /> {d.repo_count} repos
                  </span>
                </div>
                <Button
                  size="sm"
                  className="w-full"
                  disabled={running || d.doc_count === 0}
                  onClick={() => ingestDomain(d.slug)}
                  title={d.doc_count === 0 ? "No tracked docs to ingest" : undefined}
                >
                  <Play className="h-4 w-4 mr-1.5" />
                  {d.kg_ingested ? "Re-ingest" : "Ingest"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Path / URL ingest */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Ingest a Path or URL</h2>
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500 block mb-1">Path / URL</label>
            <Input
              placeholder="/path/to/file.pdf, a directory, git URL, or Confluence URL"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
          </div>
          <div className="w-full sm:w-40">
            <label className="text-xs text-gray-500 block mb-1">Format (optional)</label>
            <Input
              placeholder="auto"
              value={format}
              onChange={(e) => setFormat(e.target.value)}
            />
          </div>
          <ProductDomainPicker
            products={products ?? undefined}
            domains={domains ?? undefined}
            product={pathProduct}
            domain={pathDomain}
            onProduct={setPathProduct}
            onDomain={setPathDomain}
          />
          <Button disabled={running || !path.trim() || !pathProduct} onClick={ingestPath}>
            <Play className="h-4 w-4 mr-1.5" /> Ingest
          </Button>
        </div>
      </section>

      {/* Registered data source ingest */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Ingest a Registered Source</h2>
          <Link to="/data" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
            Manage data sources
          </Link>
        </div>
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500 block mb-1">Data source</label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Select a registered source…</option>
              {(sources ?? []).map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name} ({s.type})
                </option>
              ))}
            </select>
          </div>
          <ProductDomainPicker
            products={products ?? undefined}
            domains={domains ?? undefined}
            product={srcProduct}
            domain={srcDomain}
            onProduct={setSrcProduct}
            onDomain={setSrcDomain}
          />
          <Button disabled={running || !selectedSource || !srcProduct} onClick={ingestSource}>
            <Play className="h-4 w-4 mr-1.5" /> Ingest
          </Button>
        </div>
      </section>

      {/* Stream output */}
      <StreamConsole url={streamUrl} onDone={onStreamDone} />

      {/* Jobs */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Ingest Jobs</h2>
          {jobsLoading && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                {["Job", "Source", "Mode", "Provider", "Status", "Created"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {jobs && jobs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-gray-400 text-sm">
                    No ingest jobs yet.
                  </td>
                </tr>
              )}
              {jobs?.map((j) => (
                <tr key={j.job_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{j.job_id.slice(0, 8)}</td>
                  <td className="px-4 py-3 max-w-[260px] truncate" title={j.source}>
                    {j.domain ? (
                      <span className="font-mono text-xs">domain:{j.domain}</span>
                    ) : (
                      j.source
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{j.is_async ? "async" : "sync"}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">{j.provider}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={j.status} />
                    {j.error && (
                      <p className="text-xs text-red-500 mt-1 max-w-[220px] truncate" title={j.error}>
                        {j.error}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {j.created_at ? new Date(j.created_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
