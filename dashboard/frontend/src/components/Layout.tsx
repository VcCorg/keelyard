import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  Server,
  Activity,
  MessageSquare,
  FolderKanban,
  TerminalSquare,
  Package,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/agents", icon: Bot, label: "Agents" },
  { to: "/projects", icon: FolderKanban, label: "Agent Projects" },
  { to: "/skills", icon: Package, label: "Skills" },
  { to: "/mcp", icon: Server, label: "MCP Servers" },
  { to: "/activity", icon: Activity, label: "Activity" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/terminal", icon: TerminalSquare, label: "Terminal" },
];

export function Layout() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Sidebar */}
      <aside className="w-60 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <h1 className="text-lg font-bold tracking-tight">
            Agent Playground
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">Agentic Platform</p>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
                    : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-5 py-3 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-400">
          v0.1.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
