import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpFromLine,
  FileDiff,
  Layers,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamConsole } from "@/components/StreamConsole";
import {
  api,
  type TemplateOverlayInfo,
  type TemplateStatus,
} from "@/lib/api";

/**
 * Template & Upstream — the two-way flow between a domain meta-repo and the
 * shared template.
 *
 * A generated meta-repo drifts in both directions: the template gains
 * improvements the domain never received, and the domain makes improvements no
 * other domain ever sees. This panel makes both visible and actionable:
 *
 *   template ahead  → Pull down  (`domain template upgrade`)
 *   domain ahead    → Promote up (`domain template promote`)
 *   both ahead      → conflict, needs a human
 *
 * Every write previews first and streams the real CLI, so what happens here is
 * exactly what happens in a terminal.
 */

/** status → (chip classes, plain-English meaning). Mirrors the CLI legend. */
const STATUS_META: Record<string, { cls: string; meaning: string }> = {
  "both-modified": {
    cls: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
    meaning: "edited here AND updated in the template — reconcile by hand",
  },
  "no-baseline": {
    cls: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
    meaning: "differs from the template, generated before versioning existed",
  },
  "template-updated": {
    cls: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300",
    meaning: "the template moved ahead — safe to pull down",
  },
  "locally-modified": {
    cls: "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300",
    meaning: "improved here — candidate to promote upstream",
  },
  "local-only": {
    cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    meaning: "added here — candidate to promote upstream",
  },
  deleted: {
    cls: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
    meaning: "the template generates this but it's missing locally",
  },
  "template-removed": {
    cls: "bg-gray-200 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
    meaning: "the template no longer generates this file",
  },
  unchanged: {
    cls: "bg-gray-200 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
    meaning: "matches the current template",
  },
};

const PROMOTABLE = new Set(["locally-modified", "local-only"]);

