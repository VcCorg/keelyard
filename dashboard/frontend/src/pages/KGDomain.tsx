import { useCallback, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2, AlertCircle, ChevronDown, ChevronRight } from "lucide-react";
import * as Tabs from "@radix-ui/react-tabs";
import { usePolling } from "@/hooks/usePolling";
import { api, type KGLinkRow, type KGGapRow } from "@/lib/api";
import { KGGraphPanel } from "@/components/KGGraphPanel";

const REL_COLORS: Record<string, string> = {
  IMPLEMENTS: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
  REFERENCES: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  TESTED_BY: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  CONFIGURES: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
};

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 90 ? "text-emerald-600 dark:text-emerald-400" :
    pct >= 75 ? "text-amber-600 dark:text-amber-400" :
    "text-red-500 dark:text-red-400";
  return (
    <span className={`font-mono text-xs font-semibold ${color}`}>{pct}%</span>
  );
}

interface GraphState {
  nodeId: string;
  nodeName: string;
  nodeType: "code" | "document";
}

export function KGDomain() {
  const { domain } = useParams<{ domain: string }>();
  const [graphPanel, setGraphPanel] = useState<GraphState | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);

  const linksFetcher = useCallback(() => api.getKGDomainLinks(domain!), [domain]);
  const gapsFetcher = useCallback(() => api.getKGDomainGaps(domain!), [domain]);

  const { data: links, loading: linksLoading, error: linksError } = usePolling<KGLinkRow[]>(linksFetcher, 30000);
  const { data: gaps, loading: gapsLoading, error: gapsError } = usePolling<KGGapRow[]>(gapsFetcher, 30000);

  if (!domain) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/kg"
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> KG Context
        </Link>
        <span className="text-gray-300 dark:text-gray-600">/</span>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white font-mono">{domain}</h1>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Code Links", value: links?.length ?? "—" },
          { label: "Coverage Gaps", value: gaps?.length ?? "—" },
          { label: "Domains", value: domain },
          {
            label: "Coverage",
            value: links && gaps
              ? `${Math.round((links.length / Math.max(links.length + (gaps?.length ?? 0), 1)) * 100)}%`
              : "—",
          },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
          >
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-xl font-bold mt-1 truncate">{value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <Tabs.Root defaultValue="links">
        <Tabs.List className="flex gap-1 border-b border-gray-200 dark:border-gray-800 mb-4">
          {[
            { value: "links", label: "Code Links" },
            { value: "gaps", label: `Coverage Gaps${gaps ? ` (${gaps.length})` : ""}` },
          ].map(({ value, label }) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className="px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent -mb-px
                         data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-700
                         dark:data-[state=active]:text-indigo-400 hover:text-gray-900 dark:hover:text-gray-100
                         transition-colors"
            >
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* ── Code Links tab ── */}
        <Tabs.Content value="links">
          {linksLoading && (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
            </div>
          )}
          {linksError && (
            <div className="flex items-center gap-2 text-red-500 text-sm py-4">
              <AlertCircle className="h-4 w-4" /> {linksError}
            </div>
          )}
          {!linksLoading && links && (
            <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-800/50">
                  <tr>
                    {["Code Entity", "Requirement", "Relationship", "Confidence", ""].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {links.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-10 text-center text-gray-400 text-sm">
                        No linked edges yet. Run <code className="font-mono bg-gray-100 dark:bg-gray-800 px-1 rounded">dva kg link --domain {domain}</code> to generate links.
                      </td>
                    </tr>
                  )}
                  {links.map((row) => {
                    const evidenceKey = `${row.code_id}:${row.doc_id}`;
                    const expanded = expandedEvidence === evidenceKey;
                    return (
                      <>
                        <tr
                          key={evidenceKey}
                          className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
                        >
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setGraphPanel({ nodeId: row.code_id, nodeName: row.code_name, nodeType: "code" })}
                              className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline text-left truncate max-w-[160px] block"
                              title={row.code_name}
                            >
                              {row.code_name}
                            </button>
                            <span className="text-xs text-gray-400">{row.code_type}</span>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setGraphPanel({ nodeId: row.doc_id, nodeName: row.doc_name, nodeType: "document" })}
                              className="text-emerald-700 dark:text-emerald-400 hover:underline text-left truncate max-w-[200px] block"
                              title={row.doc_name}
                            >
                              {row.doc_name}
                            </button>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${REL_COLORS[row.relationship] ?? "bg-gray-100 text-gray-600"}`}>
                              {row.relationship}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <ConfidencePill value={row.confidence} />
                          </td>
                          <td className="px-4 py-2">
                            <button
                              onClick={() => setExpandedEvidence(expanded ? null : evidenceKey)}
                              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                              title="Show evidence"
                            >
                              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            </button>
                          </td>
                        </tr>
                        {expanded && (
                          <tr key={`${evidenceKey}-evidence`} className="bg-indigo-50 dark:bg-indigo-900/10">
                            <td colSpan={5} className="px-6 py-3 text-xs text-gray-600 dark:text-gray-300 italic">
                              {row.evidence || "No evidence recorded."}
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Tabs.Content>

        {/* ── Coverage Gaps tab ── */}
        <Tabs.Content value="gaps">
          {gapsLoading && (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
            </div>
          )}
          {gapsError && (
            <div className="flex items-center gap-2 text-red-500 text-sm py-4">
              <AlertCircle className="h-4 w-4" /> {gapsError}
            </div>
          )}
          {!gapsLoading && gaps && (
            <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-800/50">
                  <tr>
                    {["Requirement Document", "Jira ID", "Preview", ""].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {gaps.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-10 text-center text-emerald-600 dark:text-emerald-400 text-sm font-medium">
                        No coverage gaps — all requirements are linked!
                      </td>
                    </tr>
                  )}
                  {gaps.map((row) => (
                    <tr key={row.doc_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
                      <td className="px-4 py-3">
                        <button
                          onClick={() => setGraphPanel({ nodeId: row.doc_id, nodeName: row.doc_name, nodeType: "document" })}
                          className="font-medium text-gray-800 dark:text-gray-200 hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline text-left truncate max-w-[220px] block"
                          title={row.doc_name}
                        >
                          {row.doc_name}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        {row.jira_id ? (
                          <span className="font-mono text-xs bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded">
                            {row.jira_id}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-400 max-w-xs truncate" title={row.content_preview}>
                        {row.content_preview}
                      </td>
                      <td className="px-4 py-2">
                        <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
                          Unlinked
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Tabs.Content>
      </Tabs.Root>

      {/* Drilldown graph panel */}
      {graphPanel && (
        <KGGraphPanel
          nodeId={graphPanel.nodeId}
          nodeName={graphPanel.nodeName}
          nodeType={graphPanel.nodeType}
          domain={domain}
          onClose={() => setGraphPanel(null)}
        />
      )}
    </div>
  );
}
