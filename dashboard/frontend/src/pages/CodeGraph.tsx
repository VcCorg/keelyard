import { useEffect, useMemo, useState } from "react";
import { FolderGit2, Loader2, Boxes, RefreshCw, AlertCircle } from "lucide-react";
import { GraphCanvas } from "@/components/GraphCanvas";

/**
 * Code Graph — visualize a repo's graphify structural graph for review.
 * `keel code onboard --graphify` writes graphify-out/graph.json; this reads it
 * back so a dev/lead can validate what was captured before it feeds the KG.
 */

interface CodeRepo {
  name: string;
  path: string;
  exists: boolean;
  has_graph: boolean;
  languages: string[];
  domain?: string | null;
}
interface CodeGraphData {
  repo: string;
  nodes: { id: string; label: string; kind: string; group: string }[];
  edges: { source: string; target: string; relationship: string }[];
  truncated: boolean;
  node_total: number;
  edge_total: number;
}

export function CodeGraph({ embedded = false }: { embedded?: boolean } = {}) {
  const [repos, setRepos] = useState<CodeRepo[]>([]);
  const [path, setPath] = useState("");
  const [graph, setGraph] = useState<CodeGraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRepos = () =>
    fetch("/api/code/graphs").then((r) => r.json()).then(setRepos).catch(() => setRepos([]));
  useEffect(() => { loadRepos(); }, []);

  const loadGraph = async (p: string) => {
    setPath(p);
    setGraph(null);
    setError(null);
    if (!p) return;
    setLoading(true);
    try {
      const r = await fetch(`/api/code/graph?path=${encodeURIComponent(p)}`);
      if (!r.ok) throw new Error((await r.json()).detail ?? `status ${r.status}`);
      setGraph(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const nodes = useMemo(
    () => (graph?.nodes ?? []).map((n) => ({ id: n.id, name: n.label, group: n.group || n.kind })),
    [graph]
  );
  const links = useMemo(
    () => (graph?.edges ?? []).map((e) => ({ source: e.source, target: e.target, label: e.relationship })),
    [graph]
  );
  const withGraph = repos.filter((r) => r.has_graph);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-end gap-3">
        {!embedded && (
          <div className="mr-auto">
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
              <FolderGit2 className="h-7 w-7 text-blue-500" /> Code Graph
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Review the graphify structural graph captured during code onboarding
            </p>
          </div>
        )}
        <button onClick={loadRepos} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Onboarded repository</label>
          <select
            value={path}
            onChange={(e) => loadGraph(e.target.value)}
            className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">Select a repo with a graphify graph…</option>
            {withGraph.map((r) => (
              <option key={r.path} value={r.path}>
                {r.name}{r.domain ? ` · ${r.domain}` : ""} ({r.languages.slice(0, 3).join(", ") || "code"})
              </option>
            ))}
          </select>
          {repos.length > 0 && withGraph.length === 0 && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5" />
              No onboarded repo has a graphify graph yet. Re-onboard with the Graphify option
              (Repository page), or run <code className="font-mono">graphify update</code> in the repo.
            </p>
          )}
        </div>

        {loading && (
          <div className="h-64 flex items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading graph…
          </div>
        )}
        {error && (
          <div className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">{error}</div>
        )}
        {graph && (
          <>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1.5"><Boxes className="h-3.5 w-3.5" /> {graph.node_total} nodes · {graph.edge_total} edges</span>
              {graph.truncated && (
                <span className="text-amber-600 dark:text-amber-400">
                  showing the {graph.nodes.length} most-connected nodes (graph truncated for the browser)
                </span>
              )}
            </div>
            <GraphCanvas nodes={nodes} links={links} height={520} />
            <p className="text-[11px] text-gray-400">
              Colored by module/kind. Zoom in for labels; drag to explore. Scroll to zoom.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
