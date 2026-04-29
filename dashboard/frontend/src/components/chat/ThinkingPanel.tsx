import { Brain, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { ToolCallCard } from "./ToolCallCard";

export interface ToolCallEntry {
  tool: string;
  args: Record<string, unknown>;
  result?: string;
}

interface ThinkingPanelProps {
  isThinking: boolean;
  toolCalls: ToolCallEntry[];
}

export function ThinkingPanel({ isThinking, toolCalls }: ThinkingPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (toolCalls.length === 0 && !isThinking) return null;

  return (
    <div className="border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 w-80 flex flex-col shrink-0">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-800 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <Brain className="h-4 w-4 text-indigo-500" />
        Thinking
        {isThinking && (
          <span className="ml-1 h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
        )}
        <span className="ml-auto text-xs text-gray-400">{toolCalls.length} calls</span>
        {collapsed ? (
          <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
        )}
      </button>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {toolCalls.map((tc, i) => (
            <ToolCallCard
              key={`${tc.tool}-${i}`}
              tool={tc.tool}
              args={tc.args}
              result={tc.result}
            />
          ))}
          {isThinking && toolCalls.length === 0 && (
            <div className="text-xs text-gray-400 italic py-4 text-center">
              Agent is thinking...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
