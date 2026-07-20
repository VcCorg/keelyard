import { useEffect, useMemo, useRef, useState } from "react";
import {
  FlaskConical, Package, Boxes, ChevronRight, ChevronLeft, Play, Loader2,
  CheckCircle2, AlertTriangle, XCircle, MinusCircle, ArrowUpToLine, ShieldCheck,
  Upload, FolderUp, FileUp, Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamConsole } from "@/components/StreamConsole";
import { useUser } from "@/context/UserContext";
import { api, type IngestableDomain } from "@/lib/api";

/**
 * Skill Trials — test a registry skill against a specific domain BEFORE it
 * reaches the domain's validated tier or the master skills repo.
 *
 * Any role runs the trial (structure, security scan, persona policy, AI
 * review); a lead promotes passing skills into the domain-context repo's
 * validated tier — the same tier `keel code onboard --use-domain-skills`
 * installs first.
 */

type Step = "skill" | "domain" | "scorecard";

interface RegistrySkill {
  name: string;
  description?: string;
}

interface TrialCheck {
  name: string;
  status: "pass" | "warn" | "fail" | "skipped";
  detail: string;
}

interface JudgeScenario {
  scenario: string;
  with_skill_score: number;
  baseline_score: number;
  winner: "with_skill" | "baseline" | "tie";
  rationale: string;
}

interface JudgeReport {
  judge: string;
  avg_with_skill: number;
  avg_baseline: number;
  delta: number;
  verdict: "positive" | "neutral" | "negative";
  authoritative: boolean;
  scenarios: JudgeScenario[];
}

interface AuditRow {
  subcommand?: string;
  action?: string;
  entity_id?: string;
  status?: string;
  timestamp?: string;
  actor?: string;
  details?: Record<string, unknown>;
}

interface Scorecard {
  skill: string;
  domain: string;
  persona: string;
  verdict: "pass" | "warn" | "fail";
  checks: TrialCheck[];
  ai_provider: string;
  promotable: boolean;
}

const STATUS_ICON = {
  pass: { Icon: CheckCircle2, cls: "text-emerald-500" },
  warn: { Icon: AlertTriangle, cls: "text-amber-500" },
  fail: { Icon: XCircle, cls: "text-red-500" },
  skipped: { Icon: MinusCircle, cls: "text-gray-400" },
} as const;

