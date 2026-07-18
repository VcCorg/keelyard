import type { ComponentType } from "react";
import {
  LayoutDashboard,
  Bot,
  Server,
  Activity,
  MessageSquare,
  Camera,
  FolderKanban,
  TerminalSquare,
  Package,
  Sparkles,
  Store,
  Rocket,
  GitBranch,
  Boxes,
  DatabaseZap,
  FileStack,
  Database,
  FolderGit2,
  FolderOpen,
  FlaskConical,
  SquareTerminal,
  Bot as DevinBot,
  ListTodo,
  ClipboardList,
  Users,
  Share2,
  BrainCircuit,
  Wrench,
  Wand2,
  Workflow,
  Cpu,
  Search,
  Plug,
  Blocks,
  Lightbulb,
  ShieldCheck,
} from "lucide-react";
import type { UserRole } from "@/context/UserContext";

export type NavItem = {
  to: string;
  icon: ComponentType<{ className?: string }>;
  label: string;
  /** If set, renders as a button that triggers an action instead of navigating. */
  action?: "setup";
  /** Default gate: only shown to this role or higher (admin may override). */
  minRole?: UserRole;
};
export type NavSubgroup = {
  label: string;
  icon?: ComponentType<{ className?: string }>;
  items: NavItem[];
  minRole?: UserRole;
};
export type NavGroup = {
  label: string;
  items: NavItem[];
  subgroups?: NavSubgroup[];
  footerItems?: NavItem[];
  minRole?: UserRole;
};

export const UI_ROLES: UserRole[] = ["member", "lead", "admin"];
export const ROLE_RANK: Record<UserRole, number> = { member: 0, lead: 1, admin: 2 };

/** Default allowed roles for a node, derived from its `minRole`. */
export function defaultRolesFor(minRole?: UserRole): UserRole[] {
  const min = minRole ? ROLE_RANK[minRole] : 0;
  return UI_ROLES.filter((r) => ROLE_RANK[r] >= min);
}

/** Stable ids so admin overrides survive nav edits. */
export const groupId = (label: string) => `group:${label}`;
export const subgroupId = (label: string) => `subgroup:${label}`;
export const itemId = (to: string) => `item:${to}`;

/**
 * Effective allowed roles for a node: an admin override wins; otherwise the
 * `minRole`-derived default. Admin is always included (never self-lock-out).
 */
export function allowedRoles(
  id: string,
  minRole: UserRole | undefined,
  overrides: Record<string, string[]>
): UserRole[] {
  const ov = overrides[id];
  const roles = ov && ov.length ? (ov.filter((r) => UI_ROLES.includes(r as UserRole)) as UserRole[]) : defaultRolesFor(minRole);
  return roles.includes("admin") ? roles : [...roles, "admin"];
}

export function roleCanSee(
  role: UserRole,
  id: string,
  minRole: UserRole | undefined,
  overrides: Record<string, string[]>
): boolean {
  return allowedRoles(id, minRole, overrides).includes(role);
}

