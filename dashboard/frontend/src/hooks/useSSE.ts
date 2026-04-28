import { useEffect, useState, useRef } from "react";

export function useSSE(url: string | null, maxLines: number = 500) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!url) return;

    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener("log", (e) => {
      setLines((prev) => {
        const next = [...prev, e.data];
        return next.length > maxLines ? next.slice(-maxLines) : next;
      });
    });

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [url, maxLines]);

  const clear = () => setLines([]);

  return { lines, connected, clear };
}
