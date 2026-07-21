import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import {
  GitBranch,
  FileText,
  Code2,
  Share2,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertCircle,
  Database,
  DatabaseZap,
} from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type ProductKGSummary, type DomainKGStats } from "@/lib/api";

function CoverageMeter({ pct }: { pct: number }) {
  const color =
    pct === 0 ? "bg-gray-200 dark:bg-gray-700" :
    pct < 50 ? "bg-red-400" :
    pct < 80 ? "bg-amber-400" :
    "bg-emerald-500";
  return (
    <div className="flex items-center gap-2 mt-1.5">
      <div className="flex-1 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-500 w-10 text-right">{pct}%</span>
    </div>
  );
}

function StatusBadge({ stats }: { stats: DomainKGStats }) {
  if (!stats.has_data)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-400">No Data</span>;
  if (stats.linked_edges === 0)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">Not Linked</span>;
  if (stats.coverage_pct < 50)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-500 dark:text-red-400">Partial</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">Linked</span>;
}

function DomainRow({ d }: { d: DomainKGStats }) {
  return (
    <Link
      to={`/kg/${d.domain}`}
      className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors rounded-lg group"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
            {d.domain}
          </span>
          <StatusBadge stats={d} />
        </div>
        <CoverageMeter pct={d.coverage_pct} />
      </div>
      <div className="flex gap-6 text-xs text-gray-400 shrink-0">
        <span className="flex items-center gap-1">
          <Code2 className="h-3 w-3" /> {d.code_entities}
        </span>
        <span className="flex items-center gap-1">
          <FileText className="h-3 w-3" /> {d.requirement_docs}
        </span>
        <span className="flex items-center gap-1">
          <Share2 className="h-3 w-3" /> {d.linked_edges}
        </span>
      </div>
      <ChevronRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors shrink-0" />
    </Link>
  );
}

function ProductCard({ product }: { product: ProductKGSummary }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
      {/* Product header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
            <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="text-left">
            <h2 className="font-bold text-gray-900 dark:text-white">{product.product}</h2>
            <p className="text-xs text-gray-400">
              {product.total_domains} domain{product.total_domains !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Summary stats */}
          <div className="hidden md:flex gap-6 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Code2 className="h-3.5 w-3.5" />
              {product.total_code_entities} code
            </span>
            <span className="flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              {product.total_requirement_docs} docs
            </span>
            <span className="flex items-center gap-1">
              <Share2 className="h-3.5 w-3.5" />
              {product.total_linked_edges} links
            </span>
          </div>

          {/* Overall coverage ring-ish indicator */}
          <div className="text-right">
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {product.overall_coverage_pct}%
            </p>
            <p className="text-xs text-gray-400">coverage</p>
          </div>

          {expanded ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Domain list */}
      {expanded && (
        <>
          {/* Column headers */}
          <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
            <span className="flex-1 text-xs font-semibold text-gray-400 uppercase tracking-wide pl-0">Domain</span>
            <div className="flex gap-6 text-xs font-semibold text-gray-400 uppercase tracking-wide shrink-0 pr-8">
              <span className="flex items-center gap-1"><Code2 className="h-3 w-3" /> Code</span>
              <span className="flex items-center gap-1"><FileText className="h-3 w-3" /> Docs</span>
              <span className="flex items-center gap-1"><Share2 className="h-3 w-3" /> Links</span>
            </div>
          </div>

          <div className="divide-y divide-gray-50 dark:divide-gray-800/50 px-2 py-1">
            {product.domains.length === 0 && (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">No domains registered for this product.</p>
            )}
            {product.domains.map((d) => (
              <DomainRow key={d.domain} d={d} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function KGContext() {
  const fetcher = useCallback(() => api.getKGProducts(), []);
  const { data: products, loading, error } = usePolling<ProductKGSummary[]>(fetcher, 30000);

  const totalCode = products?.reduce((a, p) => a + p.total_code_entities, 0) ?? 0;
  const totalDocs = products?.reduce((a, p) => a + p.total_requirement_docs, 0) ?? 0;
  const totalLinks = products?.reduce((a, p) => a + p.total_linked_edges, 0) ?? 0;
  const totalDomains = products?.reduce((a, p) => a + p.total_domains, 0) ?? 0;

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
            <GitBranch className="h-7 w-7 text-blue-500" />
            Knowledge Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Product-level knowledge graph — code entities linked to business requirements
          </p>
        </div>
        <Link
          to="/kg/ingest"
          className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <DatabaseZap className="h-4 w-4" /> Ingest Data
        </Link>
      </div>

      {/* Top-level stats */}
      {!loading && !error && products && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Products", value: products.length, icon: Database, color: "text-blue-500" },
            { label: "Domains", value: totalDomains, icon: GitBranch, color: "text-violet-500" },
            { label: "Code Entities", value: totalCode, icon: Code2, color: "text-blue-500" },
            { label: "Requirements", value: totalDocs, icon: FileText, color: "text-emerald-500" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`h-4 w-4 ${color}`} />
                <p className="text-xs text-gray-500">{label}</p>
              </div>
              <p className="text-2xl font-bold">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-7 w-7 animate-spin text-blue-400" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-4 flex items-center gap-3 text-red-600 dark:text-red-400">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div>
            <p className="font-medium">Could not load KG data</p>
            <p className="text-sm mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Product cards */}
      {!loading && !error && products && (
        <>
          {products.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-12 text-center">
              <Database className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="font-medium text-gray-500">No KG data found</p>
              <p className="text-sm text-gray-400 mt-1">
                Run <code className="font-mono bg-gray-100 dark:bg-gray-800 px-1 rounded">keel kg ingest</code> and{" "}
                <code className="font-mono bg-gray-100 dark:bg-gray-800 px-1 rounded">keel kg link</code> to populate the knowledge graph.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {products.map((p) => (
                <ProductCard key={p.product} product={p} />
              ))}
            </div>
          )}

          {/* Global links summary */}
          {totalLinks > 0 && (
            <p className="text-xs text-gray-400 text-right">
              {totalLinks} total code→requirement edges across all domains
            </p>
          )}
        </>
      )}
    </div>
  );
}
