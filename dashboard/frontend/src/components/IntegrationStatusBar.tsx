import { useCallback, type ComponentType } from "react";
import {
  Server,
  Cloud,
  Bot,
  Boxes,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
} from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type IntegrationsResponse, type IntegrationState, type IntegrationStatus } from "@/lib/api";

const ICONS: Record<string, ComponentType<{ className?: string }>> = {
  backend: Server,
  gcloud: Cloud,
  devin: Bot,
  mcp: Boxes,
};

const STATE_STYLES: Record<IntegrationState, { dot: string; text: string; Icon: ComponentType<{ className?: string }> }> = {
  ok: {
    dot: "bg-emerald-500",
    text: "text-emerald-600 dark:text-emerald-400",
    Icon: CheckCircle2,
  },
  warn: {
    dot: "bg-amber-500",
    text: "text-amber-600 dark:text-amber-400",
    Icon: AlertTriangle,
  },
  error: {
    dot: "bg-red-500",
    text: "text-red-600 dark:text-red-400",
    Icon: XCircle,
  },
  unknown: {
    dot: "bg-gray-400",
    text: "text-gray-500 dark:text-gray-400",
    Icon: HelpCircle,
  },
};

function StatusChip({ item }: { item: IntegrationStatus }) {
  const Icon = ICONS[item.key] ?? Server;
  const style = STATE_STYLES[item.status];
  return (
    <div className="relative group">
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 cursor-default">
        <Icon className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.label}</span>
        <span className={`h-2 w-2 rounded-full ${style.dot}`} />
      </div>

      {/* Tooltip */}
      <div className="absolute right-0 top-full mt-1.5 z-50 hidden group-hover:block w-60">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg p-3 text-left">
          <div className="flex items-center gap-1.5">
            <style.Icon className={`h-3.5 w-3.5 ${style.text}`} />
            <span className="text-sm font-semibold">{item.label}</span>
            <span className={`ml-auto text-[11px] font-medium uppercase ${style.text}`}>
              {item.status}
            </span>
          </div>
          {item.detail && (
            <p className="mt-1.5 text-xs text-gray-600 dark:text-gray-400 break-words">{item.detail}</p>
          )}
          {item.hint && (
            <p className="mt-1.5 text-[11px] text-gray-400 break-words">{item.hint}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export function IntegrationStatusBar() {
  const fetcher = useCallback(() => api.getIntegrations(), []);
  // Poll every 10s so backend/MCP/devin/gcloud status reflect current state
  // without waiting up to half a minute for it to catch up.
  const { data, loading, error, refresh } = usePolling<IntegrationsResponse>(fetcher, 10000);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {error && (
        <span className="flex items-center gap-1.5 text-xs text-red-500">
          <XCircle className="h-3.5 w-3.5" />
          Backend unreachable
        </span>
      )}
      {!error && data?.integrations.map((item) => <StatusChip key={item.key} item={item} />)}
      <button
        onClick={refresh}
        title="Refresh integration status"
        aria-label="Refresh integration status"
        className="p-1.5 rounded-md text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
      </button>
    </div>
  );
}
