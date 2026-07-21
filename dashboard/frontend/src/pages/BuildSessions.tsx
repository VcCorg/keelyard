import { useEffect, useMemo, useState } from "react";
import {
  Hammer, Cpu, Play, Loader2, ExternalLink, AlertTriangle, MessageCircle, Send,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAdminSettings } from "@/context/AdminSettingsContext";
import { Devin } from "@/pages/Devin";
import { api, type ExecutionEngineInfo, type SessionLaunchResult, type EngineAskResult } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Build Sessions — the vendor-neutral home for launching coding work. The
 * engine picker is limited to the admin-enabled code-assist tools (Admin →
 * Code assist tools), defaulting to the org default. Every engine runs through
 * the same governed seam. Devin's session/snapshot management appears only when
 * Devin is the selected engine.
 */

export function BuildSessions() {
  const { settings } = useAdminSettings();
  const enabled = settings.code_assist.enabled;
  const [engines, setEngines] = useState<ExecutionEngineInfo[]>([]);
  const [engine, setEngine] = useState(settings.code_assist.default);

  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [jira, setJira] = useState("");
  const [domain, setDomain] = useState("");
  const [launching, setLaunching] = useState(false);
  const [result, setResult] = useState<SessionLaunchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<EngineAskResult | null>(null);

  useEffect(() => {
    api.listExecutionEngines().then(setEngines).catch(() => setEngines([]));
  }, []);
  // Keep the selection valid as admin settings load/change.
  useEffect(() => {
    if (!enabled.includes(engine)) setEngine(settings.code_assist.default);
  }, [enabled, settings.code_assist.default]); // eslint-disable-line

  const infoFor = (name: string) => engines.find((e) => e.name === name);
  const pickable = useMemo(
    () => enabled.map((n) => infoFor(n) ?? { name: n, available: true, kind: "?", description: "", detail: "" }),
    [enabled, engines]
  );
  const current = infoFor(engine);
  const isDevin = engine === "devin";
  const isIde = current?.kind === "ide";

  const launch = async (dry: boolean) => {
    if (!prompt.trim()) return;
    setLaunching(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.launchSession({
        prompt: prompt.trim(), title: title.trim() || undefined, jira: jira.trim() || undefined,
        domain: domain.trim() || null, engine, dry_run: dry,
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLaunching(false);
    }
  };

  const ask = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    try {
      setAnswer(await api.askEngine({ prompt: question.trim(), domain: domain.trim() || null, engine }));
    } catch (e) {
      setAnswer({ engine, answer: e instanceof Error ? e.message : String(e), authoritative: false });
    } finally {
      setAsking(false);
    }
  };

  const field = "w-full rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
          <Hammer className="h-6 w-6 text-blue-500" /> Build Sessions
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Launch coding work on your configured code-assist engine. Vendor-neutral — governance and
          audit apply to every engine.
        </p>
      </div>

      {/* Engine picker */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-blue-500" />
          <h2 className="text-sm font-semibold">Code-assist engine</h2>
          <span className="text-xs text-gray-400">org default: <code className="font-mono">{settings.code_assist.default}</code></span>
        </div>
        <div className="flex flex-wrap gap-2">
          {pickable.map((e) => (
            <button
              key={e.name}
              onClick={() => setEngine(e.name)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors",
                engine === e.name
                  ? "border-blue-400 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-300"
                  : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
              )}
            >
              {e.name}
              <span className="text-[10px] uppercase tracking-wide text-gray-400">{e.kind}</span>
              {e.available === false && <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />}
            </button>
          ))}
        </div>
        {current && current.available === false && (
          <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5" /> {current.detail || `${engine} is not available`} —
            configure it or pick another engine.
          </p>
        )}
        {isIde && (
          <p className="text-[11px] text-gray-400">
            {engine} is an IDE handoff: launching prepares a governed context bundle to open in your editor.
          </p>
        )}
      </div>

      {/* Launch form */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-3">
        <h2 className="text-sm font-semibold">Launch a session</h2>
        <textarea className={cn(field, "min-h-[80px] resize-y")} placeholder="Task prompt — what should the engine work on?" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="grid gap-3 sm:grid-cols-3">
          <input className={field} placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className={field} placeholder="Jira key (optional)" value={jira} onChange={(e) => setJira(e.target.value)} />
          <input className={field} placeholder="Domain (optional)" value={domain} onChange={(e) => setDomain(e.target.value)} />
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => launch(false)} disabled={!prompt.trim() || launching}>
            {launching ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Play className="h-4 w-4 mr-1.5" />}
            Launch on {engine}
          </Button>
          <Button variant="outline" onClick={() => launch(true)} disabled={!prompt.trim() || launching}>
            Dry run
          </Button>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">{error}</div>
        )}
        {result && (
          <div className="rounded-lg border border-gray-100 dark:border-gray-800 p-3 text-sm space-y-1">
            <p className="font-medium">
              {result.dry_run ? "Dry run" : "Launched"} on <code className="font-mono">{result.engine}</code>
              {result.status ? ` — ${result.status}` : ""}
            </p>
            {result.url && (
              <a href={result.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline break-all">
                {result.url} <ExternalLink className="h-3 w-3" />
              </a>
            )}
            {typeof result.detail?.instructions === "string" && (
              <pre className="whitespace-pre-wrap text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-950 rounded p-2 mt-1">{result.detail.instructions as string}</pre>
            )}
          </div>
        )}
      </div>

      {/* Ask the engine */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-3">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-blue-500" />
          <h2 className="text-sm font-semibold">Ask {engine}</h2>
          {current && current.supports_ask === false && (
            <span className="text-xs text-amber-600 dark:text-amber-400">this engine answers in the IDE, not here</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            className={field}
            placeholder="Ask a question about the codebase / domain…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
          <Button onClick={ask} disabled={!question.trim() || asking}>
            {asking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
        {answer && (
          <div className={cn("rounded-lg p-3 text-sm", answer.authoritative ? "bg-gray-50 dark:bg-gray-950" : "bg-amber-50 dark:bg-amber-900/20")}>
            {!answer.authoritative && <p className="text-[11px] text-amber-600 dark:text-amber-400 mb-1">non-authoritative (test-mode or IDE handoff)</p>}
            <p className="whitespace-pre-wrap text-gray-700 dark:text-gray-300">{answer.answer}</p>
            {answer.url && (
              <a href={answer.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline mt-1 break-all">
                {answer.url} <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        )}
      </div>

      {/* Devin-specific management — only when Devin is the selected engine */}
      {isDevin && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
          <Devin embedded />
        </div>
      )}
    </div>
  );
}
