import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

/**
 * Reusable force-graph canvas for any {nodes, links} graph — powers the KG
 * domain viewer and the graphify code-graph viewer. Nodes are colored by
 * `group` (stable hash → palette); labels render at readable zoom.
 */

export interface GraphNode {
  id: string;
  name: string;
  group?: string;
}
export interface GraphLink {
  source: string;
  target: string;
  label?: string;
}

const PALETTE = [
  "#6366f1", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444",
  "#0ea5e9", "#ec4899", "#14b8a6", "#a3a3a3", "#eab308",
];

function colorFor(group: string): string {
  let h = 0;
  for (let i = 0; i < group.length; i++) h = (h * 31 + group.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

export function GraphCanvas({
  nodes,
  links,
  height = 460,
  onNodeClick,
}: {
  nodes: GraphNode[];
  links: GraphLink[];
  height?: number;
  onNodeClick?: (id: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    if (!ref.current) return;
    const obs = new ResizeObserver((e) => setWidth(e[0].contentRect.width));
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, scale: number) => {
      const r = 5;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = colorFor(node.group ?? "node");
      ctx.fill();
      if (scale > 1.4) {
        const fs = Math.max(9 / scale, 3);
        ctx.font = `${fs}px sans-serif`;
        ctx.fillStyle = "#94a3b8";
        ctx.textAlign = "center";
        const label = node.name as string;
        ctx.fillText(label.length > 20 ? label.slice(0, 18) + "…" : label, node.x, node.y + r + fs);
      }
    },
    []
  );

  return (
    <div ref={ref} className="w-full rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 overflow-hidden" style={{ height }}>
      <ForceGraph2D
        graphData={{ nodes: nodes as any, links: links as any }}
        width={width}
        height={height}
        backgroundColor="rgba(0,0,0,0)"
        nodeRelSize={5}
        nodeCanvasObject={nodeCanvasObject}
        nodeLabel={(n: any) => `${n.name}${n.group ? ` · ${n.group}` : ""}`}
        linkColor={() => "rgba(148,163,184,0.35)"}
        linkDirectionalArrowLength={2.5}
        linkDirectionalArrowRelPos={1}
        onNodeClick={(n: any) => onNodeClick?.(n.id)}
        cooldownTicks={80}
      />
    </div>
  );
}
