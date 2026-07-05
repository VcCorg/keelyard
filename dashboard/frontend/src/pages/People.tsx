import { useEffect, useMemo, useState } from "react";
import { Users, Lock, Loader2, UserPlus, Trash2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUser } from "@/context/UserContext";
import { api, type RoleAssignments } from "@/lib/api";

// Mirrors agentic_cli.auth ROLE_PERMISSIONS — shown so admins see what a role grants.
const ROLE_GRANTS: Record<string, string> = {
  viewer: "read-only",
  developer: "build context · create sessions",
  maintainer: "+ project & delete knowledge",
  admin: "full access (admin:*)",
};

const ROLE_CHIP =
  "text-[11px] px-2 py-0.5 rounded-full border capitalize transition-colors";

export function People() {
  const { can, user } = useUser();
  const isAdmin = can("admin:*");
  const [data, setData] = useState<RoleAssignments | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [newEmail, setNewEmail] = useState("");
  const [newRoles, setNewRoles] = useState<string[]>(["developer"]);

  useEffect(() => {
    let alive = true;
    api
      .getRoleAssignments()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError((e as Error)?.message || "Failed to load"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const validRoles = data?.valid_roles ?? ["viewer", "developer", "maintainer", "admin"];
  const me = (user.email || "").toLowerCase();

  const apply = async (subject: string, roles: string[]) => {
    setBusy(subject);
    setError(null);
    try {
      const next = await api.setRoleAssignment({ subject, roles });
      setData(next);
    } catch (e) {
      setError((e as Error)?.message || "Update failed");
    } finally {
      setBusy(null);
    }
  };

  const toggleRole = (subject: string, current: string[], role: string) => {
    const next = current.includes(role) ? current.filter((r) => r !== role) : [...current, role];
    apply(subject, next);
  };

  const addUser = async () => {
    const email = newEmail.trim().toLowerCase();
    if (!email) return;
    await apply(email, newRoles);
    setNewEmail("");
    setNewRoles(["developer"]);
  };

  const assignments = useMemo(() => data?.assignments ?? [], [data]);

  if (!isAdmin) {
    return (
      <div className="max-w-3xl mx-auto p-6">
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50/60 dark:bg-amber-900/10 p-4 text-sm text-amber-800 dark:text-amber-300">
          <Lock className="h-4 w-4" /> People &amp; role assignment is admin-only. Ask an admin to
          grant you the <code className="font-mono">admin</code> role.
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 p-1">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <Users className="h-7 w-7 text-blue-500" /> People &amp; Roles
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Assign roles to users. Assigned roles drive permissions (RBAC) and navigation, and
          override roles derived from the SSO proxy.
        </p>
      </div>

      {error && (
        <div className="text-sm px-3 py-2 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Role legend */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="h-4 w-4 text-blue-500" />
          <h2 className="text-sm font-semibold">Roles</h2>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {validRoles.map((r) => (
            <div key={r} className="flex items-center gap-2 text-xs">
              <span className="capitalize font-medium w-24 text-gray-700 dark:text-gray-300">{r}</span>
              <span className="text-gray-500">{ROLE_GRANTS[r] ?? ""}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Add user */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <div className="flex items-center gap-2 mb-3">
          <UserPlus className="h-4 w-4 text-blue-500" />
          <h2 className="text-sm font-semibold">Assign a user</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="user@company.com"
            className="flex-1 min-w-[220px] rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-2 text-sm"
          />
          <div className="flex items-center gap-1">
            {validRoles.map((r) => {
              const on = newRoles.includes(r);
              return (
                <button
                  key={r}
                  type="button"
                  onClick={() => setNewRoles((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]))}
                  className={cn(
                    ROLE_CHIP,
                    on
                      ? "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-900/40"
                      : "bg-transparent text-gray-400 border-gray-200 dark:border-gray-700"
                  )}
                >
                  {r}
                </button>
              );
            })}
          </div>
          <Button size="sm" onClick={addUser} disabled={!newEmail.trim() || newRoles.length === 0 || busy !== null}>
            {busy && busy === newEmail.trim().toLowerCase() ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <UserPlus className="h-4 w-4 mr-1.5" />}
            Assign
          </Button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Users without an explicit assignment inherit roles from the SSO proxy (or the dev default).
        </p>
      </section>

      {/* Assignments */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Assignments</h2>
          {loading && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}
        </div>
        {assignments.length === 0 && !loading && (
          <p className="text-sm text-gray-400">No explicit assignments yet.</p>
        )}
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {assignments.map((a) => (
            <div key={a.subject} className="flex items-center gap-3 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                  {a.subject}
                  {a.subject === me && <span className="ml-2 text-[10px] text-blue-500">you</span>}
                </p>
              </div>
              <div className="flex items-center gap-1">
                {validRoles.map((r) => {
                  const on = a.roles.includes(r);
                  const lockSelfAdmin = a.subject === me && r === "admin";
                  return (
                    <button
                      key={r}
                      type="button"
                      disabled={busy === a.subject || lockSelfAdmin}
                      onClick={() => toggleRole(a.subject, a.roles, r)}
                      title={lockSelfAdmin ? "You can't remove your own admin role" : `Toggle ${r}`}
                      className={cn(
                        ROLE_CHIP,
                        on
                          ? "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-900/40"
                          : "bg-transparent text-gray-400 border-gray-200 dark:border-gray-700",
                        lockSelfAdmin && "opacity-70 cursor-default"
                      )}
                    >
                      {r}
                    </button>
                  );
                })}
                <button
                  type="button"
                  onClick={() => apply(a.subject, [])}
                  disabled={busy === a.subject || a.subject === me}
                  title={a.subject === me ? "You can't revoke your own assignment" : "Revoke assignment"}
                  className="ml-1 p-1 rounded text-gray-400 hover:text-red-500 disabled:opacity-30"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
