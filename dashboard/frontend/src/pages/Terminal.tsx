import { TerminalSquare, Plus, X, Home } from "lucide-react";
import { useTerminal } from "@/context/TerminalContext";
import { TerminalView } from "@/components/terminal/TerminalView";

export function Terminal() {
  const { tabs, activeTab, creating, createTab, closeTab, setActiveTab } =
    useTerminal();

  const isWelcome = activeTab === null;

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] -mx-6 -my-6">
      {/* Tab bar */}
      <div className="flex items-center bg-slate-900 border-b border-slate-700 px-2">
        {/* Welcome tab — always present, never closeable */}
        <div
          onClick={() => setActiveTab(null)}
          className={`flex items-center gap-2 px-3 py-2 text-xs font-medium cursor-pointer border-r border-slate-700 transition-colors ${
            isWelcome
              ? "bg-slate-800 text-white"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
          }`}
        >
          <Home className="h-3.5 w-3.5" />
          <span>Welcome</span>
        </div>

        {/* Session tabs */}
        {tabs.map((tab) => (
          <div
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`group flex items-center gap-2 px-3 py-2 text-xs font-medium cursor-pointer border-r border-slate-700 transition-colors ${
              activeTab === tab.id
                ? "bg-slate-800 text-white"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <TerminalSquare className="h-3.5 w-3.5" />
            <span>{tab.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeTab(tab.id);
              }}
              className="ml-1 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-slate-600 transition-all"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}

        <button
          onClick={createTab}
          disabled={creating || tabs.length >= 4}
          className="flex items-center gap-1 px-3 py-2 text-xs text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors disabled:opacity-30"
          title={tabs.length >= 4 ? "Max 4 terminals" : "New terminal"}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>

        <div className="flex-1" />
        <div className="text-[10px] text-slate-500 px-3 py-2 font-mono">
          dva-agentic-project
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 bg-[#0f172a] min-h-0">
        {isWelcome ? (
          /* Welcome / New Terminal screen — always available */
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <TerminalSquare className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm font-medium">Inline Terminal</p>
              <p className="text-xs text-slate-600 mt-1 max-w-xs">
                Run <code className="text-blue-400">dva</code> commands
                directly from the dashboard.
              </p>
              {tabs.length > 0 && (
                <p className="text-xs text-slate-600 mt-2">
                  {tabs.length} active session{tabs.length > 1 ? "s" : ""} — click a tab above to resume.
                </p>
              )}
              <button
                onClick={createTab}
                disabled={creating || tabs.length >= 4}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                {creating ? "Opening..." : "New Terminal"}
              </button>
              {tabs.length >= 4 && (
                <p className="text-[10px] text-slate-600 mt-2">
                  Maximum 4 terminals reached
                </p>
              )}
            </div>
          </div>
        ) : (
          <TerminalView
            key={activeTab}
            sessionId={activeTab!}
            onExit={() => closeTab(activeTab!)}
          />
        )}
      </div>
    </div>
  );
}
