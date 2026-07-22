import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  ChevronDown,
  ChevronRight,
  User as UserIcon,
  Sun,
  Moon,
  CheckCircle2,
  AlertTriangle,
  Users,
  FolderOpen,
  Rocket,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useUser,
  initials,
  workspaceLabel,
  type UserRole,
} from "@/context/UserContext";
import { useSetup } from "@/context/SetupContext";
import { useAdminSettings } from "@/context/AdminSettingsContext";
import { SetupPanel } from "@/components/SetupPanel";
import { IntegrationStatusBar } from "@/components/IntegrationStatusBar";
import { HelpButton } from "@/components/HelpButton";
import {
  navGroups,
  groupId,
  subgroupId,
  itemId,
  personaCanSee,
  roleCanSee,
  type NavItem,
  type NavSubgroup,
  type NavGroup,
} from "@/lib/nav";


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
        title="Initialize / configure the keel CLI"
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

function NavSubgroupSection({ subgroup, defaultOpen = false }: { subgroup: NavSubgroup; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
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

function NavGroupSection({
  group,
  defaultOpen = false,
  currentPath,
}: {
  group: NavGroup;
  defaultOpen?: boolean;
  currentPath: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
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
            <NavSubgroupSection
              key={sg.label}
              subgroup={sg}
              defaultOpen={subgroupContainsPath(sg, currentPath)}
            />
          ))}
          {group.footerItems?.map((item) => (
            <NavItemLink key={item.to} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

const pathMatches = (to: string, path: string) =>
  to === "/" ? path === "/" : path === to || path.startsWith(`${to}/`);

/** True when this nav group contains the current route (any items or subgroup items). */
function groupContainsPath(group: NavGroup, path: string): boolean {
  if (group.items.some((it) => !it.action && pathMatches(it.to, path))) return true;
  for (const sg of group.subgroups ?? []) {
    if (sg.items.some((it) => !it.action && pathMatches(it.to, path))) return true;
  }
  return (group.footerItems ?? []).some((it) => !it.action && pathMatches(it.to, path));
}

function subgroupContainsPath(subgroup: NavSubgroup, path: string): boolean {
  return subgroup.items.some((it) => !it.action && pathMatches(it.to, path));
}


/**
 * First-run nudge: when required CLI setup is still pending, surface a banner
 * that routes to the guided setup wizard. Dismissible for the session so it
 * never blocks; the wizard remains reachable from here anytime.
 */
function FirstRunBanner() {
  const { status, loading } = useSetup();
  const location = useLocation();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  if (loading || !status || dismissed) return null;
  if (location.pathname === "/setup") return null;
  // Only nudge when the CLI is available but required steps are incomplete.
  if (!status.cli_available || status.ready) return null;

  const pending = status.items.filter((i) => i.required && !i.configured).length;
  return (
    <div className="flex items-center gap-3 rounded-lg border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 px-4 py-3 mb-5">
      <Rocket className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />
      <div className="flex-1 text-sm text-blue-800 dark:text-blue-200">
        <span className="font-medium">Welcome to Keel.</span> Finish the guided setup
        {pending > 0 && ` — ${pending} required step${pending === 1 ? "" : "s"} left`}.
      </div>
      <button
        onClick={() => navigate("/setup")}
        className="shrink-0 inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
      >
        <Rocket className="h-3.5 w-3.5" /> Start setup
      </button>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="shrink-0 p-1 rounded text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function Layout() {
  const { user, theme, toggleTheme, updateUser, auth } = useUser();
  const { panelOpen, closePanel } = useSetup();
  const { settings } = useAdminSettings();
  const location = useLocation();
  const overrides = settings.nav_visibility;
  const role = user.role;
  const persona = auth.persona;

  const canGroup = (g: NavGroup) => roleCanSee(role, groupId(g.label), g.minRole, overrides);
  const canSub = (sg: NavSubgroup) => roleCanSee(role, subgroupId(sg.label), sg.minRole, overrides);
  const canItem = (it: NavItem) =>
    roleCanSee(role, itemId(it.to), it.minRole, overrides) &&
    personaCanSee(role, persona, it.personas);

  const visibleGroups = navGroups
    .filter(canGroup)
    .map((g) => ({
      ...g,
      items: g.items.filter(canItem),
      subgroups: (g.subgroups ?? [])
        .filter(canSub)
        .map((sg) => ({ ...sg, items: sg.items.filter(canItem) }))
        .filter((sg) => sg.items.length > 0),
      footerItems: (g.footerItems ?? []).filter(canItem),
    }))
    .filter((g) => g.items.length > 0 || g.subgroups.length > 0 || g.footerItems.length > 0);

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Sidebar */}
      <aside className="w-60 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800 space-y-3">
          <div>
            <h1 className="text-lg font-bold tracking-tight">{settings.branding.app_title}</h1>
            <p className="text-xs text-gray-500 mt-0.5">{settings.branding.app_name}</p>
          </div>
          <WorkspaceLabel />
        </div>

        <nav className="flex-1 px-3 py-4 space-y-3 overflow-y-auto">
          {visibleGroups.map((g) => (
            <NavGroupSection
              key={g.label}
              group={g}
              defaultOpen={groupContainsPath(g, location.pathname)}
              currentPath={location.pathname}
            />
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
                  ? "Local dev identity — set KEEL_AUTH_MODE=forward-auth behind an SSO proxy"
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
          <HelpButton />
        </header>
        <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-6">
          <FirstRunBanner />
          <Outlet />
        </div>
      </main>

      {panelOpen && <SetupPanel onClose={closePanel} />}
    </div>
  );
}