export function TemplatePanel({
  domain,
  onChanged,
}: {
  domain: string;
  /** Called after a write completes, so the caller can refresh its drift chip. */
  onChanged?: () => void;
}) {
  const [status, setStatus] = useState<TemplateStatus | null>(null);
  const [overlay, setOverlay] = useState<TemplateOverlayInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const [selected, setSelected] = useState<string[]>([]);
  const [push, setPush] = useState(false);
  const [allowUnreviewed, setAllowUnreviewed] = useState(false);
  const [prune, setPrune] = useState(false);
  const [force, setForce] = useState(false);

  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [streamTitle, setStreamTitle] = useState("template");

  const load = useCallback(() => {
    if (!domain) return;
    setLoading(true);
    setError(null);
    Promise.all([api.getTemplateStatus(domain), api.getTemplateOverlay()])
      .then(([s, o]) => {
        setStatus(s);
        setOverlay(o);
        // Drop selections that no longer apply after a refresh.
        setSelected((cur) =>
          cur.filter((p) => s.files.some((f) => f.path === p && PROMOTABLE.has(f.status)))
        );
      })
      .catch((e) => {
        setStatus(null);
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => setLoading(false));
  }, [domain]);

  useEffect(() => {
    setStatus(null);
    setSelected([]);
    setStreamUrl(null);
    load();
  }, [domain, load]);

  const run = (url: string, title: string) => {
    setStreamTitle(title);
    setStreamUrl(url);
  };

  const upgrade = (apply: boolean) =>
    run(
      api.templateUpgradeStreamUrl(domain, { apply, prune, force }),
      apply ? "template upgrade (applying)" : "template upgrade (preview)"
    );

  const promote = (apply: boolean) =>
    run(
      api.templatePromoteStreamUrl(domain, selected, { apply, push, allowUnreviewed }),
      apply ? "template promote (applying)" : "template promote (preview)"
    );

  const onDone = () => {
    load();
    onChanged?.();
  };

  const toggle = (path: string) =>
    setSelected((cur) =>
      cur.includes(path) ? cur.filter((p) => p !== path) : [...cur, path]
    );

  const files = status?.files ?? [];
  const visible = showAll ? files : files.filter((f) => f.status !== "unchanged");
  const promotableFiles = files.filter((f) => PROMOTABLE.has(f.status));

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-blue-500" />
          <h2 className="font-semibold text-gray-900 dark:text-white">Template &amp; Upstream</h2>
          {status && (
            <span className="text-[11px] text-gray-400">
              template v{status.template_version}
              {status.recorded_version
                ? status.recorded_version !== status.template_version
                  ? ` · generated from v${status.recorded_version}`
                  : ""
                : " · no baseline recorded"}
            </span>
          )}
        </div>
        <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
          {loading ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-1" />
          )}
          Check
        </Button>
      </div>

      <div className="p-4 space-y-4">
        {error && (
          <div className="rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {loading && !status && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Rendering the template to
            compare against…
          </div>
        )}

        {status && (
          <>
            {/* Direction summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Stat
                icon={ArrowDownToLine}
                n={status.upgradable}
                label="template ahead"
                blurb="Safe to pull down"
                tone={status.upgradable ? "cyan" : "muted"}
              />
              <Stat
                icon={ArrowUpFromLine}
                n={status.promotable}
                label="local improvements"
                blurb="Candidates to promote"
                tone={status.promotable ? "emerald" : "muted"}
              />
              <Stat
                icon={AlertTriangle}
                n={status.conflicted}
                label="need review"
                blurb="Both sides changed"
                tone={status.conflicted ? "red" : "muted"}
              />
            </div>

            {!status.has_baseline && (
              <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md px-3 py-2">
                This meta-repo was generated before template versioning, so there's
                no baseline to tell a template update apart from a local edit.
                Differences are reported as <em>needs review</em> rather than
                guessed at; an upgrade records a baseline going forward.
              </p>
            )}

            {/* Files */}
            {files.length === 0 ? (
              <p className="text-sm text-gray-400">No tracked template files found.</p>
            ) : (
              <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-900/40 text-xs text-gray-500">
                  <span className="flex items-center gap-1.5">
                    <FileDiff className="h-3.5 w-3.5" />
                    {visible.length} of {files.length} file(s)
                  </span>
                  <button className="underline" onClick={() => setShowAll((v) => !v)}>
                    {showAll ? "hide unchanged" : "show all"}
                  </button>
                </div>
                <ul className="divide-y divide-gray-100 dark:divide-gray-900 max-h-72 overflow-y-auto">
                  {visible.map((f) => {
                    const meta = STATUS_META[f.status] ?? {
                      cls: "bg-gray-200 text-gray-600",
                      meaning: "",
                    };
                    const canPromote = PROMOTABLE.has(f.status);
                    return (
                      <li key={f.path} className="flex items-start gap-2 px-3 py-2">
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={selected.includes(f.path)}
                          onChange={() => toggle(f.path)}
                          disabled={!canPromote}
                          title={
                            canPromote
                              ? "Select to promote upstream"
                              : "Only locally-modified or locally-added files can be promoted"
                          }
                        />
                        <div className="min-w-0 flex-1">
                          <code className="text-xs break-all">{f.path}</code>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400">
                            {f.detail || meta.meaning}
                          </p>
                        </div>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap ${meta.cls}`}>
                          {f.status}
                        </span>
                      </li>
                    );
                  })}
                  {visible.length === 0 && (
                    <li className="px-3 py-3 text-sm text-emerald-600 dark:text-emerald-400">
                      In sync with the template.
                    </li>
                  )}
                </ul>
              </div>
            )}

            {/* Pull down */}
            <section className="space-y-2">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1.5">
                <ArrowDownToLine className="h-4 w-4 text-cyan-500" /> Pull template
                updates down
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Fast-forwards only files untouched since generation. Local edits and
                domain-authored files are never overwritten; both-sides conflicts are
                left in place with a <code>.new</code> sidecar to compare.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm" variant="outline" onClick={() => upgrade(false)}>
                  Preview
                </Button>
                <Button
                  size="sm"
                  onClick={() => {
                    if (
                      confirm(
                        `Apply template updates to '${domain}'?\n\nFiles with uncommitted changes are refused unless "force" is checked.`
                      )
                    )
                      upgrade(true);
                  }}
                  disabled={!status.upgradable && !prune}
                >
                  Apply
                </Button>
                <Check label="prune removed files" checked={prune} onChange={setPrune} />
                <Check
                  label="force (overwrite uncommitted)"
                  checked={force}
                  onChange={setForce}
                />
              </div>
            </section>

            {/* Push up */}
            <section className="space-y-2 pt-1 border-t border-gray-100 dark:border-gray-900">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1.5 pt-3">
                <ArrowUpFromLine className="h-4 w-4 text-emerald-500" /> Promote local
                improvements upstream
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Re-tokenizes the selected file(s) — this domain's name, product, owner
                become placeholders — and writes them to the shared template overlay,
                where every other domain picks them up. Content that still looks
                domain-specific (emails, ticket keys, URLs, dates) is refused unless
                you override.
              </p>
              {promotableFiles.length === 0 ? (
                <p className="text-xs text-gray-400">
                  Nothing to promote — this domain has no locally modified or added
                  template files.
                </p>
              ) : (
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-xs text-gray-500">
                    {selected.length} selected
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => promote(false)}
                    disabled={!selected.length}
                  >
                    Preview
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      if (
                        confirm(
                          `Promote ${selected.length} file(s) from '${domain}' into the shared template?\n\nEvery domain will receive this content.`
                        )
                      )
                        promote(true);
                    }}
                    disabled={!selected.length}
                  >
                    Promote
                  </Button>
                  <Check label="push branch" checked={push} onChange={setPush} />
                  <Check
                    label="allow unreviewed"
                    checked={allowUnreviewed}
                    onChange={setAllowUnreviewed}
                  />
                </div>
              )}
              {overlay && (
                <p className="text-[11px] text-gray-400">
                  Overlay provides {overlay.files.length} file(s) ·{" "}
                  <code className="break-all">{overlay.overlay_root}</code>
                </p>
              )}
            </section>
          </>
        )}

        <StreamConsole url={streamUrl} title={streamTitle} onDone={onDone} />
      </div>
    </div>
  );
}

/* ── small local helpers ─────────────────────────────────────────────────── */

const TONES: Record<string, string> = {
  cyan: "border-cyan-300 dark:border-cyan-800 text-cyan-700 dark:text-cyan-300",
  emerald: "border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300",
  red: "border-red-300 dark:border-red-800 text-red-700 dark:text-red-300",
  muted: "border-gray-200 dark:border-gray-800 text-gray-400",
};

function Stat({
  icon: Icon,
  n,
  label,
  blurb,
  tone,
}: {
  icon: typeof Layers;
  n: number;
  label: string;
  blurb: string;
  tone: string;
}) {
  return (
    <div className={`rounded-lg border p-3 ${TONES[tone] ?? TONES.muted}`}>
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" />
        <span className="text-xl font-semibold">{n}</span>
      </div>
      <div className="text-xs font-medium mt-0.5">{label}</div>
      <div className="text-[11px] text-gray-500 dark:text-gray-400">{blurb}</div>
    </div>
  );
}

function Check({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300 select-none">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
