import { useSSE } from "@/hooks/useSSE";
import { useEffect, useRef } from "react";

interface LogViewerProps {
  url: string;
  className?: string;
}

export function LogViewer({ url, className }: LogViewerProps) {
  const { lines, connected } = useSSE(url);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className={`bg-gray-950 rounded-lg border border-gray-800 ${className ?? ""}`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <span className="text-xs text-gray-400 font-mono">Logs</span>
        <span className={`text-xs ${connected ? "text-emerald-400" : "text-red-400"}`}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
      <div className="p-3 max-h-96 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
        {lines.length === 0 && (
          <span className="text-gray-600 italic">Waiting for logs...</span>
        )}
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all leading-relaxed">
            {line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
