import { useState, type ComponentType } from "react";
import { NavLink, Outlet } from "react-router-dom";
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
  ChevronDown,
  ChevronRight,
  User as UserIcon,
  Sun,
  Moon,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  Wand2,
  Workflow,
  Cpu,
  Search,
  Plug,
  Blocks,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useUser,
  initials,
  workspaceLabel,
  type UserRole,
} from "@/context/UserContext";
import { useSetup } from "@/context/SetupContext";
import { SetupPanel } from "@/components/SetupPanel";
import { IntegrationStatusBar } from "@/components/IntegrationStatusBar";

type NavItem = {
  to: string;
  icon: ComponentType<{ className?: string }>;
  label: string;
  /** If set, renders as a button that triggers an action instead of navigating. */
  action?: "setup";
  /** If set, only shown to users with this role or higher. */
  minRole?: UserRole;
};
type NavSubgroup = {
  label: string;
  icon?: ComponentType<{ className?: string }>;
  items: NavItem[];
  /** If set, only shown to users with this role or higher. */
  minRole?: UserRole;
};
type NavGroup = {
  label: string;
  items: NavItem[];
  /** Nested, indented sub-sections rendered under this group's items. */
  subgroups?: NavSubgroup[];
  /** Top-level items rendered AFTER the subgroups (e.g. trailing shortcuts). */
  footerItems?: NavItem[];
  /** If set, only shown to users with this role or higher. */
  minRole?: UserRole;
};

const ROLE_RANK: Record<UserRole, number> = { member: 0, lead: 1, admin: 2 };

const navGroups: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/activity", icon: Activity, label: "Activity" },
    ],
  },
  {
    label: "Ideate",
    items: [{ to: "/ideate", icon: Lightbulb, label: "Requirements" }],
  },
  {
    label: "Work",
    items: [
      { to: "/tasks", icon: ListTodo, label: "Tasks" },
      { to: "/assignments", icon: ClipboardList, label: "Assignments", minRole: "lead" },
    ],
  },
  {
    label: "Build",
    items: [
      { to: "/code-onboard", icon: FolderGit2, label: "Repository" },
      { to: "/skills", icon: Package, label: "Skills" },
    ],
    subgroups: [
      {
        label: "Devin",
        icon: DevinBot,
        items: [
          { to: "/devin", icon: DevinBot, label: "Devin Sessions" },
          { to: "/snapshots", icon: Camera, label: "Snapshots", minRole: "lead" },
        ],
      },
    ],
  },
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
    label: "Governance",
    minRole: "lead",
    items: [],
    subgroups: [
      {
        label: "Onboarding",
        icon: Boxes,
        items: [
          { to: "/onboarding", icon: Boxes, label: "Domain", minRole: "lead" },
          { to: "/workspaces", icon: FolderOpen, label: "Workspaces" },
        ],
      },
      {
        label: "Registry",
        icon: Package,
        items: [
          { to: "/skills/personas", icon: Sparkles, label: "Persona Skills" },
          { to: "/marketplace", icon: Store, label: "Marketplace" },
        ],
      },
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
    label: "Admin",
    minRole: "admin",
    items: [
      { to: "/people", icon: Users, label: "People" },
      { to: "/shared/agents", icon: Share2, label: "Shared Agents" },
      { to: "/shared/kg", icon: BrainCircuit, label: "Shared KG" },
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
];

function WorkspaceLabel() {
  const { user } = useUser();
  const Icon = user.role === "admin" ? Users : FolderOpen;
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-semibold text-gray-700 dark:text-gray-200">
      <Icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      <span className="truncate">{workspaceLabel(user.role)}</span>
    </div>
  );
}

function NavItemLink({ item }: { item: NavItem }) {
  const { to, icon: Icon, label, action } = item;
  const { openPanel, status, loading } = useSetup();
  if (action === "setup") {
    const ready = status?.ready ?? false;
    const cliMissing = status ? !status.cli_available : false;
    const pendingRequired = status
      ? status.items.filter((i) => i.required && !i.configured).length
      : 0;
    return (
      <button
        onClick={openPanel}
        title="Initialize / configure the dva CLI"
        className={cn(
          "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
          ready
            ? "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            : "text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/20"
        )}
      >
        <Icon className="h-4 w-4" />
        <span className="flex-1 text-left">{label}</span>
        {loading && !status ? null : cliMissing || !ready ? (
          <span className="flex items-center gap-1 text-xs">
            <AlertTriangle className="h-3.5 w-3.5" />
            {cliMissing ? "install" : `${pendingRequired} left`}
          </span>
        ) : (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        )}
      </button>
    );
  }
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
          isActive
            ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
            : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        )
      }
    >
      <Icon className="h-4 w-4" />
      {label}
    </NavLink>
  );
}