export const navGroups: NavGroup[] = [
  // Lifecycle reading order: govern → know → ideate → build → track.
  {
    label: "Overview",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/activity", icon: Activity, label: "Activity" },
    ],
  },
  // Governance right after the dashboard: guardrails frame everything below.
  {
    label: "Governance",
    minRole: "lead",
    items: [
      { to: "/onboarding", icon: Boxes, label: "Domain", minRole: "lead" },
      { to: "/workspaces", icon: FolderOpen, label: "Workspaces" },
      { to: "/skills/personas", icon: Sparkles, label: "Persona Skills" },
      { to: "/marketplace", icon: Store, label: "Marketplace" },
    ],
  },
  {
    label: "Knowledge",
    minRole: "lead",
    items: [
      { to: "/kg", icon: GitBranch, label: "KG Context" },
      { to: "/kg/ingest", icon: DatabaseZap, label: "KG Ingest" },
      { to: "/kg/okf", icon: FileStack, label: "OKF Generation", minRole: "admin" },
      { to: "/data", icon: Database, label: "Data Sources" },
    ],
  },
  {
    label: "Ideate",
    items: [{ to: "/ideate", icon: Lightbulb, label: "Requirements" }],
  },
  // Build directly after Ideate: requirements flow straight into construction.
  {
    label: "Build",
    items: [
      { to: "/code-onboard", icon: FolderGit2, label: "Repository" },
      { to: "/skills", icon: Package, label: "Skills" },
      { to: "/devin", icon: DevinBot, label: "Devin Sessions" },
      { to: "/snapshots", icon: Camera, label: "Snapshots", minRole: "lead" },
    ],
  },
  {
    label: "Work",
    items: [
      { to: "/tasks", icon: ListTodo, label: "Tasks" },
      { to: "/assignments", icon: ClipboardList, label: "Assignments", minRole: "lead" },
    ],
  },
  // Agent Builder sits directly above Platform: agent construction is a
  // platform-adjacent capability, not part of the core code journey.
  {
    label: "Agent Builder",
    minRole: "lead",
    items: [
      { to: "/quickstart", icon: Wand2, label: "Quickstart" },
      { to: "/projects", icon: FolderKanban, label: "Agent Projects" },
      { to: "/canvas", icon: Workflow, label: "Project Canvas" },
      { to: "/agents", icon: Bot, label: "Agents" },
      { to: "/eval", icon: FlaskConical, label: "Evaluation" },
    ],
    subgroups: [
      {
        label: "Components",
        icon: Blocks,
        items: [
          { to: "/models", icon: Cpu, label: "Models" },
          { to: "/tools", icon: Wrench, label: "Tools" },
          { to: "/retrievers", icon: Search, label: "Retrievers" },
          { to: "/databases", icon: Database, label: "Databases" },
          { to: "/data", icon: Plug, label: "Data Sources" },
          { to: "/mcp", icon: Server, label: "MCP Connectors" },
          { to: "/skills", icon: Package, label: "Skills" },
        ],
      },
    ],
  },
  {
    label: "Platform",
    minRole: "lead",
    items: [
      { to: "/mcp", icon: Server, label: "MCP Servers" },
      { to: "/deployments", icon: Rocket, label: "Deployments" },
    ],
    subgroups: [
      {
        label: "CLI",
        icon: SquareTerminal,
        items: [
          { to: "/cli", icon: SquareTerminal, label: "CLI Console" },
          { to: "#cli-setup", icon: Wrench, label: "CLI Setup", action: "setup" },
        ],
      },
    ],
    footerItems: [
      { to: "/terminal", icon: TerminalSquare, label: "Terminal" },
      { to: "/chat", icon: MessageSquare, label: "Chat" },
    ],
  },
  // Admin is always LAST and admin-only.
  {
    label: "Admin",
    minRole: "admin",
    items: [
      { to: "/admin", icon: ShieldCheck, label: "Administration" },
      { to: "/people", icon: Users, label: "People" },
      { to: "/shared/agents", icon: Share2, label: "Shared Agents" },
      { to: "/shared/kg", icon: BrainCircuit, label: "Shared KG" },
    ],
  },
];

/** A flat, admin-editable catalogue of every controllable nav node. */
export type NavCatalogNode = {
  id: string;
  label: string;
  kind: "group" | "subgroup" | "item";
  group: string;               // owning top-level group label
  minRole?: UserRole;
  defaultRoles: UserRole[];
};

export function buildNavCatalog(): NavCatalogNode[] {
  const out: NavCatalogNode[] = [];
  const seen = new Set<string>();
  const push = (n: NavCatalogNode) => {
    if (seen.has(n.id)) return;
    seen.add(n.id);
    out.push(n);
  };
  for (const g of navGroups) {
    push({ id: groupId(g.label), label: g.label, kind: "group", group: g.label,
           minRole: g.minRole, defaultRoles: defaultRolesFor(g.minRole) });
    for (const it of g.items) {
      if (it.action) continue;
      push({ id: itemId(it.to), label: it.label, kind: "item", group: g.label,
             minRole: it.minRole, defaultRoles: defaultRolesFor(it.minRole) });
    }
    for (const sg of g.subgroups ?? []) {
      push({ id: subgroupId(sg.label), label: sg.label, kind: "subgroup", group: g.label,
             minRole: sg.minRole, defaultRoles: defaultRolesFor(sg.minRole) });
      for (const it of sg.items) {
        if (it.action) continue;
        push({ id: itemId(it.to), label: it.label, kind: "item", group: g.label,
               minRole: it.minRole, defaultRoles: defaultRolesFor(it.minRole) });
      }
    }
    for (const it of g.footerItems ?? []) {
      if (it.action) continue;
      push({ id: itemId(it.to), label: it.label, kind: "item", group: g.label,
             minRole: it.minRole, defaultRoles: defaultRolesFor(it.minRole) });
    }
  }
  return out;
}