export function SkillTrials() {
  const { user, auth } = useUser();
  const isLead = user.role === "lead" || user.role === "admin";

  const [step, setStep] = useState<Step>("skill");
  const [skills, setSkills] = useState<RegistrySkill[]>([]);
  const [skill, setSkill] = useState("");
  const [filter, setFilter] = useState("");
  const [domains, setDomains] = useState<IngestableDomain[]>([]);
  const [domain, setDomain] = useState("");

  const [running, setRunning] = useState(false);
  const [card, setCard] = useState<Scorecard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [promoting, setPromoting] = useState(false);
  const [promoted, setPromoted] = useState<string | null>(null);
  const [judging, setJudging] = useState(false);
  const [judge, setJudge] = useState<JudgeReport | null>(null);
  const [history, setHistory] = useState<AuditRow[]>([]);

  // Security scanner (SkillSpector) availability + per-trial toggle.
  const [scanner, setScanner] = useState<{ available: boolean; version?: string } | null>(null);
  const [runSecurity, setRunSecurity] = useState(true);
  const [installUrl, setInstallUrl] = useState<string | null>(null);

  // Upload a candidate skill (file or folder) into the registry.
  const [uploadName, setUploadName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);

  const loadSkills = () =>
    fetch("/api/skills/list")
      .then((r) => r.json())
      .then((d) => setSkills(d.skills ?? []))
      .catch(() => setSkills([]));

  const loadScanner = () =>
    fetch("/api/skills/security/status")
      .then((r) => r.json())
      .then((d) => { setScanner(d); setRunSecurity(!!d.available); })
      .catch(() => setScanner({ available: false }));

  const loadHistory = () =>
    fetch("/api/skills/audit?limit=25")
      .then((r) => r.json())
      .then((d) => setHistory(d.actions ?? []))
      .catch(() => setHistory([]));

  useEffect(() => {
    loadSkills();
    api.listIngestableDomains().then(setDomains).catch(() => setDomains([]));
    loadScanner();
    loadHistory();
  }, []);

  const handleUpload = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    setUploading(true);
    setUploadErr(null);
    setUploadMsg(null);
    try {
      const files = await Promise.all(
        Array.from(list).map(async (f) => ({
          path: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name,
          content: await f.text(),
        }))
      );
      const r = await fetch("/api/skills/trial/upload", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ skill_name: uploadName.trim(), files }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `status ${r.status}`);
      const res = await r.json();
      await loadSkills();
      setSkill(res.skill);
      setUploadName("");
      setUploadMsg(`Loaded '${res.skill}' (${res.files} file${res.files === 1 ? "" : "s"}) — select it below to trial.`);
    } catch (e) {
      setUploadErr(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
      if (folderRef.current) folderRef.current.value = "";
    }
  };

  const filtered = useMemo(
    () => skills.filter((s) => !filter || s.name.toLowerCase().includes(filter.toLowerCase())),
    [skills, filter]
  );

  const runTrial = async () => {
    setRunning(true);
    setError(null);
    setCard(null);
    setPromoted(null);
    try {
      const r = await fetch("/api/skills/trial/evaluate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ skill_name: skill, domain, run_security: runSecurity }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `status ${r.status}`);
      setCard(await r.json());
      loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const runJudge = async () => {
    setJudging(true);
    setError(null);
    setJudge(null);
    try {
      const r = await fetch("/api/skills/trial/judge", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ skill_name: skill, domain, scenarios: 3 }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `status ${r.status}`);
      setJudge(await r.json());
      loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setJudging(false);
    }
  };

  const promote = async () => {
    setPromoting(true);
    setError(null);
    try {
      const r = await fetch("/api/skills/trial/promote", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ skill_name: skill, domain }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `status ${r.status}`);
      const res = await r.json();
      setPromoted(res.promoted_to);
      loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPromoting(false);
    }
  };

  const steps: Step[] = ["skill", "domain", "scorecard"];
  const stepIndex = steps.indexOf(step);
  const canNext = step === "skill" ? !!skill : step === "domain" ? !!domain : false;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <FlaskConical className="h-7 w-7 text-blue-500" /> Skill Trials
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Test a skill against a domain before it joins the validated tier — any role can
          trial; leads promote
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2 text-xs">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-full font-medium ${
                i === stepIndex
                  ? "bg-blue-600 text-white"
                  : i < stepIndex
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                    : "bg-gray-100 text-gray-500 dark:bg-gray-800"
              }`}
            >
              {i + 1}. {s === "skill" ? "Pick skill" : s === "domain" ? "Pick domain" : "Trial scorecard"}
            </span>
            {i < steps.length - 1 && <ChevronRight className="h-3.5 w-3.5 text-gray-300" />}
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 space-y-5">
        {step === "skill" && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Package className="h-4 w-4 text-blue-500" /> Which skill do you want to trial?
            </h2>

            {/* Load a new candidate skill (file or folder) into the registry. */}
            <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-3 space-y-2">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Upload className="h-3.5 w-3.5" /> Load a new skill to trial — a folder of files
                (preferred) or a single SKILL.md.
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  placeholder="Skill name (optional for folders)"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  className="h-8 flex-1 min-w-[10rem] rounded-md border border-input bg-background px-2.5 text-sm"
                />
                <Button size="sm" variant="outline" disabled={uploading} onClick={() => folderRef.current?.click()}>
                  {uploading ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <FolderUp className="h-3.5 w-3.5 mr-1.5" />}
                  Folder
                </Button>
                <Button size="sm" variant="outline" disabled={uploading} onClick={() => fileRef.current?.click()}>
                  <FileUp className="h-3.5 w-3.5 mr-1.5" /> File(s)
                </Button>
                <input ref={fileRef} type="file" multiple hidden onChange={(e) => handleUpload(e.target.files)} />
                <input
                  ref={(el) => {
                    if (el) { el.setAttribute("webkitdirectory", ""); el.setAttribute("directory", ""); }
                    folderRef.current = el;
                  }}
                  type="file"
                  multiple
                  hidden
                  onChange={(e) => handleUpload(e.target.files)}
                />
              </div>
              {uploadErr && <p className="text-xs text-red-600 dark:text-red-400">{uploadErr}</p>}
              {uploadMsg && <p className="text-xs text-emerald-600 dark:text-emerald-400">{uploadMsg}</p>}
            </div>

            <input
              placeholder="Filter skills…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1">
              {filtered.map((s) => (
                <button
                  key={s.name}
                  onClick={() => setSkill(s.name)}
                  className={`w-full text-left rounded-lg border px-3 py-2 text-sm transition-colors ${
                    skill === s.name
                      ? "border-blue-500 bg-blue-50/60 dark:bg-blue-900/10"
                      : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                  }`}
                >
                  <span className="font-medium">{s.name}</span>
                  {s.description && (
                    <span className="block text-xs text-gray-500 truncate">{s.description}</span>
                  )}
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="text-xs text-gray-400 p-2">No skills in the registry match.</p>
              )}
            </div>
          </div>
        )}

        {step === "domain" && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Boxes className="h-4 w-4 text-blue-500" /> Trial against which domain?
            </h2>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Select a domain…</option>
              {domains.map((d) => (
                <option key={d.slug} value={d.slug}>{d.slug}</option>
              ))}
            </select>
            <p className="text-[11px] text-gray-400">
              The trial checks the domain's persona skill policy for <strong>your</strong>{" "}
              persona (<code className="font-mono">{auth.persona}</code>) — exactly what
              enforcement would apply at onboard time.
            </p>
          </div>
        )}

        {step === "scorecard" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">
                Trial: <code className="font-mono">{skill}</code> → <code className="font-mono">{domain}</code>
              </h2>
              {!card && (
                <Button onClick={runTrial} disabled={running}>
                  {running ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Play className="h-4 w-4 mr-1.5" />}
                  Run trial
                </Button>
              )}
            </div>

            {/* Security scanner control — toggle the scan, or install the
                scanner (SkillSpector) if it isn't on the backend. */}
            {!card && (
              scanner?.available ? (
                <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={runSecurity}
                    onChange={(e) => setRunSecurity(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  Run security scan
                  <span className="text-xs text-gray-400 font-mono">
                    SkillSpector{scanner.version ? ` ${scanner.version}` : ""}
                  </span>
                </label>
              ) : (
                <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-3 space-y-2">
                  <p className="text-xs text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Security scanner (SkillSpector) isn't installed — the trial's security check
                    will be skipped.
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setInstallUrl("/api/skills/security/install/stream")}
                  >
                    <Download className="h-3.5 w-3.5 mr-1.5" /> Install scanner
                  </Button>
                  <StreamConsole
                    url={installUrl}
                    title="install skillspector"
                    onDone={() => { loadScanner(); }}
                  />
                  <p className="text-[11px] text-amber-700/80 dark:text-amber-400/80">
                    Runs <code className="font-mono">uv tool install …/skillspector</code> on the
                    backend host (needs <code className="font-mono">uv</code> on PATH).
                  </p>
                </div>
              )
            )}

            {error && (
              <div className="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">{error}</div>
            )}

            {card && (
              <>
                <div className="space-y-2">
                  {card.checks.map((c) => {
                    const { Icon, cls } = STATUS_ICON[c.status];
                    return (
                      <div key={c.name} className="flex items-start gap-3 rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${cls}`} />
                        <div>
                          <p className="text-sm font-medium">{c.name}</p>
                          <p className="text-xs text-gray-500">{c.detail}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div
                  className={`rounded-lg p-4 text-sm flex items-center gap-2 ${
                    card.verdict === "pass"
                      ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-900/10 dark:text-emerald-300"
                      : card.verdict === "warn"
                        ? "bg-amber-50 text-amber-800 dark:bg-amber-900/10 dark:text-amber-300"
                        : "bg-red-50 text-red-800 dark:bg-red-900/10 dark:text-red-300"
                  }`}
                >
                  <ShieldCheck className="h-4 w-4" />
                  Verdict: <strong className="uppercase">{card.verdict}</strong>
                  {card.verdict === "warn" && " — a lead can still promote (judgement call)"}
                  {card.verdict === "fail" && " — fix the failing checks before promotion"}
                </div>

                {/* LLM-as-judge impact evaluation (deep, on demand) */}
                <div className="rounded-lg border border-gray-100 dark:border-gray-800 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium flex items-center gap-1.5">
                        <FlaskConical className="h-4 w-4 text-violet-500" /> LLM-as-judge impact
                      </p>
                      <p className="text-[11px] text-gray-400">
                        Answers 3 scenarios with and without the skill; a blind judge scores both.
                      </p>
                    </div>
                    {!judge && (
                      <Button size="sm" variant="outline" onClick={runJudge} disabled={judging}>
                        {judging ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Play className="h-4 w-4 mr-1.5" />}
                        {judging ? "Judging…" : "Run evaluation"}
                      </Button>
                    )}
                  </div>
                  {judge && (
                    <>
                      {!judge.authoritative && (
                        <p className="text-[11px] text-amber-600 dark:text-amber-400">
                          Judged by the test-mode provider — configure a real model for an
                          authoritative result.
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-sm">
                        <span>With skill: <strong>{judge.avg_with_skill}</strong></span>
                        <span>Baseline: <strong>{judge.avg_baseline}</strong></span>
                        <span className={
                          judge.verdict === "positive" ? "text-emerald-600 dark:text-emerald-400"
                          : judge.verdict === "negative" ? "text-red-600 dark:text-red-400"
                          : "text-gray-500"
                        }>
                          Δ {judge.delta > 0 ? "+" : ""}{judge.delta} — <strong className="uppercase">{judge.verdict}</strong> impact
                        </span>
                        <span className="text-[11px] text-gray-400 ml-auto font-mono">{judge.judge}</span>
                      </div>
                      <div className="space-y-1.5">
                        {judge.scenarios.map((sc, i) => (
                          <div key={i} className="text-xs rounded border border-gray-100 dark:border-gray-800 p-2">
                            <p className="font-medium truncate">{sc.scenario}</p>
                            <p className="text-gray-500">
                              with {sc.with_skill_score} vs base {sc.baseline_score} — winner:{" "}
                              <span className={
                                sc.winner === "with_skill" ? "text-emerald-600 dark:text-emerald-400"
                                : sc.winner === "baseline" ? "text-red-600 dark:text-red-400"
                                : "text-gray-500"
                              }>{sc.winner.replace("_", " ")}</span>
                              {sc.rationale && <span className="text-gray-400"> · {sc.rationale}</span>}
                            </p>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>

                {promoted ? (
                  <div className="rounded-lg border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/60 dark:bg-emerald-900/10 p-4 text-sm text-emerald-800 dark:text-emerald-300">
                    <p className="font-medium">Promoted to the domain's validated tier.</p>
                    <p className="text-xs font-mono mt-1">{promoted}</p>
                    <p className="text-xs mt-1">
                      Commit + push the domain-context repo to share it; it now installs first
                      via <code className="font-mono">keel code onboard --use-domain-skills</code>.
                    </p>
                  </div>
                ) : isLead ? (
                  <Button onClick={promote} disabled={!card.promotable || promoting} variant={card.promotable ? "default" : "outline"}>
                    {promoting ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <ArrowUpToLine className="h-4 w-4 mr-1.5" />}
                    Promote to '{domain}' validated skills
                  </Button>
                ) : (
                  <p className="text-xs text-gray-500">
                    Promotion into the domain's validated tier is a lead action — share this
                    scorecard with your tech lead (the trial is already in the audit trail).
                  </p>
                )}

                <Button variant="outline" size="sm" onClick={() => { setCard(null); setPromoted(null); setJudge(null); }}>
                  Re-run trial
                </Button>
              </>
            )}
          </div>
        )}

        {/* Nav */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800">
          <Button variant="outline" size="sm" disabled={stepIndex === 0 || running} onClick={() => setStep(steps[stepIndex - 1])}>
            <ChevronLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          {step !== "scorecard" && (
            <Button size="sm" disabled={!canNext} onClick={() => setStep(steps[stepIndex + 1])}>
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </div>

      {/* Trial audit history */}
      {history.length > 0 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
          <h2 className="text-sm font-semibold mb-3">Recent trial activity</h2>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {history.map((h, i) => {
              const act = (h.subcommand || h.action || "").replace("trial_", "");
              const d = (h.details || {}) as Record<string, unknown>;
              const meta =
                act === "judge" ? `Δ ${d.delta ?? "?"} · ${d.verdict ?? ""}`
                : act === "evaluate" ? `${d.verdict ?? ""}`
                : act === "promote" ? `→ ${d.domain ?? ""}`
                : "";
              return (
                <div key={i} className="flex items-center gap-2 text-xs border-b border-gray-50 dark:border-gray-800/50 py-1.5">
                  <span className={`px-1.5 py-0.5 rounded font-medium ${
                    act === "promote" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                    : act === "judge" ? "bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                  }`}>{act}</span>
                  <span className="font-mono truncate max-w-[10rem]">{h.entity_id}</span>
                  <span className="text-gray-400">{meta}</span>
                  <span className="text-gray-400 ml-auto">{h.actor || ""}</span>
                  {h.timestamp && <span className="text-gray-300 dark:text-gray-600">{new Date(h.timestamp).toLocaleString()}</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
