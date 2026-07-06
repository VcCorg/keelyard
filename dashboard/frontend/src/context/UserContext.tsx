import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { api, type AuthMe } from "@/lib/api";

/**
 * Identity seam.
 *
 * Everything user-aware reads from `useUser()`. Identity is hydrated from the
 * backend `/auth/me`, which the configured provider resolves — a dev principal
 * locally, or the SSO proxy's verified identity in production. Permissions come
 * from the same source; `can(permission)` gates UI (the server still enforces).
 */

export type UserRole = "member" | "lead" | "admin";

export interface CurrentUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

/** Which lens the sidebar / pages present. */
export type Workspace = "mine" | "team";

/** Visual theme. */
export type Theme = "light" | "dark";

const STORAGE_KEY = "keel.currentUser";
const WORKSPACE_KEY = "keel.workspace";
const THEME_KEY = "keel.theme";

const DEFAULT_USER: CurrentUser = {
  id: "local",
  name: "Local User",
  email: "local@localhost",
  role: "admin", // local-only mode: full access until a shared directory exists
};

function loadUser(): CurrentUser {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_USER, ...JSON.parse(raw) };
  } catch {
    // ignore corrupt profile
  }
  return DEFAULT_USER;
}

function loadWorkspace(): Workspace {
  const raw = localStorage.getItem(WORKSPACE_KEY);
  return raw === "team" ? "team" : "mine";
}

function loadTheme(): Theme {
  const raw = localStorage.getItem(THEME_KEY);
  if (raw === "light" || raw === "dark") return raw;
  // First visit defaults to the clean light theme; dark is one toggle away.
  return "light";
}

/**
 * The single top-of-sidebar workspace label. There is one workspace per user;
 * only its name changes with role: admins see the team-wide lens.
 */
export function workspaceLabel(role: UserRole): string {
  if (role === "admin") return "My Team workspace";
  if (role === "lead") return "Lead workspace";
  return "My Workspace";
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

/** Map an auth-provider role to the sidebar's coarse nav role. */
function navRoleFor(roles: string[]): UserRole {
  if (roles.includes("admin")) return "admin";
  if (roles.includes("maintainer")) return "lead";
  return "member";
}

interface AuthInfo {
  provider: string;   // dev | forward-auth | none
  mode: string;       // KEEL_AUTH_MODE
  authenticated: boolean;
  roles: string[];
  permissions: string[];
}

const DEFAULT_AUTH: AuthInfo = {
  provider: "dev",
  mode: "dev",
  authenticated: true,
  roles: ["admin"],
  permissions: ["admin:*"], // optimistic local-admin default (matches dev provider)
};

interface UserContextValue {
  user: CurrentUser;
  workspace: Workspace;
  setWorkspace: (w: Workspace) => void;
  updateUser: (patch: Partial<CurrentUser>) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  auth: AuthInfo;
  /** UI gate — server still enforces. Admins (admin:* or dev default) pass all. */
  can: (permission: string) => boolean;
}

const UserContext = createContext<UserContextValue | null>(null);

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser>(loadUser);
  const [workspace, setWorkspaceState] = useState<Workspace>(loadWorkspace);
  const [theme, setThemeState] = useState<Theme>(loadTheme);
  const [auth, setAuth] = useState<AuthInfo>(DEFAULT_AUTH);

  // Hydrate identity from the backend provider (dev locally, SSO proxy in prod).
  useEffect(() => {
    let alive = true;
    api
      .getMe()
      .then((me: AuthMe) => {
        if (!alive) return;
        setAuth({
          provider: me.provider,
          mode: me.mode,
          authenticated: me.authenticated,
          roles: me.roles,
          permissions: me.permissions,
        });
        setUser((prev) => ({
          ...prev,
          name: me.display_name || me.subject || prev.name,
          email: me.subject || prev.email,
          role: navRoleFor(me.roles),
        }));
      })
      .catch(() => {
        // No auth endpoint (older backend) → keep the local default (admin).
      });
    return () => {
      alive = false;
    };
  }, []);

  const can = useCallback(
    (permission: string) =>
      auth.permissions.includes("admin:*") || auth.permissions.includes(permission),
    [auth.permissions]
  );

  // Apply the theme class to <html> and persist the choice.
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const setTheme = useCallback((t: Theme) => setThemeState(t), []);
  const toggleTheme = useCallback(
    () => setThemeState((t) => (t === "dark" ? "light" : "dark")),
    []
  );

  const setWorkspace = useCallback((w: Workspace) => {
    setWorkspaceState(w);
    try {
      localStorage.setItem(WORKSPACE_KEY, w);
    } catch {
      // ignore
    }
  }, []);

  const updateUser = useCallback((patch: Partial<CurrentUser>) => {
    setUser((prev) => {
      const next = { ...prev, ...patch };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ user, workspace, setWorkspace, updateUser, theme, setTheme, toggleTheme, auth, can }),
    [user, workspace, setWorkspace, updateUser, theme, setTheme, toggleTheme, auth, can]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}
