import type { AgentEvent } from "./types";

export interface RunAgentOptions {
  task?: string;
  context: string;
  project_key: string;
  model?: string | null;
  signal?: AbortSignal;
  onEvent: (ev: AgentEvent) => void;
}

/**
 * Run the Ideate ReAct agent and stream its trace via SSE-over-fetch.
 *
 * The backend endpoint is POST (task + context can be large), so the browser's
 * EventSource (GET-only) can't be used. We read the response body as a stream
 * and parse `event:`/`data:` SSE frames ourselves, invoking `onEvent` per frame.
 */
export async function runAgent({
  task,
  context,
  project_key,
  model,
  signal,
  onEvent,
}: RunAgentOptions): Promise<void> {
  const res = await fetch("/api/ideate/agent/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, context, project_key, model }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Agent run failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushFrame = (frame: string) => {
    const dataLines: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    }
    if (!dataLines.length) return;
    try {
      onEvent(JSON.parse(dataLines.join("\n")) as AgentEvent);
    } catch {
      /* skip unparseable frames (e.g. comments/keep-alives) */
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      flushFrame(frame);
    }
  }
  if (buffer.trim()) flushFrame(buffer);
}
