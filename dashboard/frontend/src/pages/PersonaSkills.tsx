import { useEffect, useState } from "react";
import { Boxes, Loader2 } from "lucide-react";
import { PersonaSkillsPanel } from "@/components/PersonaSkillsPanel";
import { api, type DomainInfo } from "@/lib/api";

/**
 * Standalone Persona Skills page.
 *
 * Accessible to all team members (not just admins). Pick a domain, then:
 *  - review the persona skills generated into its meta-repo, and
 *  - recreate repo-level skills.
 *
 * Admins additionally see product-level catalog management (the panel gates
 * those controls internally by role).
 */
export function PersonaSkills() {
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [slug, setSlug] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    api
      .listDomains()
      .then((d) => {
        if (cancelled) return;
        setDomains(d);
        if (d.length > 0) setSlug(d[0].name);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const active = domains.find((d) => d.name === slug);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <Boxes className="h-5 w-5" /> Persona Skills
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Review generated persona skills and recreate repo-level skills for a domain. Product-level
          changes are available to admins.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 px-3 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading domains…
        </div>
      ) : domains.length === 0 ? (
        <p className="text-sm text-gray-400">
          No domains found. Ask an admin to create one in Domain Onboarding first.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-gray-600 dark:text-gray-300">Domain</label>
            <select
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              {domains.map((d) => (
                <option key={d.name} value={d.name}>
                  {d.product} · {d.domain}
                </option>
              ))}
            </select>
          </div>

          {active && <PersonaSkillsPanel slug={active.name} product={active.product} />}
        </>
      )}
    </div>
  );
}
