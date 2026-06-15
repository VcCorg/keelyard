import { useEffect, useRef, useState } from "react";
import { Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

/** Streams an SSE endpoint that emits `log` and `done` events. */
export function StreamConsole({
  url,
  title = "CLI output",
  onDone,
}: {
  url: string | null;
  title?: string;
  onDone?: (code: string) => void;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!url) return;
    setLines([]);
    setRunning(true);
    const es = new EventSource(url);
    es.addEventListener("log", (e: MessageEvent) => setLines((p) => [...p, e.data]));
    es.addEventListener("done", (e: MessageEvent) => {
      setRunning(false);
      es.close();
      onDone?.(e.data);
    });
    es.onerror = () => {
      setRunning(false);
      es.close();
    };
    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  if (!url) return null;

  return (
    <div className="bg-gray-950 rounded-lg border border-gray-800 mt-3">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <span className="text-xs text-gray-400 font-mono">{title}</span>
        <span
          className={cn(
            "text-xs flex items-center gap-1",
            running ? "text-amber-400" : "text-emerald-400"
          )}
        >
          {running ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" /> running
            </>
          ) : (
            <>
              <Check className="h-3 w-3" /> done
            </>
          )}
        </span>
      </div>
      <div className="p-3 max-h-96 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
        {lines.map((l, i) => (
          <div key={i} className="whitespace-pre-wrap break-all leading-relaxed">
            {l}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
