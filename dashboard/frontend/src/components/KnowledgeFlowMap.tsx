import { useMemo } from "react";
import { AlertTriangle, FileText, GitBranch, Layers } from "lucide-react";
import type { KnowledgeMap, KnowledgeNode } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Where a domain's knowledge came from, and where drift is entering it.
 *
 * Three columns — sources, instruction kinds, context artifacts — with a ribbon
 * per hop whose thickness is the number of instructions that travelled it.
 * Staleness propagates *forward*: a page that moved upstream marks every ribbon
 * and artifact built from it, which is the property a table of counts cannot
 * show and the reason this is drawn rather than tabulated.
 *
 * Only accepted instructions become ribbons. An unreviewed instruction is not
 * yet knowledge, and drawing it would overstate what the domain knows.
 */

const COLUMN = { source: 0, kind: 1, artifact: 2 } as const;
const COLUMN_LABELS = ["Sources", "Instructions", "Context"] as const;

const NODE_H = 34;
const NODE_GAP = 10;
const NODE_W = 168;
const COL_GAP = 96;
const PAD_TOP = 28;

type Placed = KnowledgeNode & { x: number; y: number };

function ribbon(x1: number, y1: number, x2: number, y2: number): string {
  const mid = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`;
}

export function KnowledgeFlowMap({ map }: { map: KnowledgeMap }) {
  const { placed, byId, width, height } = useMemo(() => {
    const columns: KnowledgeNode[][] = [[], [], []];
    for (const node of map.nodes) columns[COLUMN[node.group]].push(node);

    const placedNodes: Placed[] = [];
    columns.forEach((column, index) => {
      const x = index * (NODE_W + COL_GAP);
      column.forEach((node, row) => {
        placedNodes.push({ ...node, x, y: PAD_TOP + row * (NODE_H + NODE_GAP) });
      });
    });

    const tallest = Math.max(1, ...columns.map((c) => c.length));
    return {
      placed: placedNodes,
      byId: new Map(placedNodes.map((n) => [n.id, n])),
      width: 3 * NODE_W + 2 * COL_GAP,
      height: PAD_TOP + tallest * (NODE_H + NODE_GAP) + 8,
    };
  }, [map]);

  if (!map.nodes.length) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Nothing extracted yet. Run <span className="font-mono">extract</span>, then
        accept instructions to see how knowledge reaches this domain.
      </p>
    );
  }

  const maxFlow = Math.max(1, ...map.flows.map((f) => f.count));

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width={width}
          height={height}
          role="img"
          aria-label={`Knowledge flow for ${map.domain}: ${map.totals.sources ?? 0} sources feeding ${map.totals.accepted ?? 0} accepted instructions`}
          className="max-w-full"
        >
          {COLUMN_LABELS.map((label, index) => (
            <text
              key={label}
              x={index * (NODE_W + COL_GAP)}
              y={14}
              className="fill-gray-500 dark:fill-gray-400 text-[11px] font-medium uppercase tracking-wide"
            >
              {label}
            </text>
          ))}

          {map.flows.map((flow) => {
            const from = byId.get(flow.source);
            const to = byId.get(flow.target);
            if (!from || !to) return null;
            return (
              <path
                key={`${flow.source}->${flow.target}`}
                d={ribbon(
                  from.x + NODE_W,
                  from.y + NODE_H / 2,
                  to.x,
                  to.y + NODE_H / 2
                )}
                fill="none"
                strokeWidth={2 + (flow.count / maxFlow) * 8}
                strokeLinecap="round"
                strokeDasharray={flow.stale ? "6 4" : undefined}
                className={cn(
                  flow.stale
                    ? "stroke-amber-500/70"
                    : "stroke-sky-500/40 dark:stroke-sky-400/40"
                )}
              >
                <title>
                  {flow.count} instruction{flow.count === 1 ? "" : "s"}
                  {flow.stale ? " — source has moved upstream" : ""}
                </title>
              </path>
            );
          })}

          {placed.map((node) => (
            <g key={node.id}>
              <rect
                x={node.x}
                y={node.y}
                width={NODE_W}
                height={NODE_H}
                rx={6}
                className={cn(
                  "stroke-[1.5]",
                  node.stale
                    ? "fill-amber-50 stroke-amber-400 dark:fill-amber-950/40 dark:stroke-amber-600"
                    : "fill-white stroke-gray-300 dark:fill-gray-900 dark:stroke-gray-700"
                )}
              />
              <text
                x={node.x + 10}
                y={node.y + 15}
                className="fill-gray-900 dark:fill-gray-100 text-[11px] font-medium"
              >
                {node.label.length > 24 ? `${node.label.slice(0, 23)}…` : node.label}
              </text>
              <text
                x={node.x + 10}
                y={node.y + 27}
                className="fill-gray-500 dark:fill-gray-400 text-[10px]"
              >
                {node.group === "artifact"
                  ? node.reviewed
                    ? "reviewed"
                    : node.stale
                      ? "placeholder"
                      : "unreviewed"
                  : [
                      `${node.count} instruction${node.count === 1 ? "" : "s"}`,
                      node.held ? `${node.held} held` : "",
                      node.pending ? `${node.pending} pending` : "",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
              </text>
              <title>{node.label}</title>
            </g>
          ))}
        </svg>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-gray-500 dark:text-gray-400">
        <span className="flex items-center gap-1.5">
          <GitBranch className="h-3.5 w-3.5" /> {map.totals.sources ?? 0} source
          {map.totals.sources === 1 ? "" : "s"}
        </span>
        <span className="flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5" /> {map.totals.accepted ?? 0} accepted
        </span>
        <span className="flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5" /> {map.totals.artifacts ?? 0} context file
          {map.totals.artifacts === 1 ? "" : "s"}
        </span>
        {(map.totals.held ?? 0) > 0 && (
          <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5" /> {map.totals.held} held — carry
            identifiers, review at source
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <svg width="22" height="8" aria-hidden="true">
            <line
              x1="0"
              y1="4"
              x2="22"
              y2="4"
              strokeWidth="3"
              strokeDasharray="6 4"
              className="stroke-amber-500/70"
            />
          </svg>
          source moved upstream
        </span>
      </div>
    </div>
  );
}
