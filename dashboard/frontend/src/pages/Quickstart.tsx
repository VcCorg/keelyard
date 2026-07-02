import { useMemo, useState, type ComponentType } from "react";
import {
  FileSearch,
  GitBranch,
  MessageSquare,
  GitPullRequest,
  Boxes,
  Bot,
  ArrowRight,
  ArrowLeft,
  Check,
  Rocket,
  Terminal,
  ExternalLink,
  Wand2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { StreamConsole } from "@/components/StreamConsole";

/**
 * Quickstart — a goal-first wizard that scaffolds an agent project in one flow:
 *   Mode → Configure → Build → Done.
 *
 * It builds a `dva project create ...` invocation from the chosen goal and
 * streams it through the existing whitelisted CLI runner, so the wizard is a
 * thin design layer over the real CLI engine (no bespoke backend).
 */

type Framework = "adk" | "langgraph";

interface Mode {
  id: string;
  useCase: string; // maps to `dva project create --use-case <value>`
  title: string;
  blurb: string;
  icon: ComponentType<{ className?: string }>;
  /** Mode-specific toggles surfaced in the Configure step. */
  supports?: { kgMcp?: boolean; jiraMcp?: boolean };
  suggestedTools?: string[];
  defaultFramework?: Framework;
}

const MODES: Mode[] = [
  {
    id: "qa-docs",
    useCase: "rag",
    title: "Q&A over documents",
    blurb: "Answer questions grounded in your docs with retrieval-augmented generation.",
    icon: FileSearch,
    suggestedTools: ["memory", "web_search"],
  },
  {
    id: "kg",
    useCase: "knowledge-graph",
    title: "Knowledge-graph agent",
    blurb: "Reason over a semantic graph of your codebase or domain.",
    icon: GitBranch,
    supports: { kgMcp: true },
  },
  {
    id: "chatbot",
    useCase: "chatbot",
    title: "Conversational chatbot",
    blurb: "A stateful chat agent with memory and context management.",
    icon: MessageSquare,
    suggestedTools: ["memory"],
  },
  {
    id: "pr",
    useCase: "pr-reviewer",
    title: "PR / code reviewer",
    blurb: "Automated pull-request review via Bitbucket + optional Jira.",
    icon: GitPullRequest,
    supports: { jiraMcp: true },
  },
  {
    id: "multi",
    useCase: "multi-agent",
    title: "Multi-agent system",
    blurb: "Orchestrate several agents with a supervisor/router.",
    icon: Boxes,
    defaultFramework: "langgraph",
  },
  {
    id: "basic",
    useCase: "basic",
    title: "Basic agent",
    blurb: "A minimal single-agent starting point to build from.",
    icon: Bot,
  },
];

const ALL_TOOLS = ["web_search", "memory", "api_caller", "file_reader"];

const STEPS = ["Mode", "Configure", "Build", "Done"] as const;

/** Slugify a name into a shell-safe project identifier. */
function slug(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-_]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function Quickstart() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  // Config
  const [mode, setMode] = useState<Mode | null>(null);
  const [name, setName] = useState("");
  const [framework, setFramework] = useState<Framework>("adk");
  const [tools, setTools] = useState<Set<string>>(new Set());
  const [docker, setDocker] = useState(false);
  const [tests, setTests] = useState(true);
  const [kgMcp, setKgMcp] = useState(false);
  const [jiraMcp, setJiraMcp] = useState(false);
  const [overwrite, setOverwrite] = useState(false);

  // Build
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [doneCode, setDoneCode] = useState<string | null>(null);

  const projectSlug = slug(name);

  const command = useMemo(() => {
    if (!mode || !projectSlug) return "";
    const parts = [
      "project create",
      projectSlug,
      `--use-case ${mode.useCase}`,
      `--framework ${framework}`,
    ];
    if (tools.size) parts.push(`--tools ${Array.from(tools).join(",")}`);
    if (mode.supports?.kgMcp && kgMcp) parts.push("--kg-mcp");
    if (mode.supports?.jiraMcp && jiraMcp) parts.push("--jira-mcp");
    if (docker) parts.push("--docker");
    if (!tests) parts.push("--no-tests");
    if (overwrite) parts.push("--force");
    return parts.join(" ");
  }, [mode, projectSlug, framework, tools, kgMcp, jiraMcp, docker, tests, overwrite]);

  const pickMode = (m: Mode) => {
    setMode(m);
    setFramework(m.defaultFramework ?? "adk");
    setTools(new Set(m.suggestedTools ?? []));
    setKgMcp(!!m.supports?.kgMcp);
    setJiraMcp(!!m.supports?.jiraMcp);
    setStep(1);
  };

  const toggleTool = (t: string) =>
    setTools((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });

  const startBuild = () => {
    setDoneCode(null);
    setStreamUrl(api.cliRunStreamUrl(command));
    setStep(2);
  };

  const reset = () => {
    setStep(0);
    setMode(null);
    setName("");
    setFramework("adk");
    setTools(new Set());
    setDocker(false);
    setTests(true);
    setKgMcp(false);
    setJiraMcp(false);
    setOverwrite(false);
    setStreamUrl(null);
    setDoneCode(null);
  };

  const succeeded = doneCode === "0";

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
          <Wand2 className="h-5 w-5 text-blue-600 dark:text-blue-300" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Quickstart</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Scaffold an agent project from a goal — powered by the <code className="font-mono">dva</code> CLI.
          </p>
        </div>
      </div>

      {/* Stepper */}
      <Stepper step={step} />

      {/* Step 1 — Mode */}
      {step === 0 && (
        <div className="grid sm:grid-cols-2 gap-3">
          {MODES.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                onClick={() => pickMode(m)}
                className="group text-left rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 hover:border-blue-300 dark:hover:border-blue-800 hover:shadow-sm transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30">
                    <Icon className="h-4.5 w-4.5 text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-300" />
                  </div>
                  <span className="font-medium text-sm">{m.title}</span>
                  <span className="ml-auto text-[10px] font-mono text-gray-400">{m.useCase}</span>
                </div>
                <p className="text-xs text-gray-500 mt-2 leading-relaxed">{m.blurb}</p>
              </button>
            );
          })}
        </div>
      )}

      {/* Step 2 — Configure */}
      {step === 1 && mode && (
        <div className="space-y-5">
          <SelectedModeBanner mode={mode} onChange={() => setStep(0)} />

          <label className="block">
            <span className="text-xs font-medium text-gray-500">Project name</span>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-agent"
              className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-blue-500/40"
            />
            {name && projectSlug !== name && (
              <span className="text-[11px] text-gray-400 mt-1 inline-block">
                Will be created as <code className="font-mono">{projectSlug || "—"}</code>
              </span>
            )}
          </label>

          <div>
            <span className="text-xs font-medium text-gray-500">Framework</span>
            <div className="mt-1 flex gap-2">
              {(["adk", "langgraph"] as Framework[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFramework(f)}
                  className={cn(
                    "px-3 py-1.5 text-sm rounded-lg border font-medium transition-colors",
                    framework === f
                      ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                      : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400"
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div>
            <span className="text-xs font-medium text-gray-500">Tools</span>
            <div className="mt-1 flex flex-wrap gap-2">
              {ALL_TOOLS.map((t) => (
                <button
                  key={t}
                  onClick={() => toggleTool(t)}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-full border font-medium transition-colors",
                    tools.has(t)
                      ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                      : "border-gray-200 dark:border-gray-800 text-gray-500"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            {mode.supports?.kgMcp && (
              <Toggle label="Include KG MCP server" hint="--kg-mcp" checked={kgMcp} onChange={setKgMcp} />
            )}
            {mode.supports?.jiraMcp && (
              <Toggle label="Include Jira MCP add-on" hint="--jira-mcp" checked={jiraMcp} onChange={setJiraMcp} />
            )}
            <Toggle label="Include Docker files" hint="--docker" checked={docker} onChange={setDocker} />
            <Toggle label="Include test suite" hint="--tests" checked={tests} onChange={setTests} />
            <Toggle label="Overwrite if project exists" hint="--force" checked={overwrite} onChange={setOverwrite} />
          </div>

          {/* Command preview */}
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 p-3">
            <div className="flex items-center gap-1.5 text-[11px] text-gray-400 mb-1">
              <Terminal className="h-3 w-3" /> Command
            </div>
            <code className="text-xs font-mono text-gray-700 dark:text-gray-300 break-all">
              {command ? `dva ${command}` : "Enter a project name…"}
            </code>
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              onClick={() => setStep(0)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </button>
            <button
              onClick={startBuild}
              disabled={!projectSlug}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Build project <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 3 — Build */}
      {step === 2 && mode && (
        <div className="space-y-4">
          <SelectedModeBanner mode={mode} />
          <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 p-3">
            <code className="text-xs font-mono text-gray-700 dark:text-gray-300 break-all">dva {command}</code>
          </div>
          <StreamConsole
            url={streamUrl}
            title={`dva project create ${projectSlug}`}
            onDone={(code) => {
              setDoneCode(code);
              setStep(3);
            }}
          />
        </div>
      )}

      {/* Step 4 — Done */}
      {step === 3 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 text-center space-y-4">
          <div
            className={cn(
              "h-12 w-12 rounded-full mx-auto flex items-center justify-center",
              succeeded ? "bg-green-50 dark:bg-green-900/30" : "bg-red-50 dark:bg-red-900/30"
            )}
          >
            {succeeded ? (
              <Check className="h-6 w-6 text-green-600 dark:text-green-300" />
            ) : (
              <Terminal className="h-6 w-6 text-red-600 dark:text-red-300" />
            )}
          </div>
          <div>
            <h2 className="text-lg font-semibold">
              {succeeded ? `Project '${projectSlug}' created` : "Build finished with errors"}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {succeeded
                ? "Your agent project is scaffolded. Open it in Agent Projects or start the agent."
                : `The CLI exited with code ${doneCode}. Review the output above and try again.`}
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 pt-1">
            <button
              onClick={reset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300"
            >
              <Wand2 className="h-4 w-4" /> Create another
            </button>
            {succeeded && (
              <>
                <button
                  onClick={() => navigate("/projects")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Rocket className="h-4 w-4" /> Agent Projects
                </button>
                <button
                  onClick={() => navigate("/agents")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300"
                >
                  <ExternalLink className="h-4 w-4" /> Agents
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ────────────────────────────────────────────────────── */

function Stepper({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-2">
      {STEPS.map((label, i) => {
        const active = i === step;
        const done = i < step;
        return (
          <div key={label} className="flex items-center gap-2">
            <div
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
                active
                  ? "bg-blue-600 text-white"
                  : done
                  ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  : "bg-gray-100 text-gray-400 dark:bg-gray-800"
              )}
            >
              <span
                className={cn(
                  "h-4 w-4 rounded-full flex items-center justify-center text-[10px]",
                  active ? "bg-white/20" : done ? "bg-blue-200 dark:bg-blue-800" : "bg-gray-200 dark:bg-gray-700"
                )}
              >
                {done ? <Check className="h-2.5 w-2.5" /> : i + 1}
              </span>
              {label}
            </div>
            {i < STEPS.length - 1 && <div className="h-px w-5 bg-gray-200 dark:bg-gray-700" />}
          </div>
        );
      })}
    </div>
  );
}

function SelectedModeBanner({ mode, onChange }: { mode: Mode; onChange?: () => void }) {
  const Icon = mode.icon;
  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 px-3 py-2">
      <div className="h-8 w-8 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
        <Icon className="h-4 w-4 text-blue-600 dark:text-blue-300" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium">{mode.title}</p>
        <p className="text-[11px] text-gray-400 font-mono">--use-case {mode.useCase}</p>
      </div>
      {onChange && (
        <button onClick={onChange} className="ml-auto text-xs text-blue-600 dark:text-blue-400 hover:underline">
          Change
        </button>
      )}
    </div>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-800 text-left hover:bg-gray-50 dark:hover:bg-gray-800/40"
    >
      <span
        className={cn(
          "h-4 w-4 rounded border flex items-center justify-center shrink-0",
          checked ? "bg-blue-600 border-blue-600" : "border-gray-300 dark:border-gray-600"
        )}
      >
        {checked && <Check className="h-3 w-3 text-white" />}
      </span>
      <span className="text-sm flex-1">{label}</span>
      {hint && <code className="text-[10px] font-mono text-gray-400">{hint}</code>}
    </button>
  );
}
