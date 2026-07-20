import { useEffect, useMemo, useState } from "react";
import { ShieldCheck, UserCircle, Check, X, KeyRound, Loader2 } from "lucide-react";
import { api, type AuthMe, type RbacModel, type PermissionCheck } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Identity & Access — the frontend for `keel auth`: the identity the provider
 * resolves for you (subject, roles, persona, permissions), the RBAC model as a
 * role × permission matrix, personas, and a live permission checker.
 */

export function IdentityAccess() {
  const [me, setMe] = useState<AuthMe | null>(null);
  const [rbac, setRbac] = useState<RbacModel | null>(null);
  const [perm, setPerm] = useState("");
  const [checkResult, setCheckResult] = useState<PermissionCheck | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    api.getMe().then(setMe).catch(() => setMe(null));
    api.getRbacModel().then(setRbac).catch(() => setRbac(null));
  }, []);

  const myPerms = useMemo(() => new Set(me?.permissions ?? []), [me]);
  const isAdmin = myPerms.has("admin:*");

  const runCheck = async (p: string) => {
    if (!p) return;
    setChecking(true);
    setCheckResult(null);
    try {
      setCheckResult(await api.checkPermission(p));
    } catch {
      setCheckResult(null);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
          <ShieldCheck className="h-6 w-6 text-blue-500" /> Identity &amp; Access
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Who you are, what you can do, and the platform's RBAC model. Mirrors{" "}
          <code className="font-mono">keel auth</code>.
        </p>
      </div>

      {/* Current identity */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <div className="flex items-center gap-2 mb-4">
          <UserCircle className="h-5 w-5 text-blue-500" />
          <h2 className="text-base font-semibold">Your identity</h2>
          {me && (
            <span
              className={cn(
                "text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide",
                me.provider === "dev"
                  ? "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
              )}
              title={me.provider === "dev"
                ? "Local dev identity — set KEEL_AUTH_MODE=forward-auth behind SSO"
                : `Enterprise SSO via ${me.provider}`}
            >
              {me.provider === "dev" ? "dev" : "SSO"}
            </span>
          )}
        </div>
        {!me ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            <Field label="Subject" value={me.subject} />
            <Field label="Name" value={me.display_name || "—"} />
            <Field label="Persona" value={me.persona || "—"} />
            <Field label="Mode" value={me.mode} />
            <div className="sm:col-span-2">
              <p className="text-[11px] uppercase tracking-wide text-gray-400 mb-1">Roles</p>
              <div className="flex flex-wrap gap-1.5">
                {me.roles.length ? me.roles.map((r) => (
                  <span key={r} className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{r}</span>
                )) : <span className="text-gray-400 text-xs">none</span>}
              </div>
            </div>
            <div className="sm:col-span-2">
              <p className="text-[11px] uppercase tracking-wide text-gray-400 mb-1">Permissions</p>
              <div className="flex flex-wrap gap-1.5">
                {isAdmin ? (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">admin:* (all)</span>
                ) : me.permissions.length ? me.permissions.map((p) => (
                  <code key={p} className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{p}</code>
                )) : <span className="text-gray-400 text-xs">read-only</span>}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Permission checker */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <div className="flex items-center gap-2 mb-3">
          <KeyRound className="h-5 w-5 text-blue-500" />
          <h2 className="text-base font-semibold">Check a permission</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            list="perm-options"
            value={perm}
            onChange={(e) => setPerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runCheck(perm.trim())}
            placeholder="e.g. knowledge:project"
            className="h-9 w-72 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 text-sm font-mono"
          />
          <datalist id="perm-options">
            {rbac?.permissions.map((p) => <option key={p.permission} value={p.permission} />)}
          </datalist>
          <button
            onClick={() => runCheck(perm.trim())}
            disabled={!perm.trim() || checking}
            className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Check
          </button>
          {checkResult && (
            <span className={cn(
              "inline-flex items-center gap-1.5 text-sm font-medium",
              checkResult.allowed ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
            )}>
              {checkResult.allowed ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
              {checkResult.subject} {checkResult.allowed ? "has" : "lacks"}{" "}
              <code className="font-mono">{checkResult.permission}</code>
            </span>
          )}
        </div>
      </div>

      {/* RBAC matrix */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <h2 className="text-base font-semibold mb-3">Roles &amp; permissions</h2>
        {!rbac ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-left">
                  <th className="px-3 py-2 text-[11px] uppercase tracking-wide text-gray-400 font-medium">Permission</th>
                  {rbac.roles.map((r) => (
                    <th key={r.role} className="px-3 py-2 text-center text-[11px] uppercase tracking-wide text-gray-500 font-medium">{r.role}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800/60">
                {rbac.permissions.map((perm) => (
                  <tr key={perm.permission} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                    <td className="px-3 py-2">
                      <code className="text-[12px] font-mono text-gray-700 dark:text-gray-300">{perm.permission}</code>
                      <p className="text-[11px] text-gray-400">{perm.description}</p>
                    </td>
                    {rbac.roles.map((r) => {
                      const granted = r.permissions.includes(perm.permission) || r.permissions.includes("admin:*");
                      return (
                        <td key={r.role} className="px-3 py-2 text-center">
                          {granted ? (
                            <Check className="h-4 w-4 text-emerald-500 inline" />
                          ) : (
                            <span className="text-gray-200 dark:text-gray-700">·</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[11px] text-gray-400 mt-2">
              Roles are cumulative (each grants everything below it). Viewer is read-only.
            </p>
          </div>
        )}
      </div>

      {/* Personas */}
      {rbac && rbac.personas.length > 0 && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
          <h2 className="text-base font-semibold mb-3">Personas</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {rbac.personas.map((p) => (
              <div
                key={p.persona}
                className={cn(
                  "rounded-lg border p-3",
                  me?.persona === p.persona
                    ? "border-blue-300 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10"
                    : "border-gray-200 dark:border-gray-800"
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold capitalize">{p.persona}</span>
                  {me?.persona === p.persona && (
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 uppercase">you</span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">{p.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-gray-400 mb-0.5">{label}</p>
      <p className="text-gray-800 dark:text-gray-200 font-medium truncate" title={value}>{value}</p>
    </div>
  );
}
