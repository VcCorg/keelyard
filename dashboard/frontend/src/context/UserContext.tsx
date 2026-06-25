import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";

/**
 * Phase A local identity seam.
 *
 * Everything user-aware reads from `useUser()` so that graduating to real
 * SSO/OIDC (Phase C) is a single provider swap — no call-site changes.
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

const STORAGE_KEY = "dva.currentUser";
const WORKSPACE_KEY = "dva.workspace";
const THEME_KEY = "dva.theme";

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

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

interface UserContextValue {
  user: CurrentUser;
  workspace: Workspace;
  setWorkspace: (w: Workspace) => void;
  updateUser: (patch: Partial<CurrentUser>) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
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
    () => ({ user, workspace, setWorkspace, updateUser, theme, setTheme, toggleTheme }),
    [user, workspace, setWorkspace, updateUser, theme, setTheme, toggleTheme]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}
