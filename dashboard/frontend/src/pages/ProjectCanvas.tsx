import { useCallback, useEffect, useMemo, useState, type ComponentType } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ELK from "elkjs/lib/elk.bundled.js";
import {
  Bot,
  FolderKanban,
  Package,
  Server,
  Wrench,
  Boxes,
  Workflow,
  LayoutGrid,
  Loader2,
  RefreshCw,
  Database,
  Search,
  Plug,
  Cpu,
  Brain,
} from "lucide-react";
import { api, type AgentProject } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Project Canvas — an agent designer that visualizes a project's composition
 * as a node graph: project → agent → { skills, tools, MCP servers, domain }.
 *
 * The graph is derived from real project data (discoverProjects + installed
 * skills) and laid out with ELK, so it's a visualization layer over the
 * existing APIs — no new backend.
 */

type Kind =
  | "project"
  | "agent"
  | "model"
  | "skill"
  | "tool"
  | "retriever"
  | "datasource"
  | "database"
  | "mcp"
  | "memory"
  | "domain";

interface ResourceData extends Record<string, unknown> {
  kind: Kind;
  label: string;
  sub?: string;
}

// Ordered so the legend reads as the canonical "ingredients of an agent"
// palette: the bundle, the brain, then the building blocks it composes.
const KIND_META: Record<
  Kind,
  { icon: ComponentType<{ className?: string }>; ring: string; chip: string; dot: string; color: string; label: string }
> = {
  project: {
    icon: FolderKanban,
    ring: "border-indigo-300 dark:border-indigo-700",
    chip: "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
    dot: "bg-indigo-500",
    color: "#6366f1",
    label: "Project",
  },
  agent: {
    icon: Bot,
    ring: "border-blue-300 dark:border-blue-700",
    chip: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    dot: "bg-blue-500",
    color: "#3b82f6",
    label: "Agent",
  },
  model: {
    icon: Cpu,
    ring: "border-fuchsia-300 dark:border-fuchsia-700",
    chip: "bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300",
    dot: "bg-fuchsia-500",
    color: "#d946ef",
    label: "Model / runtime",
  },
  skill: {
    icon: Package,
    ring: "border-emerald-300 dark:border-emerald-700",
    chip: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    dot: "bg-emerald-500",
    color: "#10b981",
    label: "Skill",
  },
  tool: {
    icon: Wrench,
    ring: "border-amber-300 dark:border-amber-700",
    chip: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    dot: "bg-amber-500",
    color: "#f59e0b",
    label: "Tool",
  },
  retriever: {
    icon: Search,
    ring: "border-cyan-300 dark:border-cyan-700",
    chip: "bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
    dot: "bg-cyan-500",
    color: "#06b6d4",
    label: "Retriever",
  },
  datasource: {
    icon: Plug,
    ring: "border-teal-300 dark:border-teal-700",
    chip: "bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
    dot: "bg-teal-500",
    color: "#14b8a6",
    label: "Data source",
  },
  database: {
    icon: Database,
    ring: "border-rose-300 dark:border-rose-700",
    chip: "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
    dot: "bg-rose-500",
    color: "#f43f5e",
    label: "Database",
  },
  mcp: {
    icon: Server,
    ring: "border-slate-300 dark:border-slate-600",
    chip: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    dot: "bg-slate-500",
    color: "#64748b",
    label: "MCP connector",
  },
  memory: {
    icon: Brain,
    ring: "border-orange-300 dark:border-orange-700",
    chip: "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
    dot: "bg-orange-500",
    color: "#f97316",
    label: "Memory",
  },
  domain: {
    icon: Boxes,
    ring: "border-purple-300 dark:border-purple-700",
    chip: "bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    dot: "bg-purple-500",
    color: "#a855f7",
    label: "Domain",
  },
};

const NODE_W = 200;
const NODE_H = 60;

/* ── Custom node ───────────────────────────────────────────────────────── */

function ResourceNode({ data }: NodeProps) {
  const d = data as ResourceData;
  const meta = KIND_META[d.kind];
  const Icon = meta.icon;
  return (
    <div
      className={cn(
        "rounded-xl border-2 bg-white dark:bg-gray-900 shadow-sm px-3 py-2 flex items-center gap-2.5",
        meta.ring
      )}
      style={{ width: NODE_W, height: NODE_H }}
    >
      <Handle type="target" position={Position.Left} className="!bg-gray-400 !w-2 !h-2" />
      <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center shrink-0", meta.chip)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold truncate text-gray-900 dark:text-gray-100">{d.label}</p>
        <p className="text-[10px] text-gray-400 truncate">{d.sub ?? meta.label}</p>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-gray-400 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { resource: ResourceNode };

/* ── ELK layout ────────────────────────────────────────────────────────── */

const elk = new ELK();

async function layoutGraph(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.layered.spacing.nodeNodeBetweenLayers": "90",
      "elk.spacing.nodeNode": "28",
    },
    children: nodes.map((n) => ({ id: n.id, width: NODE_W, height: NODE_H })),
    edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };
  const res = await elk.layout(graph);
  const pos = new Map<string, { x: number; y: number }>();
  (res.children ?? []).forEach((c) => pos.set(c.id, { x: c.x ?? 0, y: c.y ?? 0 }));
  return nodes.map((n) => ({ ...n, position: pos.get(n.id) ?? { x: 0, y: 0 } }));
}

/* ── Graph builder (real project → nodes/edges) ────────────────────────── */

interface InstalledSkill {
  name: string;
  description?: string;
  mcp?: { server?: string } | null;
}

