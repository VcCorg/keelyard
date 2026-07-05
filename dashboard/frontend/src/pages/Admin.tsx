import { useMemo, useState } from "react";
import { ShieldCheck, Save, RotateCcw, Loader2, Palette, ListChecks, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUser, type UserRole } from "@/context/UserContext";
import { useAdminSettings } from "@/context/AdminSettingsContext";
import { buildNavCatalog, UI_ROLES, type NavCatalogNode } from "@/lib/nav";

const KIND_BADGE: Record<NavCatalogNode["kind"], string> = {
  group: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  subgroup: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  item: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

const sameRoles = (a: UserRole[], b: UserRole[]) =>
  a.length === b.length && UI_ROLES.every((r) => a.includes(r) === b.includes(r));

export function Admin() {
  const { can } = useUser();
  const canEdit = can("admin:*");
  const { settings, loading, updateSettings } = useAdminSettings();

  const catalog = useMemo(() => buildNavCatalog(), []);

  // ── Branding draft ──────────────────────────────────────────────────────
  const [title, setTitle] = useState(settings.branding.app_title);
  const [name, setName] = useState(settings.branding.app_name);
  const [savingBrand, setSavingBrand] = useState(false);
  const brandDirty = title !== settings.branding.app_title || name !== settings.branding.app_name;

  const saveBranding = async () => {
    setSavingBrand(true);
    try {
      await updateSettings({ branding: { app_title: title.trim() || "Agent Playground", app_name: name.trim() || "Agentic Platform" } });
    } finally {
      setSavingBrand(false);
    }
  };

  // ── Nav visibility draft ────────────────────────────────────────────────
  const effective = (n: NavCatalogNode): UserRole[] => {
    const ov = settings.nav_visibility[n.id];
    return ov && ov.length ? (ov.filter((r) => UI_ROLES.includes(r as UserRole)) as UserRole[]) : n.defaultRoles;
  };
  const [draft, setDraft] = useState<Record<string, UserRole[]>>({});
  const rolesFor = (n: NavCatalogNode): UserRole[] => draft[n.id] ?? effective(n);
  const [savingNav, setSavingNav] = useState(false);

  const toggle = (n: NavCatalogNode, role: UserRole) => {
    if (role === "admin") return; // admin can never be removed
    const cur = rolesFor(n);
    const next = cur.includes(role) ? cur.filter((r) => r !== role) : [...cur, role];
    if (!next.includes("admin")) next.push("admin");
    setDraft((d) => ({ ...d, [n.id]: UI_ROLES.filter((r) => next.includes(r)) }));
  };
  const resetRow = (n: NavCatalogNode) =>
    setDraft((d) => ({ ...d, [n.id]: n.defaultRoles }));

  const navDirty = catalog.some((n) => draft[n.id] && !sameRoles(draft[n.id], effective(n)));

  const saveNav = async () => {
    setSavingNav(true);
    try {
      // Only send nodes whose roles differ from their default → real overrides.
      const overrides: Record<string, string[]> = {};
      for (const n of catalog) {
        const roles = rolesFor(n);
        if (!sameRoles(roles, n.defaultRoles)) overrides[n.id] = roles;
      }
      await updateSettings({ nav_visibility: overrides, replace_nav: true });
      setDraft({});
    } finally {
      setSavingNav(false);
    }
  };

  const grouped = useMemo(() => {
    const m = new Map<string, NavCatalogNode[]>();
    for (const n of catalog) {
      if (!m.has(n.group)) m.set(n.group, []);
      m.get(n.group)!.push(n);
    }
    return [...m.entries()];
  }, [catalog]);

  return (
    <div className="max-w-4xl mx-auto space-y-8 p-1">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <ShieldCheck className="h-7 w-7 text-blue-500" /> Administration
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Control app branding and which roles see which navigation. Changes apply for everyone.
        </p>
      </div>

      {!canEdit && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50/60 dark:bg-amber-900/10 p-3 text-sm text-amber-800 dark:text-amber-300">
          <Lock className="h-4 w-4" /> You can view these settings, but only an admin
          (<code className="font-mono">admin:*</code>) can change them.
        </div>
      )}

      {/* ── Branding ─────────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Palette className="h-5 w-5 text-blue-500" />
          <h2 className="text-lg font-semibold">Branding</h2>
          <span className="text-xs text-gray-400">shown top-left of the app</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-medium text-gray-500">App title (heading)</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={!canEdit}
              className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-2 text-sm disabled:opacity-60"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-500">App name (subtitle)</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!canEdit}
              className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-2 text-sm disabled:opacity-60"
            />
          </label>
        </div>
        <div className="flex items-center gap-3">
          <Button size="sm" onClick={saveBranding} disabled={!canEdit || !brandDirty || savingBrand}>
            {savingBrand ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
            Save branding
          </Button>
          {/* Live preview */}
          <div className="ml-auto rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-1.5">
            <p className="text-sm font-bold leading-tight">{title || "Agent Playground"}</p>
            <p className="text-[11px] text-gray-500">{name || "Agentic Platform"}</p>
          </div>
        </div>
      </section>

      {/* ── Nav visibility ───────────────────────────────────────────────── */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <ListChecks className="h-5 w-5 text-blue-500" />
          <h2 className="text-lg font-semibold">Navigation visibility</h2>
          <span className="text-xs text-gray-400">which roles see each entry</span>
          <div className="ml-auto flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setDraft({})} disabled={!navDirty}>
              Discard
            </Button>
            <Button size="sm" onClick={saveNav} disabled={!canEdit || !navDirty || savingNav}>
              {savingNav ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
              Save visibility
            </Button>
          </div>
        </div>

        {loading && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}

        <div className="space-y-5">
          {grouped.map(([groupLabel, nodes]) => (
            <div key={groupLabel}>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">{groupLabel}</p>
              <div className="rounded-lg border border-gray-200 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800">
                {nodes.map((n) => {
                  const roles = rolesFor(n);
                  const overridden = !sameRoles(roles, n.defaultRoles);
                  return (
                    <div key={n.id} className="flex items-center gap-3 px-3 py-2">
                      <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide", KIND_BADGE[n.kind])}>
                        {n.kind}
                      </span>
                      <span className="text-sm text-gray-800 dark:text-gray-200 flex-1 truncate">{n.label}</span>
                      {overridden && (
                        <span className="text-[10px] text-amber-600 dark:text-amber-400">overridden</span>
                      )}
                      <div className="flex items-center gap-1">
                        {UI_ROLES.map((r) => {
                          const on = roles.includes(r);
                          const locked = r === "admin";
                          return (
                            <button
                              key={r}
                              type="button"
                              disabled={!canEdit || locked}
                              onClick={() => toggle(n, r)}
                              title={locked ? "Admins always have access" : `Toggle ${r}`}
                              className={cn(
                                "text-[11px] px-2 py-0.5 rounded-full border capitalize transition-colors",
                                on
                                  ? "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-900/40"
                                  : "bg-transparent text-gray-400 border-gray-200 dark:border-gray-700",
                                locked && "opacity-70 cursor-default",
                                !canEdit && "cursor-not-allowed"
                              )}
                            >
                              {r}
                            </button>
                          );
                        })}
                        <button
                          type="button"
                          onClick={() => resetRow(n)}
                          disabled={!canEdit || !overridden}
                          title="Reset to default"
                          className="ml-1 p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
