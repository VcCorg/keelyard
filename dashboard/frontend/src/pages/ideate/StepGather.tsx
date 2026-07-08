import { useRef } from "react";
import { FileUp, Search, Loader2, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentWindow } from "./AgentWindow";
import type { AgentEvent, IdeateAgent } from "./types";

export function StepGather({
  context,
  onContext,
  searchSource,
  onSearchSource,
  searchQuery,
  onSearchQuery,
  onSearch,
  searching,
  onUpload,
  uploading,
  agentEvents,
  agentRunning,
  onRunAgent,
  agents,
  selectedAgentPaths,
  onToggleAgent,
}: {
  context: string;
  onContext: (v: string) => void;
  searchSource: "glean" | "confluence";
  onSearchSource: (s: "glean" | "confluence") => void;
  searchQuery: string;
  onSearchQuery: (q: string) => void;
  onSearch: () => void;
  searching: boolean;
  onUpload: (file: File) => void;
  uploading: boolean;
  agentEvents: AgentEvent[];
  agentRunning: boolean;
  onRunAgent: () => void;
  agents: IdeateAgent[];
  selectedAgentPaths: string[];
  onToggleAgent: (path: string) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={searchSource}
          onChange={(e) => onSearchSource(e.target.value as "glean" | "confluence")}
          className="text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
        >
          <option value="glean">Glean</option>
          <option value="confluence">Confluence</option>
        </select>
        <input
          value={searchQuery}
          onChange={(e) => onSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
          placeholder="Search enterprise knowledge…"
          className="flex-1 min-w-[200px] text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-1.5 outline-none"
        />
        <button
          onClick={onSearch}
          disabled={searching || !searchQuery.trim()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-300"
        >
          {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />} Search
        </button>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 dark:bg-gray-800 dark:text-gray-300"
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />} Upload
        </button>
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = "";
          }}
        />
      </div>
      <textarea
        value={context}
        onChange={(e) => onContext(e.target.value)}
        rows={10}
        placeholder="Paste or gather requirements here…"
        className="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 px-3 py-2 outline-none"
      />
      {agents.length > 0 && (
        <div className="space-y-1">
          <div className="text-[11px] font-semibold text-gray-500 flex items-center gap-1">
            <Bot className="h-3.5 w-3.5 text-violet-500" /> Inject agents as tools
          </div>
          <div className="flex flex-wrap gap-1.5">
            {agents.map((a) => {
              const on = selectedAgentPaths.includes(a.path);
              return (
                <button
                  key={a.path}
                  onClick={() => onToggleAgent(a.path)}
                  className={cn(
                    "text-[11px] rounded-full px-2.5 py-1 border transition-colors",
                    on
                      ? "bg-violet-50 text-violet-700 border-violet-300 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-700"
                      : "bg-transparent text-gray-500 border-gray-200 dark:border-gray-800 hover:border-gray-300"
                  )}
                  title={a.path}
                >
                  {a.name}
                </button>
              );
            })}
          </div>
        </div>
      )}
      <AgentWindow
        events={agentEvents}
        running={agentRunning}
        onRun={onRunAgent}
        disabled={!context.trim()}
      />
    </div>
  );
}
