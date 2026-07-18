import { useEffect, useState } from "react";
import { ShieldCheck, ShieldAlert, FlaskConical } from "lucide-react";
import { api, type BuildGovernanceInfo } from "@/lib/api";

/**
 * Build-governance guidance for domain-first forms (Repository, Devin session).
 * Fetches the effective level for the chosen domain (or the domain-less admin
 * default) and renders a compact badge + contextual explanation, so users see
 * what the backend seams will do BEFORE they submit.
 */

export function useBuildGovernance(domain: string) {
  const [info, setInfo] = useState<BuildGovernanceInfo | null>(null);
  useEffect(() => {
    let alive = true;
    api
      .getBuildGovernance(domain || undefined)
      .then((g) => alive && setInfo(g))
      .catch(() => alive && setInfo(null));
    return () => {
      alive = false;
    };
  }, [domain]);
  return info;
}

export function GovernanceBadge({ info }: { info: BuildGovernanceInfo | null }) {
  if (!info) return null;
  const styles: Record<string, string> = {
    off: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
    warn: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    enforce: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  };
  const Icon = info.level === "off" ? FlaskConical : info.level === "warn" ? ShieldAlert : ShieldCheck;
  const label = info.level === "off" ? "sandbox" : info.level;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium ${styles[info.level]}`}
      title={`Build governance: ${info.level} (${info.source})`}
    >
      <Icon className="h-3 w-3" /> governance: {label}
    </span>
  );
}

export function GovernanceBanner({ info, domain }: { info: BuildGovernanceInfo | null; domain: string }) {
  if (!info) return null;
  const domainless = !domain;
  if (info.level === "off") {
    return (
      <p className="text-[11px] text-gray-400">
        {domainless
          ? "Domain-less work runs without governance checks (admin default: off)."
          : "This domain is a sandbox (build_governance: off) — work runs freely and is still audited."}
      </p>
    );
  }
  if (info.level === "warn") {
    return (
      <p className="text-[11px] text-amber-600 dark:text-amber-400">
        {domainless
          ? "No domain selected — this will run but be tagged UNGOVERNED in the audit trail. Pick a domain to run governed."
          : info.meta_repo_found
            ? null
            : `Domain '${domain}' has no meta-repo yet — runs will be tagged ungoverned until the governance phase creates one.`}
      </p>
    );
  }
  // enforce
  return (
    <p className="text-[11px] text-red-600 dark:text-red-400">
      {domainless
        ? "Governance is ENFORCED for domain-less work — this will be refused. Select a governed domain (or a sandbox domain)."
        : info.meta_repo_found
          ? null
          : `Domain '${domain}' has no meta-repo — enforced governance will refuse this. Run the governance phase first (keel domain scaffold).`}
    </p>
  );
}

/** True when submitting with the current selection would be refused. */
export function governanceBlocks(info: BuildGovernanceInfo | null, domain: string): boolean {
  if (!info || info.level !== "enforce") return false;
  if (!domain) return true;
  return !info.meta_repo_found;
}
