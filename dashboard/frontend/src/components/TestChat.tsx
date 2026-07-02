import { useState } from "react";
import { MessageSquare, Send, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface TestMsg {
  role: "user" | "agent";
  content: string;
  error?: boolean;
}

interface TestChatProps {
  path: string;
  compact?: boolean;
}

export function TestChat({ path, compact = false }: TestChatProps) {
  const [messages, setMessages] = useState<TestMsg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setSending(true);
    try {
      const res = await api.testAgent(path, text);
      if (res.ok) {
        setMessages((prev) => [...prev, { role: "agent", content: res.response || "(empty response)" }]);
      } else {
        setMessages((prev) => [...prev, { role: "agent", content: res.error || "Unknown error", error: true }]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: err instanceof Error ? err.message : String(err), error: true },
      ]);
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const containerClass = compact
    ? ""
    : "rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5";

  return (
    <div className={containerClass}>
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <h3 className="text-sm font-semibold">Test agent</h3>
        <span className="text-xs text-gray-400">runs the agent's answer() once per message</span>
      </div>

      <div className="space-y-3 max-h-72 overflow-y-auto mb-3">
        {messages.length === 0 && (
          <p className="text-xs text-gray-400 py-4 text-center">
            Send a message to invoke the generated agent and validate its response.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-blue-600 text-white"
                  : m.error
                    ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300 font-mono text-xs"
                    : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800 text-gray-500">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Running agent…
            </div>
          </div>
        )}
      </div>

      <div className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type a message to test the agent… (Enter to send)"
          rows={1}
          disabled={sending}
          className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 placeholder-gray-400"
        />
        <button
          onClick={send}
          disabled={!input.trim() || sending}
          className="shrink-0 h-10 w-10 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 flex items-center justify-center transition-colors"
        >
          {sending ? <Loader2 className="h-4 w-4 text-white animate-spin" /> : <Send className="h-4 w-4 text-white" />}
        </button>
      </div>
    </div>
  );
}