function buildGraph(project: AgentProject, skills: InstalledSkill[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const add = (id: string, kind: Kind, label: string, sub?: string) =>
    nodes.push({ id, type: "resource", position: { x: 0, y: 0 }, data: { kind, label, sub } });
  const link = (source: string, target: string) =>
    edges.push({ id: `${source}->${target}`, source, target, animated: false });

  add("project", "project", project.name, project.domain ? `domain · ${project.domain}` : "project");

  const agentId = "agent";
  add(agentId, "agent", project.agent_type || "agent", project.use_case || undefined);
  link("project", agentId);

  // Model / runtime ingredient — derived from the project's framework.
  if (project.framework) {
    add("model", "model", project.framework, "runtime");
    link(agentId, "model");
  }

  if (project.domain) {
    add("domain", "domain", project.domain, "domain context");
    link(agentId, "domain");
  }

  // Tools — the `memory` tool is surfaced as its own Memory ingredient.
  (project.tools ?? []).forEach((t, i) => {
    const isMemory = /memory/i.test(t);
    const id = `${isMemory ? "memory" : "tool"}-${i}`;
    add(id, isMemory ? "memory" : "tool", t, isMemory ? "memory" : "tool");
    link(agentId, id);
  });

  const mcpSeen = new Map<string, string>(); // server → node id
  skills.forEach((s, i) => {
    const id = `skill-${i}`;
    add(id, "skill", s.name, s.description ? s.description.slice(0, 40) : "skill");
    link(agentId, id);
    const server = s.mcp?.server;
    if (server) {
      let mcpId = mcpSeen.get(server);
      if (!mcpId) {
        mcpId = `mcp-${mcpSeen.size}`;
        mcpSeen.set(server, mcpId);
        add(mcpId, "mcp", server, "MCP server");
      }
      link(id, mcpId);
    }
  });

  return { nodes, edges };
}

/* ── Page ──────────────────────────────────────────────────────────────── */

export function ProjectCanvas() {
  const [projects, setProjects] = useState<AgentProject[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const project = useMemo(() => projects.find((p) => p.path === selected), [projects, selected]);

  useEffect(() => {
    (async () => {
      try {
        const list = await api.discoverProjects();
        setProjects(list);
        if (list.length) setSelected(list[0].path);
      } catch {
        /* non-fatal */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // State is only updated after awaits (mirrors the discover effect) so the
  // graph rebuild never triggers a synchronous setState inside an effect.
  const applyGraph = useCallback(
    async (p: AgentProject) => {
      let skills: InstalledSkill[] = [];
      try {
        const res = await fetch(`/api/skills/project/${encodeURIComponent(p.path)}`);
        if (res.ok) skills = (await res.json()).installed_skills ?? [];
      } catch {
        /* skills are best-effort */
      }
      const { nodes: rawNodes, edges: rawEdges } = buildGraph(p, skills);
      const laid = await layoutGraph(rawNodes, rawEdges);
      setNodes(laid);
      setEdges(rawEdges);
    },
    [setNodes, setEdges]
  );

  useEffect(() => {
    if (project) applyGraph(project);
  }, [project, applyGraph]);

  const autoLayout = useCallback(async () => {
    const laid = await layoutGraph(nodes, edges);
    setNodes(laid);
  }, [nodes, edges, setNodes]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    nodes.forEach((n) => {
      const k = (n.data as ResourceData).kind;
      c[k] = (c[k] ?? 0) + 1;
    });
    return c;
  }, [nodes]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading projects…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
            <Workflow className="h-5 w-5 text-blue-600 dark:text-blue-300" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Project Canvas</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Visualize how an agent project is composed — agent, skills, tools, and MCP servers.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            disabled={!projects.length}
            className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none max-w-[16rem]"
          >
            {projects.length === 0 && <option>No projects found</option>}
            {projects.map((p) => (
              <option key={p.path} value={p.path}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            onClick={autoLayout}
            disabled={!nodes.length}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
            title="Auto-arrange the graph"
          >
            <LayoutGrid className="h-4 w-4" /> Auto layout
          </button>
          <button
            onClick={() => project && applyGraph(project)}
            disabled={!project}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
            title="Rebuild from project"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Legend — the full agent-ingredient palette. Types present in the
          selected project are highlighted with a count; the rest stay listed
          (dimmed) so every component type is identifiable at a glance. */}
      <div className="flex items-center gap-x-3 gap-y-1.5 flex-wrap text-xs">
        <span className="font-medium text-gray-500">Components</span>
        {(Object.keys(KIND_META) as Kind[]).map((k) => {
          const present = !!counts[k];
          return (
            <span
              key={k}
              className={cn(
                "inline-flex items-center gap-1.5",
                present ? "text-gray-700 dark:text-gray-200 font-medium" : "text-gray-400 opacity-70"
              )}
              title={present ? `${counts[k]} in this project` : "Not used in this project"}
            >
              <span className={cn("h-2 w-2 rounded-full", KIND_META[k].dot, !present && "opacity-50")} />
              {KIND_META[k].label}
              {present ? <span className="text-gray-400 font-normal">· {counts[k]}</span> : null}
            </span>
          );
        })}
      </div>

      {/* Canvas */}
      {projects.length === 0 ? (
        <div className="text-center py-20 rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
          <Workflow className="h-10 w-10 mx-auto text-gray-300 dark:text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">
            No agent projects found. Create one from <span className="font-medium">Build → Quickstart</span>.
          </p>
        </div>
      ) : (
        <div className="h-[68vh] rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden bg-gray-50 dark:bg-gray-950">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
            defaultEdgeOptions={{ style: { stroke: "#94a3b8", strokeWidth: 1.5 } }}
          >
            <Background color="#cbd5e1" gap={18} />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => KIND_META[(n.data as ResourceData).kind]?.color ?? "#94a3b8"}
              className="!bg-white dark:!bg-gray-900"
            />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
