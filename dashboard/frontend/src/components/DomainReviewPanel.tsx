import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  EyeOff,
  Loader2,
  RefreshCw,
  ShieldAlert,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StreamConsole } from "@/components/StreamConsole";
import { api, type ReviewEntry, type ReviewProposal } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Review and finalize the instructions extracted from the onboarding corpus.
 *
 * The proposal file in the meta-repo is the source of truth; this screen is an
 * editor over it, which is why a team can equally review it as a pull request.
 *
 * A held entry can never be accepted here. Its text was never written — only the
 * kinds of identifier found in it — so there is nothing to approve, and the only
 * honest action is to open the source. The API refuses it too; this just makes
 * the refusal legible instead of surprising.
 */

const STATUS_STYLES: Record<string, string> = {
  unreviewed:
    "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
  accepted: "bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300",
  rejected: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
  stale: "bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300",
};

function EntryRow({
  entry,
  busy,
  onVerdict,
}: {
  entry: ReviewEntry;
  busy: boolean;
  onVerdict: (accept: boolean) => void;
}) {
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2.5 space-y-1.5",
        entry.held
          ? "border-amber-300 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20"
          : "border-gray-200 dark:border-gray-800"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="secondary" className="text-[10px]">
              {entry.kind}
            </Badge>
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-[10px] font-medium",
                STATUS_STYLES[entry.status] ?? STATUS_STYLES.rejected
              )}
            >
              {entry.status}
            </span>
            {entry.source_absent && (
              <span className="flex items-center gap-1 text-[10px] text-amber-700 dark:text-amber-400">
                <AlertTriangle className="h-3 w-3" /> no longer at its source
              </span>
            )}
          </div>

          {entry.held ? (
            <p className="flex items-start gap-1.5 text-sm text-amber-800 dark:text-amber-300">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                Held — {entry.reason}. The text was never stored; open the source
                to decide.
              </span>
            </p>
          ) : (
            <p className="text-sm text-gray-900 dark:text-gray-100">{entry.text}</p>
          )}

          {entry.proposed_text && (
            <p className="rounded border-l-2 border-purple-400 bg-purple-50/60 py-1 pl-2 text-sm text-purple-800 dark:bg-purple-950/20 dark:text-purple-300">
              Source changed → {entry.proposed_text}
            </p>
          )}

          <p className="font-mono text-[10px] text-gray-500 dark:text-gray-400">
            {entry.citation}
          </p>
        </div>

        <div className="flex shrink-0 gap-1">
          {entry.held ? (
            <span
              className="flex items-center gap-1 px-2 text-[10px] text-gray-500 dark:text-gray-400"
              title="Held entries carry no text, so there is nothing to approve."
            >
              <EyeOff className="h-3.5 w-3.5" /> review at source
            </span>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                disabled={busy || entry.status === "accepted"}
                onClick={() => onVerdict(true)}
              >
                <Check className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || entry.status === "rejected"}
                onClick={() => onVerdict(false)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function DomainReviewPanel({
  slug,
  onFinalized,
}: {
  slug: string;
  onFinalized?: () => void;
}) {
  const [proposal, setProposal] = useState<ReviewProposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSettled, setShowSettled] = useState(false);
  const [stream, setStream] = useState<{ url: string; label: string } | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setProposal(await api.getReviewProposal(slug));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const verdict = async (id: string, accept: boolean) => {
    setBusy(true);
    try {
      await api.recordVerdicts(slug, accept ? { accept: [id] } : { reject: [id] });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const acceptAllPending = async () => {
    const ids = (proposal?.entries ?? [])
      .filter((e) => e.pending && !e.held)
      .map((e) => e.id);
    if (!ids.length) return;
    setBusy(true);
    try {
      await api.recordVerdicts(slug, { accept: ids });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const entries = proposal?.entries ?? [];
  const shown = showSettled ? entries : entries.filter((e) => e.pending);
  const pending = entries.filter((e) => e.pending).length;
  const held = entries.filter((e) => e.held).length;
  const accepted = entries.filter((e) => e.status === "accepted").length;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="font-medium">Extract onboarding intent</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Reads tracked onboarding pages and each repo's CONTRIBUTING, docs and
              ADRs. Bodies are consumed in memory and discarded — only instructions,
              each citing its source, are proposed.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={!!stream}
            onClick={() =>
              setStream({
                url: `/api/domains/${slug}/onboarding/extract/stream`,
                label: "extract",
              })
            }
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Run extract
          </Button>
        </div>

        {stream && (
          <StreamConsole
            url={stream.url}
            onDone={() => {
              setStream(null);
              void refresh();
              if (stream.label === "finalize") onFinalized?.();
            }}
          />
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{pending} pending</Badge>
        <Badge variant="secondary">{accepted} accepted</Badge>
        {held > 0 && (
          <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
            {held} held
          </Badge>
        )}
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="ghost" onClick={() => setShowSettled((v) => !v)}>
            {showSettled ? "Show pending only" : "Show all"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy || !pending}
            onClick={acceptAllPending}
          >
            Accept all pending
          </Button>
          <Button
            size="sm"
            disabled={!!stream || !accepted}
            onClick={() =>
              setStream({
                url: `/api/domains/${slug}/onboarding/finalize/stream`,
                label: "finalize",
              })
            }
          >
            Finalize {accepted > 0 ? `(${accepted})` : ""}
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading proposal…
        </div>
      ) : !proposal?.exists ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No proposal yet — run extract to read the onboarding corpus.
        </p>
      ) : !shown.length ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Nothing pending. {accepted} instruction{accepted === 1 ? "" : "s"} ready to
          finalize.
        </p>
      ) : (
        <div className="space-y-2">
          {shown.map((entry) => (
            <EntryRow
              key={entry.id}
              entry={entry}
              busy={busy}
              onVerdict={(accept) => void verdict(entry.id, accept)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
