import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
  role: "user" | "agent";
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
}

export function MessageBubble({ role, content, timestamp, isStreaming }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-blue-100 dark:bg-blue-900/40"
            : "bg-emerald-100 dark:bg-emerald-900/40"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        ) : (
          <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        )}
      </div>

      <div className={`max-w-[70%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 rounded-tl-sm"
          }`}
        >
          {content}
          {isStreaming && (
            <span className="inline-block ml-1 w-1.5 h-4 bg-current animate-pulse rounded" />
          )}
        </div>
        {timestamp && (
          <div className="text-[10px] text-gray-400 mt-1 px-1">
            {new Date(timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
}
