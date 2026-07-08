import { useRef } from "react";
import { FileUp, Search, Loader2, Bot, ExternalLink, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentWindow } from "./AgentWindow";
import type { AgentEvent, IdeateAgent, SearchResult } from "./types";

export function StepGather({
  context,
  onContext,
  searchSource,
  onSearchSource,
  searchQuery,
  onSearchQuery,
  onSearch,
  searching,
  searchResults,
  onAttachResult,
  onAttachAll,
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
  searchResults: SearchResult[];
  onAttachResult: (r: SearchResult) => void;
  onAttachAll: () => void;
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
      {searchResults.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-semibold text-gray-500">
              {searchResults.length} result{searchResults.length === 1 ? "" : "s"}
            </div>
            <button
              onClick={onAttachAll}
              className="text-[11px] font-medium text-blue-600 hover:text-blue-700"
            >
              Attach all
            </button>
          </div>
          <div className="space-y-1.5 max-h-72 overflow-y-auto">
            {searchResults.map((r, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    {r.url ? (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener"
                        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline break-words"
                      >
                        {r.title || r.url}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                        {r.title || "Untitled"}
                      </span>
                    )}
                    {r.snippet && (
                      <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">{r.snippet}</p>
                    )}
                  </div>
                  <button
                    onClick={() => onAttachResult(r)}
                    className="inline-flex items-center gap-1 shrink-0 text-[11px] font-medium text-blue-600 hover:text-blue-700 border border-blue-200 dark:border-blue-800 rounded-lg px-2 py-1"
                    title="Attach to context"
                  >
                    <Plus className="h-3 w-3" /> Attach
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
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
