import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { api } from "@/lib/api";

export interface TerminalTab {
  id: string;
  title: string;
}

interface TerminalContextValue {
  tabs: TerminalTab[];
  activeTab: string | null; // null = welcome screen
  creating: boolean;
  createTab: () => Promise<void>;
  closeTab: (id: string) => Promise<void>;
  setActiveTab: (id: string | null) => void;
}

const TerminalContext = createContext<TerminalContextValue | null>(null);

export function useTerminal() {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminal must be used within TerminalProvider");
  return ctx;
}

export function TerminalProvider({ children }: { children: ReactNode }) {
  const [tabs, setTabs] = useState<TerminalTab[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [initialised, setInitialised] = useState(false);

  // Restore alive sessions once on first mount
  useEffect(() => {
    if (initialised) return;
    api
      .listTerminalSessions()
      .then((sessions) => {
        const alive = sessions.filter((s) => s.alive);
        if (alive.length > 0) {
          setTabs(alive.map((s) => ({ id: s.id, title: s.title })));
          // Don't auto-select — let user see welcome first
        }
      })
      .catch(() => {})
      .finally(() => setInitialised(true));
  }, [initialised]);

  const createTab = useCallback(async () => {
    if (creating || tabs.length >= 4) return;
    setCreating(true);
    try {
      const session = await api.createTerminalSession({
        title: `Terminal ${tabs.length + 1}`,
      });
      const tab: TerminalTab = { id: session.id, title: session.title };
      setTabs((prev) => [...prev, tab]);
      setActiveTab(session.id);
    } catch (err) {
      console.error("Failed to create terminal:", err);
    } finally {
      setCreating(false);
    }
  }, [creating, tabs.length]);

  const closeTab = useCallback(
    async (id: string) => {
      try {
        await api.killTerminalSession(id);
      } catch {
        // ignore
      }
      setTabs((prev) => {
        const remaining = prev.filter((t) => t.id !== id);
        // If we closed the active tab, go to welcome
        if (activeTab === id) {
          setActiveTab(remaining.length > 0 ? remaining[remaining.length - 1].id : null);
        }
        return remaining;
      });
    },
    [activeTab]
  );

  return (
    <TerminalContext.Provider
      value={{ tabs, activeTab, creating, createTab, closeTab, setActiveTab }}
    >
      {children}
    </TerminalContext.Provider>
  );
}
