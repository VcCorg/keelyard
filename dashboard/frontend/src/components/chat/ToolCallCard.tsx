import { useState } from "react";
import { Wrench, ChevronDown, ChevronRight, CheckCircle2 } from "lucide-react";
interface ToolCallCardProps {
  tool: string;
  args: Record<string, unknown>;
  result?: string;
}

export function ToolCallCard({ tool, args, result }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
      >
        {result ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
        ) : (
          <Wrench className="h-3.5 w-3.5 text-blue-500 animate-spin shrink-0" />
        )}
        <span className="font-mono font-semibold text-blue-600 dark:text-blue-400 truncate">
          {tool}
        </span>
        {expanded ? (
          <ChevronDown className="h-3 w-3 ml-auto text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 ml-auto text-gray-400 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-2 space-y-2">
          {Object.keys(args).length > 0 && (
            <div>
              <span className="text-gray-500 font-medium">Args:</span>
              <pre className="mt-1 p-2 rounded bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-400 overflow-x-auto whitespace-pre-wrap break-all">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          {result && (
            <div>
              <span className="text-gray-500 font-medium">Result:</span>
              <pre className="mt-1 p-2 rounded bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-400 overflow-x-auto whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                {result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
