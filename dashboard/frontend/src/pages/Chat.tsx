import { useState, useEffect, useCallback } from "react";
import { MessageSquare, Plus, Trash2, ExternalLink, ChevronDown } from "lucide-react";
import { api, type ChatSessionInfo, type AgentInfo } from "@/lib/api";
import { ChatWindow } from "@/components/chat/ChatWindow";

export function Chat() {
  const [sessions, setSessions] = useState<ChatSessionInfo[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("dva-assistant");

  const loadSessions = useCallback(async () => {
    try {
      const list = await api.listChatSessions();
      setSessions(list);
    } catch {
      // Backend may not be running
    }
  }, []);

  useEffect(() => {
    loadSessions();
    api.listAgents().then((list) => {
      const interactive = list.filter(
        (a) => a.agent_type === "interactive" && a.status === "running"
      );
      setAgents(interactive);
    }).catch(() => {});
  }, [loadSessions]);

  const handleNewSession = async () => {
    setCreating(true);
    try {
      const session = await api.createChatSession(selectedAgent);
      setSessions((prev) => [session, ...prev]);
      setActiveSession(session.id);
    } catch (err) {
      console.error("Failed to create session:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await api.deleteChatSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSession === id) setActiveSession(null);
    } catch {
      // ignore
    }
  };

  const handleOpenInNewWindow = () => {
    if (activeSession) {
      window.open(`/chat?session=${activeSession}`, "_blank", "width=900,height=700");
    }
  };

  return (
    <div className="flex h-[calc(100vh-5rem)] -mx-6 -my-6">
      {/* Session sidebar */}
      <div className="w-56 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col shrink-0">
        <div className="px-3 py-3 border-b border-gray-200 dark:border-gray-800 space-y-2">
          {/* Agent selector */}
          <div className="relative">
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="w-full appearance-none bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-xs font-medium pr-7 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="dva-assistant">dva-assistant (default)</option>
              {agents.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.name} (running)
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400 pointer-events-none" />
          </div>
          <button
            onClick={handleNewSession}
            disabled={creating}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            {creating ? "Creating..." : "New Chat"}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 && (
            <div className="px-3 py-6 text-center text-xs text-gray-400">
              No chat sessions yet
            </div>
          )}
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer border-b border-gray-100 dark:border-gray-800 transition-colors ${
                activeSession === session.id
                  ? "bg-blue-50 dark:bg-blue-900/20"
                  : "hover:bg-gray-50 dark:hover:bg-gray-800/50"
              }`}
              onClick={() => setActiveSession(session.id)}
            >
              <MessageSquare className="h-3.5 w-3.5 text-gray-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">{session.agent_name}</div>
                <div className="text-[10px] text-gray-400">{session.id}</div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
              >
                <Trash2 className="h-3 w-3 text-red-500" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeSession ? (
          <>
            {/* Chat header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
              <div className="text-sm font-medium">
                Session <span className="font-mono text-blue-600 dark:text-blue-400">{activeSession}</span>
              </div>
              <button
                onClick={handleOpenInNewWindow}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                Pop out
              </button>
            </div>
            <div className="flex-1 min-h-0">
              <ChatWindow sessionId={activeSession} />
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <MessageSquare className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-gray-500">DVA Agent Chat</h2>
              <p className="text-sm text-gray-400 mt-1 max-w-sm">
                Create a new chat session to interact with your agents.
                The agent has access to MCP tools (Bitbucket, Jira, KG, etc.)
              </p>
              <button
                onClick={handleNewSession}
                disabled={creating}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Start Chatting
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
