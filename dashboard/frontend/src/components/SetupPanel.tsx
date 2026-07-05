import { useState } from "react";
import { Check, X, AlertTriangle, Terminal, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamConsole } from "@/components/StreamConsole";
import { useSetup } from "@/context/SetupContext";
import { api, type SetupItem } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Items configured through an in-panel form (streams `dva init ...`). The
 * PAT-based integrations (Jira/Bitbucket/Confluence) write their URL + token to
 * ~/.dva/.env via the CLI, so they no longer need to be exported into the shell.
 * Devin remains env-only (its key is never persisted to disk).
 */
const FORM_CONFIGURABLE = new Set([
  "workspaces",
  "vertex_ai",
  "neo4j",
  "jira",
  "bitbucket",
  "confluence",
]);

const INTEGRATION_KEYS = ["jira", "bitbucket", "confluence"] as const;
type IntegrationKind = (typeof INTEGRATION_KEYS)[number];

function StatusDot({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400">
      <Check className="h-3.5 w-3.5" />
    </span>
  ) : (
    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
      <X className="h-3.5 w-3.5" />
    </span>
  );
}

function ItemRow({
  item,
  onConfigure,
  active,
  children,
}: {
  item: SetupItem;
  onConfigure: () => void;
  active: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
      <div className="flex items-start gap-3">
        <StatusDot ok={item.configured} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.label}</p>
            <span
              className={cn(
                "text-[10px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wide",
                item.required
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
              )}
            >
              {item.required ? "required" : "optional"}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{item.detail}</p>
          <code className="text-[11px] text-gray-400 break-all">{item.fix_hint}</code>
        </div>
        {FORM_CONFIGURABLE.has(item.key) && (
          <Button size="sm" variant={item.configured ? "outline" : "default"} onClick={onConfigure}>
            <Settings2 className="h-3.5 w-3.5 mr-1.5" />
            {item.configured ? "Reconfigure" : "Configure"}
          </Button>
        )}
      </div>
      {active && children}
    </div>
  );
}

