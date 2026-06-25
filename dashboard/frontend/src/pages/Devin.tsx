import { useCallback, useEffect, useState } from "react";
import {
  Bot,
  Plus,
  RefreshCw,
  ExternalLink,
  Send,
  KeyRound,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  MinusCircle,
  MessagesSquare,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type DevinSession,
  type DevinStatus,
  type CreateDevinSessionRequest,
  type CreateDevinSessionResponse,
  type DevinSessionDetail,
} from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  blocked: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  finished: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  expired: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

function statusClass(status?: string | null): string {
  if (!status) return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
  return STATUS_COLORS[status.toLowerCase()] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
}

export function Devin() {
  const statusFetcher = useCallback(() => api.getDevinStatus(), []);
  const { data: status } = usePolling<DevinStatus>(statusFetcher, 30000);

  const sessionsFetcher = useCallback(() => api.listDevinSessions(), []);
  const { data: sessions, loading, refresh } = usePolling<DevinSession[]>(sessionsFetcher, 10000);

  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<DevinSessionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();

  const openDetail = useCallback(async (sessionId: string) => {
    setDetailLoading(true);
    try {
      setSelected(await api.getDevinSession(sessionId));
    } catch (err) {
      console.error("Failed to load session:", err);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Deep-link: when arriving from the Skills validate flow (?session=<id>),
  // auto-open that session, then clear the param so refreshes don't reopen it.
  useEffect(() => {
    const sid = searchParams.get("session");
    if (!sid) return;
    openDetail(sid);
    searchParams.delete("session");
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams, openDetail]);

  const sendMessage = async () => {
    if (!selected || !message.trim()) return;
    try {
      await api.sendDevinMessage(selected.session_id, message.trim());
      setMessage("");
      await openDetail(selected.session_id);
    } catch (err) {
      console.error("Failed to send message:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
            <Bot className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Devin Sessions</h1>
            <p className="text-sm text-gray-500">Trigger and track autonomous coding sessions.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            New Session
          </button>
        </div>
      </div>

      {/* Status banner */}
      {status && !status.api_key_present && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300 text-sm">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            No <code>DEVIN_API_KEY</code> detected on the backend. Live session creation is disabled — only{" "}
            <strong>dry-run</strong> previews will work.
          </span>
        </div>
      )}
      {status?.api_key_present && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <KeyRound className="h-3.5 w-3.5 text-green-600" />
          Connected to <code>{status.base_url}</code> · default budget {status.default_max_acu} ACU
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Session list */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Tracked Sessions {sessions ? `(${sessions.length})` : ""}
          </h2>
          {sessions && sessions.length === 0 && (
            <div className="text-sm text-gray-500 border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 text-center">
              No sessions yet. Click <strong>New Session</strong> to trigger Devin.
            </div>
          )}
          {sessions?.map((s) => (
            <button
              key={s.session_id}
              onClick={() => openDetail(s.session_id)}
              className={`w-full text-left p-4 rounded-lg border transition-colors ${
                selected?.session_id === s.session_id
                  ? "border-blue-400 bg-blue-50/50 dark:bg-blue-900/10"
                  : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium truncate">{s.title || s.session_id}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs ${statusClass(s.status)}`}>
                  {s.status || "unknown"}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5 text-xs text-gray-500">
                {s.domain && <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800">{s.domain}</span>}
                {s.jira && <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800">{s.jira}</span>}
                {s.created_at && <span>{new Date(s.created_at).toLocaleString()}</span>}
              </div>
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Session Detail</h2>
          {!selected && (
            <div className="text-sm text-gray-500 border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 text-center">
              Select a session to view live status and output.
            </div>
          )}
          {selected && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <code className="text-sm">{selected.session_id}</code>
                <span className={`px-2 py-0.5 rounded-full text-xs ${statusClass(selected.status)}`}>
                  {detailLoading ? "loading…" : selected.status || "unknown"}
                </span>
              </div>
              {selected.url && (
                <a
                  href={selected.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                >
                  Open in Devin <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              {selected.structured_output != null && (
                <VerdictCard output={selected.structured_output} />
              )}
              <Transcript raw={selected.raw} />
              <div className="flex items-center gap-2 pt-1">
                <input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder="Send a follow-up message…"
                  className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent"
                />
                <button
                  onClick={sendMessage}
                  disabled={!message.trim()}
                  className="flex items-center gap-1 px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {showForm && (
        <CreateSessionModal
          apiKeyPresent={!!status?.api_key_present}
          onClose={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function CreateSessionModal({
  apiKeyPresent,
  onClose,
  onCreated,
}: {
  apiKeyPresent: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<CreateDevinSessionRequest>({
    prompt: "",
    title: "",
    domain: "",
    jira: "",
    knowledge_from_sync: true,
    idempotent: true,
    dry_run: !apiKeyPresent,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CreateDevinSessionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!form.prompt.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.createDevinSession({
        ...form,
        domain: form.domain || undefined,
      });
      setResult(res);
      if (!res.dry_run) onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 max-h-[90vh] overflow-y-auto">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold">New Devin Session</h3>
        </div>
        <div className="p-5 space-y-4">
          <Field label="Prompt *">
            <textarea
              value={form.prompt}
              onChange={(e) => setForm({ ...form, prompt: e.target.value })}
              rows={4}
              placeholder="Describe the task for Devin…"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Title">
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent"
              />
            </Field>
            <Field label="Jira Key">
              <input
                value={form.jira}
                onChange={(e) => setForm({ ...form, jira: e.target.value })}
                placeholder="PROJ-123"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent"
              />
            </Field>
          </div>
          <Field label="Domain">
            <input
              value={form.domain ?? ""}
              onChange={(e) => setForm({ ...form, domain: e.target.value })}
              placeholder="cwow-facility"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent"
            />
          </Field>
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.knowledge_from_sync}
                onChange={(e) => setForm({ ...form, knowledge_from_sync: e.target.checked })}
              />
              Attach domain knowledge
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.idempotent}
                onChange={(e) => setForm({ ...form, idempotent: e.target.checked })}
              />
              Idempotent
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.dry_run}
                onChange={(e) => setForm({ ...form, dry_run: e.target.checked })}
              />
              Dry run
            </label>
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">{error}</div>
          )}

          {result && (
            <div className="text-sm rounded-lg p-3 bg-gray-50 dark:bg-gray-800 space-y-2">
              {result.dry_run ? (
                <>
                  <p className="font-medium">Dry-run preview ({result.knowledge_count} knowledge attached)</p>
                  <pre className="text-xs overflow-x-auto max-h-48">
                    {JSON.stringify(result.payload, null, 2)}
                  </pre>
                </>
              ) : (
                <p className="font-medium text-green-700 dark:text-green-400">
                  Session {result.session_id} created ({result.is_new ? "new" : "reused"}).
                </p>
              )}
            </div>
          )}
        </div>
        <div className="px-5 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Close
          </button>
          <button
            onClick={submit}
            disabled={submitting || !form.prompt.trim()}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Working…" : form.dry_run ? "Preview" : "Create Session"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-gray-500 mb-1">{label}</span>
      {children}
    </label>
  );
}

/* ── Verdict card ──────────────────────────────────────────────────────────
 * Renders a skill-validation verdict (PASS/FAIL/PARTIAL) when the session's
 * structured_output matches our schema; otherwise falls back to a JSON dump.
 */

interface Verdict {
  verdict?: string;
  summary?: string;
  what_worked?: string[];
  issues?: string[];
  edge_cases_tested?: string[];
  suggested_skill_edits?: string[];
}

const VERDICT_STYLE: Record<string, { cls: string; Icon: typeof CheckCircle2 }> = {
  PASS: { cls: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-900/50", Icon: CheckCircle2 },
  FAIL: { cls: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-900/50", Icon: XCircle },
  PARTIAL: { cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-900/50", Icon: MinusCircle },
};

function parseVerdict(output: unknown): Verdict | null {
  let obj: unknown = output;
  if (typeof output === "string") {
    try {
      obj = JSON.parse(output);
    } catch {
      return null;
    }
  }
  if (!obj || typeof obj !== "object") return null;
  const v = obj as Verdict;
  if (!v.verdict && !v.summary && !v.what_worked && !v.issues) return null;
  return v;
}

function VerdictCard({ output }: { output: unknown }) {
  const v = parseVerdict(output);
  if (!v) {
    return (
      <pre className="text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto max-h-64">
        {JSON.stringify(output, null, 2)}
      </pre>
    );
  }
  const key = (v.verdict || "").toUpperCase();
  const style = VERDICT_STYLE[key] ?? VERDICT_STYLE.PARTIAL;
  const Icon = style.Icon;
  return (
    <div className="space-y-3">
      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-semibold ${style.cls}`}>
        <Icon className="h-4 w-4" />
        {key || "RESULT"}
      </div>
      {v.summary && <p className="text-sm text-gray-600 dark:text-gray-300">{v.summary}</p>}
      <VerdictList title="What worked" items={v.what_worked} tone="good" />
      <VerdictList title="Issues" items={v.issues} tone="bad" />
      <VerdictList title="Edge cases tested" items={v.edge_cases_tested} tone="neutral" />
      <VerdictList title="Suggested SKILL.md edits" items={v.suggested_skill_edits} tone="neutral" />
    </div>
  );
}

function VerdictList({
  title,
  items,
  tone,
}: {
  title: string;
  items?: string[];
  tone: "good" | "bad" | "neutral";
}) {
  if (!items || items.length === 0) return null;
  const dot =
    tone === "good" ? "bg-green-500" : tone === "bad" ? "bg-red-500" : "bg-gray-400";
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{title}</p>
      <ul className="space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-300">
            <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Transcript ────────────────────────────────────────────────────────────
 * Renders the session message history from raw.messages so reviewers don't
 * have to open Devin. Defensive about the exact message shape.
 */

interface RawMessage {
  type?: string;
  role?: string;
  message?: string;
  content?: string;
  text?: string;
  timestamp?: string;
  created_at?: string;
}

function messageText(m: RawMessage): string {
  return m.message ?? m.content ?? m.text ?? "";
}

function Transcript({ raw }: { raw: Record<string, unknown> }) {
  const [open, setOpen] = useState(true);
  const messages = Array.isArray(raw?.messages) ? (raw.messages as RawMessage[]) : [];
  if (messages.length === 0) return null;
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <MessagesSquare className="h-3.5 w-3.5" />
        Transcript ({messages.length})
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2 max-h-72 overflow-y-auto">
          {messages.map((m, i) => {
            const who = (m.type || m.role || "message").toLowerCase();
            const isDevin = who.includes("devin") || who.includes("assistant") || who.includes("ai");
            const text = messageText(m);
            if (!text) return null;
            return (
              <div
                key={i}
                className={`text-sm rounded-lg px-3 py-2 ${
                  isDevin
                    ? "bg-blue-50 dark:bg-blue-900/20 text-gray-700 dark:text-gray-200"
                    : "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200"
                }`}
              >
                <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-0.5">
                  {who}
                </p>
                <p className="whitespace-pre-wrap">{text}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
