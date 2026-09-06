import { useCallback } from "react";
import {
  Brain,
  Trophy,
  Boxes,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  type LucideIcon,
} from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  type IntegrationsResponse,
  type IntegrationState,
  type IntegrationStatus,
} from "@/lib/api";

const ICONS: Record<string, LucideIcon> = {
  huggingface: Brain,
  kaggle: Trophy,
};

const STATE: Record<IntegrationState, { chip: string; Icon: LucideIcon; word: string }> = {
  ok: {
    chip: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-900/40",
    Icon: CheckCircle2,
    word: "Connected",
  },
  warn: {
    chip: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-900/40",
    Icon: AlertTriangle,
    word: "Partly configured",
  },
  error: {
    chip: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-900/40",
    Icon: XCircle,
    word: "Failing",
  },
  unknown: {
    chip: "bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700",
    Icon: HelpCircle,
    word: "Not connected",
  },
};

/** What each hub is actually good for once connected, named by the command that
 *  uses it. A status panel that only says "connected" leaves the reader with no
 *  idea what changed, which is how an integration gets configured and then
 *  never used. */
const USES: Record<string, string[]> = {
  huggingface: [
    "keel context fetch hf://model/<org>/<name> — model and dataset cards, pinned to a commit",
    "keel eval dataset pull <repo> --input … --expected … — hub datasets as eval sets",
    "keel eval playground --model hf:<org>/<name> — replay against a hub model, tokens counted",
  ],
  kaggle: [
    "keel context fetch kaggle://competition/<slug> — the metric, deadline and category",
    "keel domain add-source <domain> kaggle://competition/<slug> — track one as a domain source",
  ],
};

function HubCard({ item }: { item: IntegrationStatus }) {
  const Icon = ICONS[item.key] ?? Boxes;
  const state = STATE[item.status];
  const uses = USES[item.key] ?? [];

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-3.5">
      <div className="flex items-start gap-3">
        <Icon className="h-5 w-5 mt-0.5 text-gray-500 dark:text-gray-400 shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {item.label}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${state.chip}`}
            >
              <state.Icon className="h-3 w-3" />
              {state.word}
            </span>
          </div>

          {item.detail && (
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400 break-words">
              {item.detail}
            </p>
          )}
          {item.hint && (
            <p className="mt-1 text-[11px] text-gray-400 break-words">{item.hint}</p>
          )}
          {item.docs_command && (
            <code className="mt-2 inline-block rounded bg-gray-100 dark:bg-gray-900 px-1.5 py-0.5 font-mono text-[11px] text-gray-700 dark:text-gray-300 break-all">
              {item.docs_command}
            </code>
          )}

          {uses.length > 0 && (
            <ul className="mt-2.5 space-y-1">
              {uses.map((use) => (
                <li
                  key={use}
                  className="text-[11px] text-gray-500 dark:text-gray-400 break-words"
                >
                  <span className="text-gray-300 dark:text-gray-600 mr-1.5">→</span>
                  {use}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Data and model hubs — Hugging Face and Kaggle.
 *
 * Read-only on purpose. Keel detects where a hub credential lives and never
 * copies the value, so there is no key field here to fill in: the credential
 * belongs to the hub's own CLI, and a second copy would be a second thing to
 * rotate and a second thing to leak. What this panel does is tell you whether
 * the credential and the client are present, which half is missing, and the one
 * command that fixes it.
 */
export function HubIntegrationsPanel() {
  const fetcher = useCallback(() => api.getIntegrations(), []);
  const { data, loading, error, refresh } = usePolling<IntegrationsResponse>(fetcher, 30000);

  const hubs = (data?.integrations ?? []).filter((i) => i.group === "optional");

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Credentials stay with each hub&rsquo;s own CLI — Keel records where they live, never
          what they are. Connect a hub there, then check here.
        </p>
        <button
          onClick={refresh}
          title="Refresh hub status"
          aria-label="Refresh hub status"
          className="p-1.5 rounded-md text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-500">Could not read hub status: {error}</p>
      )}

      {!error && !loading && hubs.length === 0 && (
        <p className="text-xs text-gray-400">
          This backend reports no optional integrations.
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {hubs.map((item) => (
          <HubCard key={item.key} item={item} />
        ))}
      </div>
    </div>
  );
}
