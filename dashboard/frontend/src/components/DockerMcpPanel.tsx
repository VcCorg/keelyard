import { useCallback } from "react";
import { Container, RefreshCw, CheckCircle2, XCircle, CircleDashed, AlertTriangle } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type DockerMcpStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Docker MCP stack status — the bundled MCP servers (Jira, Confluence,
 * Bitbucket, KG, …) require Docker. This surfaces, at a glance, whether Docker
 * is up and which MCP containers are running, so a user understands why an
 * MCP-dependent feature (e.g. Work Items) is unavailable.
 */

function ServiceDot({ status, running }: { status: string; running: boolean }) {
  if (running) return <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />;
  if (status === "absent") return <CircleDashed className="h-4 w-4 text-gray-300 dark:text-gray-600 shrink-0" />;
  return <XCircle className="h-4 w-4 text-amber-500 shrink-0" />;
}

export function DockerMcpPanel() {
  const fetcher = useCallback(() => api.getDockerMcpStatus(), []);
  const { data, loading, refresh } = usePolling<DockerMcpStatus>(fetcher, 15000);

  const running = data?.services.filter((s) => s.running).length ?? 0;
  const total = data?.services.length ?? 0;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Container className="h-5 w-5 text-blue-500" />
          <h2 className="text-base font-semibold">Docker MCP stack</h2>
          {data && (
            <span
              className={cn(
                "text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide",
                data.docker_available
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                  : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
              )}
            >
              {data.docker_available ? "docker up" : "docker down"}
            </span>
          )}
          {data?.docker_available && total > 0 && (
            <span className="text-xs text-gray-400">{running}/{total} running</span>
          )}
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} /> Re-check
        </button>
      </div>

      {loading && !data && <p className="mt-3 text-sm text-gray-400">Checking Docker…</p>}

      {data && !data.docker_available && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3 text-sm text-amber-800 dark:text-amber-300">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            <span className="font-medium">{data.docker_message || "Docker is not available."}</span>{" "}
            The bundled MCP servers (Jira, Confluence, Bitbucket, KG) run as Docker containers and
            can't start without it. Start Docker and bring up the stack, or{" "}
            <span className="font-medium">register a remote MCP server</span> below to point at a
            shared stack instead.
          </div>
        </div>
      )}

      {data && data.docker_available && !data.compose_found && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3 text-sm text-blue-800 dark:text-blue-300">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            Docker is running, but no bundled <code className="font-mono">docker-compose.yml</code> was
            found. Showing the expected MCP services and any matching containers by name.
          </div>
        </div>
      )}

      {data && data.services.length > 0 && (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {data.services.map((s) => (
            <div
              key={s.name}
              className="flex items-center gap-2.5 rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2"
            >
              <ServiceDot status={s.status} running={s.running} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{s.name}</span>
                  {s.port && <span className="text-[11px] text-gray-400 font-mono">:{s.port}</span>}
                </div>
                {s.description && <p className="text-[11px] text-gray-400 truncate">{s.description}</p>}
              </div>
              <span
                className={cn(
                  "text-[11px] font-medium whitespace-nowrap",
                  s.running ? "text-emerald-600 dark:text-emerald-400"
                    : s.status === "absent" ? "text-gray-400"
                    : "text-amber-600 dark:text-amber-400"
                )}
              >
                {s.running ? "running" : s.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
