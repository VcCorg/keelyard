import { useRef } from "react";
import { FileUp, Search, Loader2, Bot, ExternalLink, Plus, Check, X } from "lucide-react";
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
  attached,
  onToggleAttach,
  onAttachAll,
  onRemoveAttached,
  onClearAttached,
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
  attached: SearchResult[];
  onToggleAttach: (r: SearchResult) => void;
  onAttachAll: () => void;
  onRemoveAttached: (r: SearchResult) => void;
  onClearAttached: () => void;
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
  const keyOf = (r: SearchResult) => r.url || r.title;
  const isAttached = (r: SearchResult) => attached.some((a) => keyOf(a) === keyOf(r));
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
                  {isAttached(r) ? (
                    <button
                      onClick={() => onToggleAttach(r)}
                      className="inline-flex items-center gap-1 shrink-0 text-[11px] font-medium text-emerald-700 border border-emerald-300 bg-emerald-50 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700 rounded-lg px-2 py-1"
                      title="Remove from context"
                    >
                      <Check className="h-3 w-3" /> Attached
                    </button>
                  ) : (
                    <button
                      onClick={() => onToggleAttach(r)}
                      className="inline-flex items-center gap-1 shrink-0 text-[11px] font-medium text-blue-600 hover:text-blue-700 border border-blue-200 dark:border-blue-800 rounded-lg px-2 py-1"
                      title="Attach to context"
                    >
                      <Plus className="h-3 w-3" /> Attach
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {attached.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-semibold text-gray-500">
              Attached context ({attached.length})
            </div>
            <button
              onClick={onClearAttached}
              className="text-[11px] font-medium text-gray-500 hover:text-red-600"
            >
              Clear all
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {attached.map((r) => (
              <span
                key={keyOf(r)}
                className="inline-flex items-center gap-1 max-w-[260px] text-[11px] rounded-full border border-emerald-300 bg-emerald-50 text-emerald-700 px-2 py-1 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700"
              >
                {r.url ? (
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener"
                    className="truncate hover:underline"
                    title={r.title || r.url}
                  >
                    {r.title || r.url}
                  </a>
                ) : (
                  <span className="truncate" title={r.title}>
                    {r.title || "Untitled"}
                  </span>
                )}
                <button
                  onClick={() => onRemoveAttached(r)}
                  className="shrink-0 hover:text-red-600"
                  title="Remove from context"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
      <textarea
        value={context}
        onChange={(e) => onContext(e.target.value)}
        rows={8}
        placeholder="Add any extra requirements or instructions… (attached results are included automatically)"
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
        disabled={!context.trim() && attached.length === 0}
      />
    </div>
  );
}