export function SetupPanel({ onClose }: { onClose: () => void }) {
  const { status, loading, refresh } = useSetup();
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  // form state
  const [code, setCode] = useState("");
  const [docs, setDocs] = useState("");
  const [projectId, setProjectId] = useState("");
  const [location, setLocation] = useState("us-central1");
  const [neoUri, setNeoUri] = useState("bolt://localhost:7687");
  const [neoUser, setNeoUser] = useState("neo4j");
  const [neoPwd, setNeoPwd] = useState("");
  // Per-integration URL + token (Jira / Bitbucket / Confluence).
  const [intg, setIntg] = useState<Record<string, { url: string; token: string }>>({});
  const setIntgField = (key: IntegrationKind, field: "url" | "token", value: string) =>
    setIntg((prev) => ({
      ...prev,
      [key]: { url: "", token: "", ...prev[key], [field]: value },
    }));

  const toggle = (key: string) => {
    setStreamUrl(null);
    setOpenKey((k) => (k === key ? null : key));
  };

  const onDone = () => refresh();

  const fieldCls =
    "w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2.5 py-1.5 text-sm";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-blue-500" />
            <h2 className="text-base font-semibold">CLI Setup</h2>
            {status && (
              <span
                className={cn(
                  "text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase",
                  status.ready
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                    : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                )}
              >
                {status.ready ? "ready" : "action needed"}
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {!status?.cli_available && (
            <div className="flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-300">
              <AlertTriangle className="h-4 w-4 mt-0.5" />
              <div>
                The <code>dva</code> CLI is not available to the backend. Install it:
                <code className="block mt-1">./install-agentic-cli.sh</code>
              </div>
            </div>
          )}

          <p className="text-sm text-gray-500 dark:text-gray-400">
            These steps initialize the <code>dva</code> CLI that powers onboarding, KG ingest, OKF
            and agents. Required items must be configured before those workflows can run.
          </p>

          {loading && !status && <p className="text-sm text-gray-400">Loading status…</p>}

          {status?.items.map((item) => (
            <ItemRow key={item.key} item={item} active={openKey === item.key} onConfigure={() => toggle(item.key)}>
              <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 space-y-2">
                {item.key === "workspaces" && (
                  <>
                    <input className={fieldCls} placeholder="Code workspace dir (e.g. ~/dva-code-workspace)" value={code} onChange={(e) => setCode(e.target.value)} />
                    <input className={fieldCls} placeholder="Docs workspace dir (e.g. ~/dva-doc-workspace)" value={docs} onChange={(e) => setDocs(e.target.value)} />
                    <Button size="sm" disabled={!code.trim() || !docs.trim()} onClick={() => setStreamUrl(api.setupWorkspaceStreamUrl(code.trim(), docs.trim()))}>
                      Run init workspace
                    </Button>
                  </>
                )}
                {item.key === "vertex_ai" && (
                  <>
                    <input className={fieldCls} placeholder="Google Cloud project ID" value={projectId} onChange={(e) => setProjectId(e.target.value)} />
                    <input className={fieldCls} placeholder="Location (default us-central1)" value={location} onChange={(e) => setLocation(e.target.value)} />
                    <p className="text-[11px] text-gray-400">
                      Persists project/location only. Run <code>gcloud auth application-default login</code> in the Terminal for credentials.
                    </p>
                    <Button size="sm" disabled={!projectId.trim()} onClick={() => setStreamUrl(api.setupVertexStreamUrl({ project_id: projectId.trim(), location: location.trim() }))}>
                      Run init vertex-ai
                    </Button>
                  </>
                )}
                {item.key === "neo4j" && (
                  <>
                    <input className={fieldCls} placeholder="Neo4j URI" value={neoUri} onChange={(e) => setNeoUri(e.target.value)} />
                    <input className={fieldCls} placeholder="Username" value={neoUser} onChange={(e) => setNeoUser(e.target.value)} />
                    <input className={fieldCls} type="password" placeholder="Password" value={neoPwd} onChange={(e) => setNeoPwd(e.target.value)} />
                    <Button size="sm" disabled={!neoPwd.trim()} onClick={() => setStreamUrl(api.setupNeo4jStreamUrl({ uri: neoUri.trim(), username: neoUser.trim(), password: neoPwd }))}>
                      Run kg init (neo4j)
                    </Button>
                  </>
                )}
                {INTEGRATION_KEYS.includes(item.key as IntegrationKind) && (
                  <>
                    <input
                      className={fieldCls}
                      placeholder={`${item.label} server URL (e.g. https://${item.key}.company.com)`}
                      value={intg[item.key]?.url ?? ""}
                      onChange={(e) => setIntgField(item.key as IntegrationKind, "url", e.target.value)}
                    />
                    <input
                      className={fieldCls}
                      type="password"
                      placeholder="Personal access token"
                      value={intg[item.key]?.token ?? ""}
                      onChange={(e) => setIntgField(item.key as IntegrationKind, "token", e.target.value)}
                    />
                    <p className="text-[11px] text-gray-400">
                      Saved to <code>~/.dva/.env</code> (chmod 600) — loaded automatically, no shell export needed.
                    </p>
                    <Button
                      size="sm"
                      disabled={!intg[item.key]?.url?.trim() || !intg[item.key]?.token?.trim()}
                      onClick={() =>
                        setStreamUrl(
                          api.setupIntegrationStreamUrl(
                            item.key as IntegrationKind,
                            intg[item.key].url.trim(),
                            intg[item.key].token.trim()
                          )
                        )
                      }
                    >
                      Run init {item.key}
                    </Button>
                  </>
                )}
              </div>
            </ItemRow>
          ))}

          <StreamConsole url={streamUrl} title="dva init output" onDone={onDone} />
        </div>
      </div>
    </div>
  );
}
