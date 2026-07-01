import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { api, type SetupStatus, type SetupItem } from "@/lib/api";

interface SetupContextValue {
  status: SetupStatus | null;
  loading: boolean;
  /** Re-fetch the CLI setup status (call after running an init step). */
  refresh: () => Promise<void>;
  /** Convenience lookup for a single config item. */
  item: (key: string) => SetupItem | undefined;
  /** True when the named item is configured (false while loading / missing). */
  isConfigured: (key: string) => boolean;
  /** Whether the global setup modal is open (rendered by Layout). */
  panelOpen: boolean;
  openPanel: () => void;
  closePanel: () => void;
}

const SetupContext = createContext<SetupContextValue | null>(null);

export function useSetup() {
  const ctx = useContext(SetupContext);
  if (!ctx) throw new Error("useSetup must be used within SetupProvider");
  return ctx;
}

export function SetupProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [panelOpen, setPanelOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await api.getSetupStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const item = useCallback(
    (key: string) => status?.items.find((i) => i.key === key),
    [status]
  );
  const isConfigured = useCallback(
    (key: string) => !!status?.items.find((i) => i.key === key)?.configured,
    [status]
  );

  return (
    <SetupContext.Provider
      value={{
        status,
        loading,
        refresh,
        item,
        isConfigured,
        panelOpen,
        openPanel: () => setPanelOpen(true),
        closePanel: () => setPanelOpen(false),
      }}
    >
      {children}
    </SetupContext.Provider>
  );
}
