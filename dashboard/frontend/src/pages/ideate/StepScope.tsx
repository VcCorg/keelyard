import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight } from "lucide-react";
import type { DomainInfo, ProductInfo } from "@/lib/api";

const selectCls =
  "w-full max-w-sm text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none disabled:opacity-50";

function OnboardCta({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-900/20 p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
        <AlertTriangle className="h-4 w-4" />
        {children}
      </div>
      <Link
        to="/onboarding"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        Go to Domain Onboarding <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

export function StepScope({
  products,
  domains,
  productName,
  domainSlug,
  onProduct,
  onDomain,
  jiraConfigured,
}: {
  products: ProductInfo[];
  domains: DomainInfo[];
  productName: string;
  domainSlug: string;
  onProduct: (p: string) => void;
  onDomain: (slug: string) => void;
  jiraConfigured: boolean;
}) {
  // Nothing onboarded yet → guide the user to onboarding first.
  if (!products.length && !domains.length) {
    return (
      <div className="space-y-3">
        <div>
          <label className="text-sm font-medium">Scope</label>
          <p className="text-xs text-gray-500">
            Pick the product and domain your stories belong to. The Jira project is
            taken from the domain's onboarding configuration.
          </p>
        </div>
        <OnboardCta>No products or domains onboarded yet — onboard a domain first.</OnboardCta>
      </div>
    );
  }

  const productDomains = domains.filter((d) => d.product === productName);
  const selectedDomain = domains.find((d) => d.name === domainSlug) || null;
  const jiraProject = (selectedDomain?.jira_project || "").trim();

  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">Scope</label>
        <p className="text-xs text-gray-500">
          Pick the product and domain your stories belong to. The target Jira project
          is configured on the domain during onboarding.
        </p>
      </div>

      {/* Product */}
      <div className="space-y-1">
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">Product</label>
        <select value={productName} onChange={(e) => onProduct(e.target.value)} className={selectCls}>
          <option value="" disabled>
            Select a product…
          </option>
          {products.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
              {p.domain_count ? ` (${p.domain_count} domain${p.domain_count === 1 ? "" : "s"})` : ""}
            </option>
          ))}
        </select>
      </div>

      {/* Domain */}
      <div className="space-y-1">
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">Domain</label>
        {!productName ? (
          <p className="text-xs text-gray-500">Select a product to see its domains.</p>
        ) : productDomains.length ? (
          <select value={domainSlug} onChange={(e) => onDomain(e.target.value)} className={selectCls}>
            <option value="" disabled>
              Select a domain…
            </option>
            {productDomains.map((d) => (
              <option key={d.name} value={d.name}>
                {d.domain || d.name}
                {d.jira_project ? ` · ${d.jira_project}` : " · no Jira project"}
              </option>
            ))}
          </select>
        ) : (
          <OnboardCta>No domains onboarded under {productName} — onboard one first.</OnboardCta>
        )}
      </div>

      {/* Derived Jira project */}
      {selectedDomain && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3 space-y-1">
          <div className="text-xs font-medium text-gray-600 dark:text-gray-300">Target Jira project</div>
          {jiraProject ? (
            <>
              <div className="text-sm font-semibold">{jiraProject}</div>
              <p className="text-xs text-gray-500">
                From domain <span className="font-medium">{selectedDomain.domain || selectedDomain.name}</span>.
                Approved stories are created here; it determines available fields/epics.
              </p>
              {!jiraConfigured && (
                <p className="text-xs text-amber-600 flex items-center gap-1">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Jira integration isn't configured — you can draft, but pushing will fail until it's set up.
                </p>
              )}
            </>
          ) : (
            <OnboardCta>
              Domain <span className="font-medium">{selectedDomain.domain || selectedDomain.name}</span> has no
              Jira project. Set it in onboarding before pushing.
            </OnboardCta>
          )}
        </div>
      )}
    </div>
  );
}
