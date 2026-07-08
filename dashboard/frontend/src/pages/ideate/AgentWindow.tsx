import { useEffect, useRef, useState } from "react";
import {
  Bot,
  ChevronDown,
  ChevronUp,
  Loader2,
  Wrench,
  CheckCircle2,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentEvent } from "./types";

const ICONS: Record<AgentEvent["type"], typeof Bot> = {
  thinking: Sparkles,
  tool_call: Wrench,
  tool_result: CheckCircle2,
  stories: Sparkles,
  final: CheckCircle2,
  error: AlertCircle,
};

function summarize(ev: AgentEvent): string {
  switch (ev.type) {
    case "tool_call":
      return `Calling ${ev.tool}(${JSON.stringify(ev.args ?? {})})`;
    case "tool_result": {
      const r = ev.result as { error?: string } | undefined;
      if (r?.error) return `${ev.tool} → error: ${r.error}`;
      return `${ev.tool} → ${JSON.stringify(ev.result)}`.slice(0, 240);
    }
    case "stories":
      return `Drafted ${ev.stories?.length ?? 0} stories`;
    case "final":
      return ev.text || "Done";
    case "error":
      return ev.error || "Agent error";
    default:
      return ev.text || "";
  }
}

/**
 * Collapsible window that streams the agent's reasoning/tool trace.
 * `running` shows the spinner; `events` is the accumulated trace.
 */
export function AgentWindow({
  events,
  running,
  onRun,
  disabled,
}: {
  events: AgentEvent[];
  running: boolean;
  onRun: () => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events, open]);

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950">
      <div className="flex items-center justify-between px-3 py-2">
        <button
          onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-200"
        >
          <Bot className="h-4 w-4 text-violet-500" />
          Agent
          {running && <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500" />}
          {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        <button
          onClick={onRun}
          disabled={disabled || running}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-violet-50 text-violet-700 hover:bg-violet-100 disabled:opacity-50 dark:bg-violet-900/30 dark:text-violet-300"
        >
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          Run agent
        </button>
      </div>

      {open && (
        <div className="max-h-64 overflow-y-auto px-3 pb-3 space-y-1.5">
          {events.length === 0 && !running && (
            <p className="text-xs text-gray-400">
              The agent will search your sources and draft stories. Its steps appear here.
            </p>
          )}
          {events.map((ev, i) => {
            const Icon = ICONS[ev.type] ?? Bot;
            return (
              <div
                key={i}
                className={cn(
                  "flex items-start gap-2 text-xs rounded-md px-2 py-1.5",
                  ev.type === "error"
                    ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                    : ev.type === "tool_call"
                      ? "bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300"
                      : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300"
                )}
              >
                <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                <span className="break-words font-mono">{summarize(ev)}</span>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