function NavSubgroupSection({ subgroup }: { subgroup: NavSubgroup }) {
  const [open, setOpen] = useState(true);
  const Icon = subgroup.icon;
  return (
    <div className="mt-1 ml-2 pl-2 border-l border-gray-200 dark:border-gray-800">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
      >
        {Icon && <Icon className="h-3 w-3" />}
        {subgroup.label}
        {open ? (
          <ChevronDown className="h-3 w-3 ml-auto" />
        ) : (
          <ChevronRight className="h-3 w-3 ml-auto" />
        )}
      </button>
      {open && (
        <div className="space-y-0.5 mt-0.5">
          {subgroup.items.map((item) => (
            <NavItemLink key={item.to} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function NavGroupSection({ group }: { group: NavGroup }) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
      >
        {group.label}
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>
      {open && (
        <div className="space-y-0.5 mt-0.5">
          {group.items.map((item) => (
            <NavItemLink key={item.to} item={item} />
          ))}
          {group.subgroups?.map((sg) => (
            <NavSubgroupSection key={sg.label} subgroup={sg} />
          ))}
          {group.footerItems?.map((item) => (
            <NavItemLink key={item.to} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}


export function Layout() {
  const { user, theme, toggleTheme, updateUser, auth } = useUser();
  const { panelOpen, closePanel } = useSetup();

  const meetsRole = (min?: UserRole) =>
    !min || ROLE_RANK[user.role] >= ROLE_RANK[min];
  const isVisible = (x: { minRole?: UserRole }) => meetsRole(x.minRole);

  const visibleGroups = navGroups
    .filter(isVisible)
    .map((g) => ({
      ...g,
      items: g.items.filter(isVisible),
      subgroups: (g.subgroups ?? [])
        .filter(isVisible)
        .map((sg) => ({ ...sg, items: sg.items.filter(isVisible) }))
        .filter((sg) => sg.items.length > 0),
    }))
    .filter((g) => g.items.length > 0 || g.subgroups.length > 0);

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Sidebar */}
      <aside className="w-60 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800 space-y-3">
          <div>
            <h1 className="text-lg font-bold tracking-tight">Agent Playground</h1>
            <p className="text-xs text-gray-500 mt-0.5">Agentic Platform</p>
          </div>
          <WorkspaceLabel />
        </div>

        <nav className="flex-1 px-3 py-4 space-y-3 overflow-y-auto">
          {visibleGroups.map((g) => (
            <NavGroupSection key={g.label} group={g} />
          ))}
        </nav>

        <div className="px-3 py-3 border-t border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3 px-2 py-1.5 rounded-lg">
            <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-xs font-bold text-blue-700 dark:text-blue-300">
              {user.name ? initials(user.name) : <UserIcon className="h-4 w-4" />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{user.name}</p>
              {auth.provider === "dev" ? (
                <select
                  value={user.role}
                  onChange={(e) => updateUser({ role: e.target.value as UserRole })}
                  title="Switch role (local dev preview — real roles come from SSO)"
                  className="-ml-0.5 text-[11px] bg-transparent text-gray-400 capitalize outline-none cursor-pointer hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <option value="member">member</option>
                  <option value="lead">lead</option>
                  <option value="admin">admin</option>
                </select>
              ) : (
                <p
                  className="text-[11px] text-gray-400 truncate"
                  title={`Identity from ${auth.provider} · roles: ${auth.roles.join(", ") || "none"}`}
                >
                  {auth.roles.join(", ") || "no roles"}
                </p>
              )}
            </div>
            <span
              className={cn(
                "text-[9px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wide",
                auth.provider === "dev"
                  ? "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
              )}
              title={
                auth.provider === "dev"
                  ? "Local dev identity — set DVA_AUTH_MODE=forward-auth behind an SSO proxy"
                  : `Enterprise SSO via ${auth.provider}`
              }
            >
              {auth.provider === "dev" ? "dev" : "SSO"}
            </span>
            <button
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              aria-label="Toggle theme"
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
          <p className="px-2 pt-2 text-[10px] text-gray-400">v0.1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto flex flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-end gap-3 px-6 py-2.5 border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-950/80 backdrop-blur">
          <IntegrationStatusBar />
        </header>
        <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>

      {panelOpen && <SetupPanel onClose={closePanel} />}
    </div>
  );
}
