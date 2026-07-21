import { useEffect, useMemo, useState } from "react";
import { GitBranch, Loader2, Boxes, AlertCircle } from "lucide-react";
import { GraphCanvas } from "@/components/GraphCanvas";
import { api, type IngestableDomain, type KGNeighborhood } from "@/lib/api";

/**
 * KG Graph — the frontend equivalent of `keel kg visualize` (which only
 * generated a Neo4j HTML file). Renders a whole-domain knowledge graph:
 * code entities linked to requirement docs.
 */

export function KGGraph({ embedded = false }: { embedded?: boolean } = {}) {
  const [domains, setDomains] = useState<IngestableDomain[]>([]);
  const [domain, setDomain] = useState("");
  const [data, setData] = useState<KGNeighborhood | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listIngestableDomains().then(setDomains).catch(() => setDomains([]));
  }, []);

  const load = async (d: string) => {
    setDomain(d);
    setData(null);
    setError(null);
    setLoading(true);
    try {
      const r = await fetch(`/api/kg/graph?domain=${encodeURIComponent(d)}&limit=600`);
      if (!r.ok) throw new Error((await r.json()).detail ?? `status ${r.status}`);
      setData(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const nodes = useMemo(
    () => (data?.nodes ?? []).map((n) => ({ id: n.id, name: n.label, group: n.node_type })),
    [data]
  );
  const links = useMemo(
    () => (data?.edges ?? []).map((e) => ({ source: e.source, target: e.target, label: e.relationship })),
    [data]
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
            <GitBranch className="h-7 w-7 text-blue-500" /> KG Graph
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Visualize the domain knowledge graph — code entities linked to requirements
          </p>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Domain</label>
          <select
            value={domain}
            onChange={(e) => load(e.target.value)}
            className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">All domains</option>
            {domains.map((d) => (
              <option key={d.slug} value={d.slug}>{d.slug}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full" style={{ background: "#6366f1" }} /> Code</span>
          <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full" style={{ background: "#10b981" }} /> Document</span>
        </div>

        {loading && (
          <div className="h-64 flex items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading graph…
          </div>
        )}
        {error && (
          <div className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">{error}</div>
        )}
        {data && (
          data.nodes.length === 0 ? (
            <p className="text-sm text-gray-500 flex items-center gap-1.5 py-8 justify-center">
              <AlertCircle className="h-4 w-4" />
              No graph data. Ingest with the KG Onboarding wizard and link with{" "}
              <code className="font-mono">keel kg link</code> (Neo4j provider required).
            </p>
          ) : (
            <>
              <p className="text-xs text-gray-500 flex items-center gap-1.5">
                <Boxes className="h-3.5 w-3.5" /> {data.nodes.length} nodes · {data.edges.length} edges
              </p>
              <GraphCanvas nodes={nodes} links={links} height={520} />
              <p className="text-[11px] text-gray-400">Zoom in for labels; drag nodes to explore.</p>
            </>
          )
        )}
      </div>
    </div>
  );
}
