import { useCallback, useEffect, useRef, useState } from "react";
import { X, Loader2, AlertCircle } from "lucide-react";
import ForceGraph2D from "react-force-graph-2d";
import { api, type KGNeighborhood, type KGGraphNode } from "@/lib/api";

interface Props {
  nodeId: string;
  nodeName: string;
  nodeType: "code" | "document";
  domain: string;
  onClose: () => void;
}

const NODE_COLORS: Record<string, string> = {
  code: "#6366f1",
  document: "#10b981",
};

const EDGE_COLORS: Record<string, string> = {
  IMPLEMENTS: "#6366f1",
  REFERENCES: "#f59e0b",
  TESTED_BY: "#10b981",
  CONFIGURES: "#8b5cf6",
};

export function KGGraphPanel({ nodeId, nodeName, nodeType, domain, onClose }: Props) {
  const [data, setData] = useState<KGNeighborhood | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 480, height: 360 });

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getKGNodeNeighborhood(domain, nodeId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [nodeId, domain]);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDims({ width, height: Math.max(height, 300) });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const graphData = data
    ? {
        nodes: data.nodes.map((n: KGGraphNode) => ({ id: n.id, name: n.label, type: n.node_type })),
        links: data.edges.map((e) => ({
          source: e.source,
          target: e.target,
          label: e.relationship,
          color: EDGE_COLORS[e.relationship] ?? "#94a3b8",
        })),
      }
    : { nodes: [], links: [] };

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name as string;
      const fontSize = Math.max(10 / globalScale, 4);
      const r = node.id === nodeId ? 8 : 6;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = NODE_COLORS[node.type] ?? "#94a3b8";
      ctx.fill();
      if (node.id === nodeId) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      ctx.font = `${fontSize}px sans-serif`;
      ctx.fillStyle = "#e2e8f0";
      ctx.textAlign = "center";
      ctx.fillText(label.length > 22 ? label.slice(0, 20) + "…" : label, node.x, node.y + r + fontSize);
    },
    [nodeId]
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <aside className="relative z-10 flex flex-col w-full max-w-xl bg-gray-900 border-l border-gray-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">
              {nodeType === "code" ? "Code Entity" : "Requirement Doc"}
            </p>
            <h2 className="text-base font-semibold text-white truncate max-w-xs" title={nodeName}>
              {nodeName}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Legend */}
        <div className="px-5 py-2 border-b border-gray-800 flex gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full bg-indigo-500" /> Code
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full bg-emerald-500" /> Document
          </span>
          {Object.entries(EDGE_COLORS).map(([rel, color]) => (
            <span key={rel} className="flex items-center gap-1" style={{ color }}>
              — {rel}
            </span>
          ))}
        </div>

        {/* Graph area */}
        <div ref={containerRef} className="flex-1 bg-gray-950 relative min-h-0">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="h-6 w-6 text-indigo-400 animate-spin" />
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex items-center gap-2 text-red-400 text-sm">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            </div>
          )}
          {!loading && !error && data && (
            <ForceGraph2D
              graphData={graphData}
              width={dims.width}
              height={dims.height}
              backgroundColor="#030712"
              nodeCanvasObject={nodeCanvasObject}
              nodeCanvasObjectMode={() => "replace"}
              linkColor={(link: any) => link.color}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              linkLabel={(link: any) => link.label}
              cooldownTicks={80}
            />
          )}
        </div>

        {/* Stats footer */}
        {data && (
          <div className="px-5 py-3 border-t border-gray-700 text-xs text-gray-400 flex gap-6">
            <span>{data.nodes.length} nodes</span>
            <span>{data.edges.length} edges</span>
            <span className="ml-auto font-mono truncate max-w-[200px]" title={nodeId}>
              id: {nodeId}
            </span>
          </div>
        )}
      </aside>
    </div>
  );
}
