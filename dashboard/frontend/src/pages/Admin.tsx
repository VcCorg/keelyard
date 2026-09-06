import { useEffect, useMemo, useState, type ComponentType, type ReactNode } from "react";
import { ShieldCheck, Save, RotateCcw, Loader2, Palette, ListChecks, Lock, AlertTriangle, Trash2, Scale, Cpu, ChevronDown, ChevronRight, Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUser, type UserRole } from "@/context/UserContext";
import { useAdminSettings } from "@/context/AdminSettingsContext";
import { buildNavCatalog, UI_ROLES, type NavCatalogNode } from "@/lib/nav";
import { api, type ResetScope } from "@/lib/api";
import { HubIntegrationsPanel } from "@/components/HubIntegrationsPanel";

const RESET_CONFIRM = "RESET";

const KIND_BADGE: Record<NavCatalogNode["kind"], string> = {
  group: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  subgroup: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  item: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

const sameRoles = (a: UserRole[], b: UserRole[]) =>
  a.length === b.length && UI_ROLES.every((r) => a.includes(r) === b.includes(r));

// Code-assist engines grouped into vendor families with friendly labels. An
// engine with no meta renders standalone under its own name. Hidden engines
// stay registered underneath (used elsewhere) but don't clutter the admin UI:
// `local` is the internal portable-bundle mechanism; `devin-cli` is deferred
// from the tools list to keep the picker to just Devin and VS Code for now.
const ENGINE_META: Record<string, { family: string; label: string; primary?: boolean }> = {
  "vscode-copilot": { family: "VS Code + Copilot", label: "VS Code + Copilot", primary: true },
  "devin": { family: "Devin", label: "Devin", primary: true },
};
const HIDDEN_ENGINES = new Set(["local", "devin-cli"]);
const familyOf = (name: string) => ENGINE_META[name]?.family ?? name;
const labelOf = (name: string) => ENGINE_META[name]?.label ?? name;
// The "primary" engine of a family is the one whose toggle controls the family
// (e.g. Devin/Cloud). Sub-options can't be enabled without their primary.
const isPrimary = (name: string) => !ENGINE_META[name] || !!ENGINE_META[name].primary;
const primaryOf = (family: string) =>
  Object.entries(ENGINE_META).find(([, m]) => m.family === family && m.primary)?.[0];

/**
 * Collapsible section wrapper used for every Admin card. The header row shows
 * an icon + title + hint on the left and an actions slot on the right; the
 * body is only rendered when open. Navigation visibility opts into
 * `defaultOpen={false}` so it stops dominating the page.
 */
function AdminSection({
  icon: Icon,
  title,
  hint,
  actions,
  defaultOpen = true,
  tone = "default",
  children,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  hint?: string;
  actions?: ReactNode;
  defaultOpen?: boolean;
  tone?: "default" | "danger";
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const shellCls =
    tone === "danger"
      ? "rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50/40 dark:bg-red-900/10"
      : "rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900";
  const titleCls =
    tone === "danger" ? "text-lg font-semibold text-red-700 dark:text-red-300" : "text-lg font-semibold";
  return (
    <section className={shellCls}>
      <div className="flex items-center gap-2 px-5 py-4">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex items-center gap-2 flex-1 min-w-0 text-left hover:opacity-80"
        >
          {open ? (
            <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
          )}
          <Icon className={cn("h-5 w-5", tone === "danger" ? "text-red-500" : "text-blue-500")} />
          <h2 className={titleCls}>{title}</h2>
          {hint && (
            <span className={cn("text-xs truncate", tone === "danger" ? "text-red-500/80" : "text-gray-400")}>
              {hint}
            </span>
          )}
        </button>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {open && <div className="px-5 pb-5 space-y-4">{children}</div>}
    </section>
  );
}

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
      await updateSettings({ branding: { app_title: title.trim() || "Keel", app_name: name.trim() || "Agentic Product Development Platform" } });
    } finally {
      setSavingBrand(false);
    }
  };

  // ── Skill governance (enforcement toggle) ───────────────────────────────
  const enforcing = settings.skill_enforcement === "enforce";
  const [savingEnf, setSavingEnf] = useState(false);
  const setEnforcement = async (mode: "off" | "enforce") => {
    if (mode === settings.skill_enforcement) return;
    setSavingEnf(true);
    try {
      await updateSettings({ skill_enforcement: mode });
    } finally {
      setSavingEnf(false);
    }
  };

  // ── Build governance default (domain-less work) ─────────────────────────
  const buildGov = settings.build_governance_default;
  const [savingGov, setSavingGov] = useState(false);
  const setBuildGov = async (level: "off" | "warn" | "enforce") => {
    if (level === buildGov) return;
    setSavingGov(true);
    try {
      await updateSettings({ build_governance_default: level });
    } finally {
      setSavingGov(false);
    }
  };

  // ── Code assist tools (vendor-neutral engines) ──────────────────────────
  const [engines, setEngines] = useState<
    { name: string; kind: string; available: boolean; description: string; detail: string }[]
  >([]);
  const [savingCA, setSavingCA] = useState(false);
  const ca = settings.code_assist;

  useEffect(() => {
    fetch("/api/execution/engines").then((r) => r.json()).then(setEngines).catch(() => setEngines([]));
  }, []);

  // ── Onboarding-IDE tools (where `keel code onboard` places SKILL.md) ────
  // Separate concept from Code assist tools (execution engines). Same
  // enable/default UX so it feels familiar; two rails avoid conflating
  // "who runs the code" with "which IDE reads the skills on disk".
  const [ideTools, setIdeTools] = useState<
    { name: string; label: string; description: string; deprecated: boolean; has_bridge: boolean }[]
  >([]);
  const [savingIde, setSavingIde] = useState(false);
  const oi = settings.onboarding_ide;

  useEffect(() => {
    fetch("/api/execution/onboarding-ide-tools")
      .then((r) => r.json())
      .then(setIdeTools)
      .catch(() => setIdeTools([]));
  }, []);

  const saveOnboardingIde = async (enabled: string[], def: string) => {
    setSavingIde(true);
    try {
      await updateSettings({ onboarding_ide: { enabled, default: def } });
    } finally {
      setSavingIde(false);
    }
  };
  const toggleIde = (name: string) => {
    const on = oi.enabled.includes(name);
    const enabled = on ? oi.enabled.filter((e) => e !== name) : [...oi.enabled, name];
    if (enabled.length === 0) return; // Never leave the store with zero options
    const def = enabled.includes(oi.default) ? oi.default : enabled[0];
    saveOnboardingIde(enabled, def);
  };
  const setDefaultIde = (name: string) => {
    if (name === oi.default) return;
    const enabled = oi.enabled.includes(name) ? oi.enabled : [...oi.enabled, name];
    saveOnboardingIde(enabled, name);
  };

  const saveCodeAssist = async (enabled: string[], def: string) => {
    setSavingCA(true);
    try {
      await updateSettings({ code_assist: { enabled, default: def } });
    } finally {
      setSavingCA(false);
    }
  };
  const toggleEngine = (name: string) => {
    const on = ca.enabled.includes(name);
    let enabled = on ? ca.enabled.filter((e) => e !== name) : [...ca.enabled, name];
    // Disabling a family's primary drops its sub-options (a sub can't outlive
    // its primary — e.g. turning Devin off removes Devin CLI too).
    if (on && isPrimary(name)) {
      const fam = familyOf(name);
      enabled = enabled.filter((e) => familyOf(e) !== fam || e === name);
    }
    if (enabled.length === 0) return; // keep at least one enabled
    const def = enabled.includes(ca.default) ? ca.default : enabled[0];
    saveCodeAssist(enabled, def);
  };
  const setDefaultEngine = (name: string) => {
    if (name === ca.default) return;
    const enabled = ca.enabled.includes(name) ? ca.enabled : [...ca.enabled, name];
    saveCodeAssist(enabled, name);
  };

  const renderEngineRow = (
    e: { name: string; kind: string; available: boolean; description: string; detail: string },
    opts: { isChild?: boolean; primaryOn?: boolean } = {}
  ) => {
    const on = ca.enabled.includes(e.name);
    const isDefault = ca.default === e.name;
    const locked = !!opts.isChild && !opts.primaryOn;   // sub-option needs its family primary enabled
    return (
      <div
        key={e.name}
        className={cn(
          "flex items-center gap-3 rounded-lg border p-3",
          opts.isChild && "ml-6",
          locked && "opacity-60",
          isDefault ? "border-blue-300 dark:border-blue-800 bg-blue-50/40 dark:bg-blue-900/10"
            : "border-gray-200 dark:border-gray-800"
        )}
      >
        <input
          type="checkbox"
          checked={on}
          disabled={!canEdit || savingCA || locked}
          onChange={() => toggleEngine(e.name)}
          className="h-4 w-4 rounded border-gray-300"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{labelOf(e.name)}</span>
            <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">{e.kind}</span>
            {!e.available && (
              <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">unavailable</span>
            )}
          </div>
          <p className="text-[11px] text-gray-400 truncate">
            {locked ? "Enable this vendor above to use this option" : (e.detail || e.description)}
          </p>
        </div>
        <button
          onClick={() => setDefaultEngine(e.name)}
          disabled={!canEdit || savingCA || !on}
          className={cn(
            "text-xs px-2.5 py-1 rounded-md border transition-colors disabled:opacity-40",
            isDefault
              ? "border-blue-300 bg-blue-100 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
              : "border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800"
          )}
        >
          {isDefault ? "default" : "make default"}
        </button>
      </div>
    );
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

  // ── Platform reset (danger zone) ────────────────────────────────────────
  const [resetScopes, setResetScopes] = useState<ResetScope[]>([]);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [confirmText, setConfirmText] = useState("");
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!canEdit) return;
    let alive = true;
    api
      .getResetPreview()
      .then((p) => alive && setResetScopes(p.scopes))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [canEdit]);

  const toggleScope = (s: string) =>
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });

  const doReset = async () => {
    const scopes = [...chosen];
    if (!scopes.length || confirmText !== RESET_CONFIRM) return;
    setResetting(true);
    setResetMsg(null);
    try {
      const res = await api.resetPlatform({ scopes, confirm: confirmText });
      setResetMsg(`Reset: ${res.reset.join(", ")}`);
      setChosen(new Set());
      setConfirmText("");
      const p = await api.getResetPreview();
      setResetScopes(p.scopes);
    } catch (e) {
      setResetMsg((e as Error)?.message || "Reset failed");
    } finally {
      setResetting(false);
    }
  };

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
      <AdminSection icon={Palette} title="Branding" hint="shown top-left of the app">
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
            <p className="text-sm font-bold leading-tight">{title || "Keel"}</p>
            <p className="text-[11px] text-gray-500">{name || "Agentic Product Development Platform"}</p>
          </div>
        </div>
      </AdminSection>

      {/* ── Skill governance ─────────────────────────────────────────────── */}
      <AdminSection icon={Scale} title="Skill governance" hint="persona-scoped skill enforcement">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              When <strong>enforced</strong>, onboarding installs only the skills a user's
              persona is permitted by each domain's <code className="font-mono text-xs">skills.yaml</code>
              {" "}policy — denied and out-of-policy skills are skipped. When <strong>off</strong>,
              policy is advisory only (reported by <code className="font-mono text-xs">make validate</code>),
              and nothing is withheld.
            </p>
            <div
              className={cn(
                "mt-3 inline-flex items-center gap-2 rounded-md px-2.5 py-1 text-xs font-medium",
                enforcing
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                  : "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
              )}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              {enforcing ? "Hard enforcement is ON" : "Advisory mode (enforcement off)"}
            </div>
          </div>
          {/* Toggle */}
          <button
            type="button"
            role="switch"
            aria-checked={enforcing}
            disabled={!canEdit || savingEnf}
            onClick={() => setEnforcement(enforcing ? "off" : "enforce")}
            className={cn(
              "relative mt-1 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50",
              enforcing ? "bg-emerald-500" : "bg-gray-300 dark:bg-gray-700"
            )}
          >
            <span
              className={cn(
                "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                enforcing ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>
        {savingEnf && (
          <p className="text-xs text-gray-400 flex items-center gap-1.5">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
          </p>
        )}

        {/* Build governance default (domain-less work) */}
        <div className="pt-4 border-t border-gray-100 dark:border-gray-800 space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">Build governance — domain-less default</h3>
            {savingGov && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Applies to onboards and engine sessions with <strong>no domain</strong>. Work inside a
            domain follows that domain's own <code className="font-mono text-xs">governance.yaml</code>
            {" "}(<code className="font-mono text-xs">build_governance: off | warn | enforce</code>) —
            a domain set to <code className="font-mono text-xs">off</code> acts as a sandbox.
          </p>
          <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            {(["off", "warn", "enforce"] as const).map((level) => (
              <button
                key={level}
                onClick={() => setBuildGov(level)}
                disabled={!canEdit || savingGov}
                className={cn(
                  "px-3.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50",
                  buildGov === level
                    ? level === "enforce"
                      ? "bg-emerald-500 text-white"
                      : level === "warn"
                        ? "bg-amber-500 text-white"
                        : "bg-gray-400 text-white"
                    : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                )}
              >
                {level}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-gray-400">
            off: ungoverned work runs silently · warn: runs but is tagged in the audit trail ·
            enforce: refused at the seams (onboard &amp; session create)
          </p>
        </div>
      </AdminSection>

      {/* ── Code assist tools (vendor-neutral build engines) ─────────────── */}
      <AdminSection
        icon={Cpu}
        title="Code assist tools"
        hint="which engines Build may use, and the org default"
        actions={savingCA ? <Loader2 className="h-4 w-4 animate-spin text-blue-400" /> : null}
      >
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Enable the code-assist tools your team may pick, and click <strong>make default</strong>
          {" "}on the one to use org-wide. Build Sessions and "Open in IDE" open the{" "}
          <strong>default</strong> tool — enabling a tool alone doesn't switch it. Governance +
          audit apply to every engine identically.
        </p>
        <div className="space-y-2">
          {(() => {
            // Group visible engines by family, primary first inside each family.
            const visible = engines.filter((e) => !HIDDEN_ENGINES.has(e.name));
            if (visible.length === 0) {
              return <p className="text-sm text-gray-400">No execution engines registered.</p>;
            }
            const families: string[] = [];
            for (const e of visible) {
              const fam = familyOf(e.name);
              if (!families.includes(fam)) families.push(fam);
            }
            return families.map((fam) => {
              const members = visible.filter((e) => familyOf(e.name) === fam)
                .sort((a, b) => Number(isPrimary(b.name)) - Number(isPrimary(a.name)));
              const primaryName = primaryOf(fam);
              const primaryOn = primaryName ? ca.enabled.includes(primaryName) : true;
              return (
                <div key={fam} className="space-y-2">
                  {members.map((m, i) =>
                    renderEngineRow(m, { isChild: i > 0, primaryOn }))}
                </div>
              );
            });
          })()}
        </div>
        <p className="text-[11px] text-gray-400">
          Devin runs a remote cloud session; VS Code + Copilot hands off a governed context bundle
          to your local editor. At least one tool stays enabled.
        </p>
      </AdminSection>

      {/* ── Onboarding-IDE tools (SKILL.md placement layer) ───────────────── */}
      <AdminSection
        icon={Cpu}
        title="Onboarding IDE tools"
        hint="where `keel code onboard` places SKILL.md so the IDE reads it"
        actions={savingIde ? <Loader2 className="h-4 w-4 animate-spin text-blue-400" /> : null}
      >
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Enable the IDE targets your team may pick, and make one the org default. Distinct from
          the <strong>Code assist tools</strong> above (which pick the <em>execution engine</em>).
          When <code className="font-mono text-xs">--code-assist-tool auto</code> is passed to
          onboard, the default here wins if no live IDE is detected on the machine.
        </p>
        <div className="space-y-2">
          {ideTools.length === 0 ? (
            <p className="text-sm text-gray-400">No onboarding IDE tools registered.</p>
          ) : (
            ideTools.map((t) => {
              const on = oi.enabled.includes(t.name);
              const isDefault = oi.default === t.name;
              return (
                <div
                  key={t.name}
                  className={cn(
                    "flex items-center gap-3 rounded-lg border p-3",
                    isDefault
                      ? "border-blue-300 dark:border-blue-800 bg-blue-50/40 dark:bg-blue-900/10"
                      : "border-gray-200 dark:border-gray-800"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={on}
                    disabled={!canEdit || savingIde}
                    onChange={() => toggleIde(t.name)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{t.label}</span>
                      {t.deprecated && (
                        <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                          deprecated
                        </span>
                      )}
                      {t.has_bridge && (
                        <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                          bridge
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-gray-400 truncate">{t.description}</p>
                  </div>
                  <button
                    onClick={() => setDefaultIde(t.name)}
                    disabled={!canEdit || savingIde || !on}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-md border transition-colors disabled:opacity-40",
                      isDefault
                        ? "border-blue-300 bg-blue-100 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                        : "border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800"
                    )}
                  >
                    {isDefault ? "default" : "make default"}
                  </button>
                </div>
              );
            })
          )}
        </div>
        <p className="text-[11px] text-gray-400">
          Deprecated tools (like Windsurf post-Devin migration) can still be enabled if a team
          needs them, but a fresh <code className="font-mono text-xs">auto</code> detection never
          picks one when a non-deprecated IDE is present. At least one tool stays enabled.
        </p>
      </AdminSection>

      {/* ── Nav visibility ───────────────────────────────────────────────── */}
      <AdminSection
        icon={ListChecks}
        title="Navigation visibility"
        hint="which roles see each entry"
        defaultOpen={false}
        actions={
          <>
            <Button size="sm" variant="outline" onClick={() => setDraft({})} disabled={!navDirty}>
              Discard
            </Button>
            <Button size="sm" onClick={saveNav} disabled={!canEdit || !navDirty || savingNav}>
              {savingNav ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
              Save visibility
            </Button>
          </>
        }
      >
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
      </AdminSection>

      {/* ── Data and model hubs ──────────────────────────────────────────── */}
      <AdminSection
        icon={Boxes}
        title="Data & model hubs"
        hint="Hugging Face · Kaggle"
        defaultOpen={false}
      >
        <HubIntegrationsPanel />
      </AdminSection>

      {/* ── Danger zone: platform reset ──────────────────────────────────── */}
      {canEdit && (
        <AdminSection
          icon={AlertTriangle}
          title="Reset platform data"
          hint="destructive · cannot be undone"
          defaultOpen={false}
          tone="danger"
        >
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Return the platform to a clean state. Select what to clear, then type{" "}
            <code className="font-mono">{RESET_CONFIRM}</code> to confirm.
          </p>

          <div className="space-y-1.5">
            {resetScopes.map((s) => (
              <label
                key={s.scope}
                className="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 cursor-pointer"
              >
                <input type="checkbox" checked={chosen.has(s.scope)} onChange={() => toggleScope(s.scope)} />
                <span className="text-sm text-gray-800 dark:text-gray-200 flex-1">{s.label}</span>
                <span className="text-xs text-gray-400">{s.items} item{s.items === 1 ? "" : "s"}</span>
              </label>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={`Type ${RESET_CONFIRM} to confirm`}
              className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-2 text-sm w-56"
            />
            <Button
              size="sm"
              className="bg-red-600 hover:bg-red-700 text-white"
              disabled={resetting || chosen.size === 0 || confirmText !== RESET_CONFIRM}
              onClick={doReset}
            >
              {resetting ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Trash2 className="h-4 w-4 mr-1.5" />}
              Reset selected data
            </Button>
            {resetMsg && <span className="text-xs text-gray-500">{resetMsg}</span>}
          </div>
        </AdminSection>
      )}
    </div>
  );
}
