import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { api, type AdminSettings, type AdminSettingsUpdate } from "@/lib/api";

/**
 * App-level, admin-controlled settings: branding (title/name shown top-left) and
 * per-role navigation visibility. Hydrated once from the backend so every user
 * renders the org's configured app; admins mutate it via `updateSettings`.
 */

const DEFAULTS: AdminSettings = {
  branding: { app_title: "Keel", app_name: "Agentic Product Development Platform" },
  nav_visibility: {},
  skill_enforcement: "off",
  build_governance_default: "warn",
  code_assist: { enabled: ["devin", "local"], default: "devin" },
};

interface AdminSettingsValue {
  settings: AdminSettings;
  loading: boolean;
  refresh: () => void;
  updateSettings: (patch: AdminSettingsUpdate) => Promise<void>;
}

const Ctx = createContext<AdminSettingsValue | null>(null);

export function useAdminSettings() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAdminSettings must be used within AdminSettingsProvider");
  return ctx;
}

export function AdminSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AdminSettings>(DEFAULTS);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    setLoading(true);
    api
      .getAdminSettings()
      .then((s) => setSettings({ ...DEFAULTS, ...s, branding: { ...DEFAULTS.branding, ...s.branding } }))
      .catch(() => setSettings(DEFAULTS))
      .finally(() => setLoading(false));
  }, []);

  // Hydrate once. setState runs only inside the async callbacks (not the effect
  // body) so it does not trigger cascading-render warnings.
  useEffect(() => {
    let alive = true;
    api
      .getAdminSettings()
      .then((s) => alive && setSettings({ ...DEFAULTS, ...s, branding: { ...DEFAULTS.branding, ...s.branding } }))
      .catch(() => alive && setSettings(DEFAULTS))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const updateSettings = useCallback(async (patch: AdminSettingsUpdate) => {
    const next = await api.updateAdminSettings(patch);
    setSettings({ ...DEFAULTS, ...next, branding: { ...DEFAULTS.branding, ...next.branding } });
  }, []);

  const value = useMemo(
    () => ({ settings, loading, refresh, updateSettings }),
    [settings, loading, refresh, updateSettings]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
