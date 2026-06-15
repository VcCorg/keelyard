import { useEffect, useState } from "react";
import { FolderGit2, Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StreamConsole } from "@/components/StreamConsole";
import { RunHistory } from "@/components/RunHistory";
import { api, type DomainInfo, type OnboardParams } from "@/lib/api";

type SourceMode = "repo" | "path";

function Toggle({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={`flex items-start gap-2 ${disabled ? "opacity-50" : "cursor-pointer"}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-gray-300"
      />
      <span>
        <span className="text-sm text-gray-800 dark:text-gray-200">{label}</span>
        {hint && <span className="block text-xs text-gray-400">{hint}</span>}
      </span>
    </label>
  );
}

export function CodeOnboard() {
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [mode, setMode] = useState<SourceMode>("repo");
  const [repo, setRepo] = useState("");
  const [path, setPath] = useState("");
  const [domain, setDomain] = useState("");
  const [tool, setTool] = useState("generic");

  const [kg, setKg] = useState(false);
  const [extractEntities, setExtractEntities] = useState(false);
  const [useDomainSkills, setUseDomainSkills] = useState(false);
  const [linkKg, setLinkKg] = useState(false);
  const [graphify, setGraphify] = useState(false);
  const [agent, setAgent] = useState(false);

  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  useEffect(() => {
    api.listDomains().then(setDomains).catch(() => setDomains([]));
  }, []);

  const start = () => {
    const params: OnboardParams = {
      domain: domain || undefined,
      kg,
      extract_entities: kg && extractEntities,
      use_domain_skills: !!domain && useDomainSkills,
      link_kg: !!domain && kg && linkKg,
      graphify,
      agent,
      code_assist_tool: tool,
    };
    if (mode === "repo") params.repo = repo.trim();
    else params.path = path.trim();
    setRunning(true);
    setStreamUrl(api.codeOnboardStreamUrl(params));
  };

  const canRun = mode === "repo" ? !!repo.trim() : !!path.trim();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <FolderGit2 className="h-7 w-7 text-indigo-500" />
          Code Onboard
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Onboard a repository — install skills, attach domain context, and optionally build KG
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-5">
        {/* Source */}
        <div className="space-y-2">
          <div className="flex gap-2">
            {(["repo", "path"] as SourceMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                  mode === m
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
                    : "border-gray-200 dark:border-gray-700 text-gray-500"
                }`}
              >
                {m === "repo" ? "Git Repo URL" : "Local Path"}
              </button>
            ))}
          </div>
          {mode === "repo" ? (
            <Input placeholder="https://github.com/org/repo.git" value={repo} onChange={(e) => setRepo(e.target.value)} />
          ) : (
            <Input placeholder="/abs/path/to/project" value={path} onChange={(e) => setPath(e.target.value)} />
          )}
        </div>

        {/* Domain + tool */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Domain (optional)</label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">None</option>
              {domains.map((d) => (
                <option key={d.name} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Code assist tool</label>
            <select
              value={tool}
              onChange={(e) => setTool(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="generic">generic</option>
              <option value="windsurf">windsurf</option>
              <option value="cursor">cursor</option>
            </select>
          </div>
        </div>

        {/* Options */}
        <div className="grid sm:grid-cols-2 gap-3">
          <Toggle label="Build KG" hint="Generate code context + ingest into KG" checked={kg} onChange={setKg} />
          <Toggle
            label="Extract entities"
            hint="Full KG ingestion with entity extraction"
            checked={extractEntities}
            onChange={setExtractEntities}
            disabled={!kg}
          />
          <Toggle
            label="Use domain skills"
            hint="Install domain-validated skills (requires domain)"
            checked={useDomainSkills}
            onChange={setUseDomainSkills}
            disabled={!domain}
          />
          <Toggle
            label="Link KG"
            hint="Link code to requirements (requires domain + KG)"
            checked={linkKg}
            onChange={setLinkKg}
            disabled={!domain || !kg}
          />
          <Toggle label="Graphify" hint="Generate code structure graph" checked={graphify} onChange={setGraphify} />
          <Toggle label="Use AI agent" hint="Agent-driven skill gap detection" checked={agent} onChange={setAgent} />
        </div>

        <div className="flex justify-end">
          <Button disabled={!canRun || running} onClick={start}>
            {running ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Play className="h-4 w-4 mr-1.5" />}
            Onboard
          </Button>
        </div>
      </div>

      <StreamConsole
        url={streamUrl}
        title="dva code onboard"
        onDone={() => {
          setRunning(false);
          setHistoryKey((k) => k + 1);
        }}
      />

      <RunHistory kind="code" refreshKey={historyKey} title="Onboarding History" />
    </div>
  );
}
