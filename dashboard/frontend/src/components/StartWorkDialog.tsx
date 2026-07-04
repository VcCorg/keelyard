import { useEffect, useState } from "react";
import {
  X,
  AlertTriangle,
  GitBranch,
  ShieldCheck,
  Laptop,
  Cloud,
  ExternalLink,
  Loader2,
  Boxes,
  BookOpen,
  Package,
  Download,
  Copy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamConsole } from "@/components/StreamConsole";
import { useUser } from "@/context/UserContext";
import {
  api,
  type TaskContract,
  type OpenIdeResult,
  type CreateDevinSessionResponse,
  type PortableContextResult,
} from "@/lib/api";

/**
 * "Start work" launcher — turns a Jira issue into a governed Task Contract and
 * lets the user initiate either execution path:
 *   - Local meta workspace  (sync the Tech-Lead domain workspace + open in Devin/IDE)
 *   - Devin Cloud session    (createDevinSession seeded with snapshot/playbook/KG)
 *
 * P1: no hard enforcement — governance is surfaced and injected into the prompt.
 */
export function StartWorkDialog({ issueKey, onClose }: { issueKey: string; onClose: () => void }) {
  const { can } = useUser();
  const canCreateSession = can("session:create");
  const canBuildContext = can("context:build");
  const [contract, setContract] = useState<TaskContract | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [editors, setEditors] = useState<string[]>([]);
  const [editor, setEditor] = useState("");

  const [syncUrl, setSyncUrl] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const [openResult, setOpenResult] = useState<OpenIdeResult | null>(null);

  const [dryRun, setDryRun] = useState(true);
  const [creating, setCreating] = useState(false);
  const [devinResult, setDevinResult] = useState<CreateDevinSessionResponse | null>(null);
  const [devinError, setDevinError] = useState<string | null>(null);

  const [portableBusy, setPortableBusy] = useState(false);
  const [portable, setPortable] = useState<PortableContextResult | null>(null);
  const [portableError, setPortableError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .getJiraContract(issueKey)
      .then((c) => {
        if (!alive) return;
        setContract(c);
        setPrompt(c.prompt);
      })
      .catch((e) => alive && setLoadError(e?.message || "Failed to build contract"));
    api
      .listEditors()
      .then((r) => {
        if (!alive) return;
        setEditors(r.editors);
        setEditor(r.editors[0] || "devin");
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [issueKey]);

  const slug = contract?.domain.slug || "";

  const runSync = () => {
    if (!slug) return;
    setOpenResult(null);
    setSyncUrl(api.workspaceSyncStreamUrl(slug, { persona: "tech-lead", graphify: true, editor }));
  };

  const openLocal = async () => {
    const path = contract?.local_workspace.path;
    if (!path) return;
    setOpening(true);
    setOpenResult(null);
    try {
      const res = await api.openInIde(path, editor);
      setOpenResult(res);
    } catch (e) {
      setOpenResult({
        success: false,
        editor,
        command: "",
        path,
        message: (e as Error)?.message || "Failed to open",
      });
    } finally {
      setOpening(false);
    }
  };

  const createDevin = async () => {
    if (!contract) return;
    setCreating(true);
    setDevinError(null);
    setDevinResult(null);
    try {
      const res = await api.createDevinSession({
        prompt,
        title: `${contract.issue.key}: ${contract.issue.summary}`.slice(0, 120),
        domain: slug || undefined,
        jira: contract.issue.key,
        snapshot_id: contract.devin.snapshot_id || undefined,
        playbook_id: contract.devin.playbook_id || undefined,
        knowledge_from_sync: true,
        tags: ["jira", contract.issue.project, ...(slug ? [slug] : [])],
        dry_run: dryRun,
      });
      setDevinResult(res);
    } catch (e) {
      setDevinError((e as Error)?.message || "Failed to create session");
    } finally {
      setCreating(false);
    }
  };

  const buildPortable = async () => {
    if (!contract) return;
    setPortableBusy(true);
    setPortableError(null);
    setPortable(null);
    try {
      const res = await api.previewPortableContext({
        prompt,
        title: `${contract.issue.key}: ${contract.issue.summary}`.slice(0, 120),
        jira: contract.issue.key,
        domain: slug || undefined,
        tags: ["jira", contract.issue.project, ...(slug ? [slug] : [])],
      });
      setPortable(res);
    } catch (e) {
      setPortableError((e as Error)?.message || "Failed to render context");
    } finally {
      setPortableBusy(false);
    }
  };

  const downloadPortable = () => {
    if (!portable) return;
    const blob = new Blob([portable.context_md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CONTEXT-${portable.bundle_id || contract?.issue.key || "task"}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const gov = contract?.governance;
  const chips: string[] = [];
  if (gov?.require_code_review) chips.push(`Review · ${gov.min_reviewers ?? 1}+`);
  if (gov?.require_tests)
    chips.push(gov.test_coverage_min ? `Tests · ${gov.test_coverage_min}%` : "Tests");
  if (gov?.require_ci_gates && gov.gates.length) chips.push(`CI · ${gov.gates.length} gate(s)`);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[88vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                {issueKey}
              </span>
              <h2 className="text-base font-semibold">Start work</h2>
            </div>
            {contract && <p className="text-sm text-gray-500 mt-1 truncate">{contract.issue.summary}</p>}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {!contract && !loadError && (
            <p className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" /> Assembling task contract…
            </p>
          )}
          {loadError && (
            <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300 text-sm">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{loadError}</span>
            </div>
          )}

          {contract && (
            <>
              {/* Warnings */}
              {contract.warnings.map((w, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300 text-xs"
                >
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  <span>{w}</span>
                </div>
              ))}

              {/* Contract summary */}
              <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3 space-y-2 text-sm">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span className="text-gray-500">
                    Domain:{" "}
                    {contract.domain.found ? (
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {contract.domain.label} · {contract.domain.product}
                      </span>
                    ) : (
                      <span className="text-amber-600">unresolved</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <GitBranch className="h-3.5 w-3.5 text-gray-400" />
                  <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800">{contract.branch_name}</code>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-gray-400" />
                  {gov?.found ? (
                    chips.length ? (
                      chips.map((c) => (
                        <span
                          key={c}
                          className="text-[11px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                        >
                          {c}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-400">governance found (no explicit gates)</span>
                    )
                  ) : (
                    <span className="text-xs text-gray-400">no governance file — repo conventions apply</span>
                  )}
                </div>
              </div>

              {/* Editable prompt */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Agent goal (governance-injected, editable)
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={7}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-2 text-xs font-mono"
                />
              </div>

              {/* Execution paths */}
              <div className="grid gap-3 sm:grid-cols-2">
                {/* Local */}
                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3 flex flex-col">
                  <div className="flex items-center gap-2 mb-1">
                    <Laptop className="h-4 w-4 text-blue-500" />
                    <p className="text-sm font-medium">Local meta workspace</p>
                  </div>
                  <p className="text-xs text-gray-500 flex-1">{contract.local_workspace.hint || "Tech-Lead domain workspace."}</p>
                  <div className="mt-2 space-y-2">
                    {editors.length > 0 && (
                      <select
                        value={editor}
                        onChange={(e) => setEditor(e.target.value)}
                        className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-xs"
                      >
                        {editors.map((ed) => (
                          <option key={ed} value={ed}>
                            {ed}
                          </option>
                        ))}
                      </select>
                    )}
                    {contract.local_workspace.needs === "sync" ? (
                      <Button size="sm" className="w-full" disabled={!contract.can_launch_local || !!syncUrl} onClick={runSync}>
                        Sync workspace + open
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        className="w-full"
                        disabled={!contract.can_launch_local || opening || !contract.local_workspace.path}
                        onClick={openLocal}
                      >
                        {opening ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : `Open in ${editor || "IDE"}`}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Devin cloud */}
                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3 flex flex-col">
                  <div className="flex items-center gap-2 mb-1">
                    <Cloud className="h-4 w-4 text-blue-500" />
                    <p className="text-sm font-medium">Devin Cloud session</p>
                  </div>
                  <div className="text-xs text-gray-500 flex-1 space-y-1">
                    <p className="flex items-center gap-1">
                      <Boxes className="h-3 w-3" />
                      snapshot: {contract.devin.snapshot_id ? (
                        <span className={contract.devin.snapshot_state === "drift" ? "text-amber-600" : "text-emerald-600"}>
                          {contract.devin.snapshot_state || "set"}
                        </span>
                      ) : (
                        <span className="text-gray-400">none</span>
                      )}
                    </p>
                    <p className="flex items-center gap-1">
                      <BookOpen className="h-3 w-3" />
                      knowledge: {contract.devin.knowledge_folder || "domain default"}
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-gray-500 mt-2">
                    <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
                    Dry run (preview payload, no session)
                  </label>
                  <Button
                    size="sm"
                    className="w-full mt-2"
                    disabled={!contract.can_launch_devin || creating || (!dryRun && !canCreateSession)}
                    title={!dryRun && !canCreateSession ? "Requires the session:create permission (developer+)" : undefined}
                    onClick={createDevin}
                  >
                    {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : dryRun ? "Preview Devin session" : "Create Devin session"}
                  </Button>
                </div>
              </div>

              {/* Portable context — vendor-neutral, any agent */}
              <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-violet-500" />
                    <p className="text-sm font-medium">Portable context bundle</p>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300 uppercase tracking-wide">
                      any agent
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={portableBusy || !canBuildContext}
                    title={canBuildContext ? undefined : "Requires the context:build permission (developer+)"}
                    onClick={buildPortable}
                  >
                    {portableBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Render context"}
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  The same canonical context — governance + domain knowledge — rendered as an
                  engine-neutral bundle for Claude Code, Codex, or any local agent. No vendor, no lock-in.
                </p>
                {portableError && (
                  <div className="mt-2 text-xs px-3 py-2 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300">
                    {portableError}
                  </div>
                )}
                {portable && (
                  <div className="mt-2 space-y-2">
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>
                        bundle <code className="font-mono">{portable.bundle_id}</code> · {portable.resolved}/
                        {portable.item_count} refs resolved
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => navigator.clipboard?.writeText(portable.context_md)}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <Copy className="h-3 w-3" /> Copy
                        </button>
                        <button
                          onClick={downloadPortable}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <Download className="h-3 w-3" /> CONTEXT.md
                        </button>
                      </div>
                    </div>
                    <pre className="max-h-56 overflow-auto rounded-md border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 p-2.5 text-[11px] font-mono whitespace-pre-wrap">
                      {portable.context_md}
                    </pre>
                  </div>
                )}
              </div>

              {/* Local sync stream */}
              <StreamConsole url={syncUrl} title="dva domain sync (tech-lead)" />
              {openResult && (
                <div
                  className={`text-xs px-3 py-2 rounded-lg ${
                    openResult.success
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                      : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                  }`}
                >
                  {openResult.message}
                </div>
              )}

              {/* Devin result */}
              {devinError && (
                <div className="text-xs px-3 py-2 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300">
                  {devinError}
                </div>
              )}
              {devinResult && (
                <div className="text-xs px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800 space-y-1">
                  {devinResult.dry_run ? (
                    <p className="text-gray-600 dark:text-gray-300">
                      Dry run OK · {devinResult.knowledge_count} knowledge item(s) would be attached.
                    </p>
                  ) : devinResult.url ? (
                    <a
                      href={devinResult.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      Open Devin session ({devinResult.status || "created"})
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <p className="text-gray-600 dark:text-gray-300">Session created.</p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
