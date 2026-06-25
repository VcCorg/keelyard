import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2 } from "lucide-react";
import { api, type ChatStreamEvent } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";
import { ThinkingPanel, type ToolCallEntry } from "./ThinkingPanel";

interface Message {
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

interface ChatWindowProps {
  sessionId: string;
}

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [toolCalls, setToolCalls] = useState<ToolCallEntry[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [wsConnected, setWsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  // Connect WebSocket
  useEffect(() => {
    const url = api.chatWebSocketUrl(sessionId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (event) => {
      try {
        const evt: ChatStreamEvent = JSON.parse(event.data);
        handleStreamEvent(evt);
      } catch {
        console.error("Failed to parse WebSocket message:", event.data);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  const handleStreamEvent = useCallback((evt: ChatStreamEvent) => {
    switch (evt.type) {
      case "thinking_start":
        setIsThinking(true);
        setToolCalls([]);
        break;

      case "tool_call":
        setToolCalls((prev) => [
          ...prev,
          {
            tool: evt.data.tool as string,
            args: (evt.data.args as Record<string, unknown>) ?? {},
          },
        ]);
        break;

      case "tool_result":
        setToolCalls((prev) => {
          const updated = [...prev];
          const toolName = evt.data.tool as string;
          // Find the last tool call with this name that has no result
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].tool === toolName && !updated[i].result) {
              updated[i] = { ...updated[i], result: evt.data.result as string };
              break;
            }
          }
          return updated;
        });
        break;

      case "thinking_end":
        setIsThinking(false);
        break;

      case "agent_response":
        setStreamingContent((prev) => prev + (evt.data.content as string));
        break;

      case "agent_response_end":
        setStreamingContent((prev) => {
          if (prev) {
            setMessages((msgs) => [
              ...msgs,
              { role: "agent", content: prev, timestamp: new Date().toISOString() },
            ]);
          }
          return "";
        });
        setSending(false);
        break;

      case "error":
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            content: `Error: ${evt.data.message}`,
            timestamp: new Date().toISOString(),
          },
        ]);
        setSending(false);
        setIsThinking(false);
        break;
    }
  }, []);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed, timestamp: new Date().toISOString() },
    ]);
    setInput("");
    setSending(true);
    setStreamingContent("");

    // Send via WebSocket
    wsRef.current.send(JSON.stringify({ type: "user_message", content: trimmed }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full">
      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && !streamingContent && (
            <div className="flex items-center justify-center h-full text-sm text-gray-400">
              Start a conversation with the agent
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              timestamp={msg.timestamp}
            />
          ))}

          {/* Streaming response */}
          {streamingContent && (
            <MessageBubble
              role="agent"
              content={streamingContent}
              isStreaming
            />
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-gray-800 px-4 py-3">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={wsConnected ? "Type a message... (Enter to send)" : "Connecting..."}
              disabled={!wsConnected || sending}
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-600 disabled:opacity-50 placeholder-gray-400"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || !wsConnected || sending}
              className="shrink-0 h-10 w-10 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 flex items-center justify-center transition-colors"
            >
              {sending ? (
                <Loader2 className="h-4 w-4 text-white animate-spin" />
              ) : (
                <Send className="h-4 w-4 text-white" />
              )}
            </button>
          </div>
          <div className="flex items-center justify-between mt-1.5 px-1">
            <span className="text-[10px] text-gray-400">Shift+Enter for new line</span>
            <span className={`text-[10px] ${wsConnected ? "text-emerald-500" : "text-red-400"}`}>
              {wsConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </div>

      {/* Thinking panel */}
      <ThinkingPanel isThinking={isThinking} toolCalls={toolCalls} />
    </div>
  );
}
