import { useState } from "react";
import { ListTodo, Info, Bot, Code2, BrainCircuit } from "lucide-react";

/**
 * Tasks board — visual mockup for the Jira-synced delegation surface (P1).
 *
 * Uses static sample data (incl. CWOW-271902 Heparin) so the management view
 * can be visualized before the `anchor` Jira MCP sync + `tasks_cache` land.
 */

interface SampleTask {
  key: string;
  title: string;
  domain: string;
  complexity: "Low" | "Medium" | "High";
  notes: string;
  status: "Open" | "In Progress" | "Blocked" | "Done";
  assignee?: string;
}

const SAMPLE_TASKS: SampleTask[] = [
  {
    key: "CWOW-271902",
    title: "Heparin Protocol Enhancement: Protocol Order",
    domain: "Apollo/Orders",
    complexity: "Medium",
    notes: "Warning message when Heparin orders unlink from TX on discontinue. Last updated Jun 9.",
    status: "Open",
  },
  {
    key: "CWOW-268440",
    title: "Eligibility Check: surface payer denial reason",
    domain: "cwow-patient",
    complexity: "High",
    notes: "Show denial reason inline on the eligibility panel.",
    status: "In Progress",
    assignee: "A. Patel",
  },
  {
    key: "CWOW-270115",
    title: "Care Plan: nightly recalculation job hardening",
    domain: "cwow-facility",
    complexity: "Low",
    notes: "Add retry + alert when the recalculation job fails.",
    status: "Blocked",
    assignee: "Local User",
  },
];

const COMPLEXITY_COLORS: Record<string, string> = {
  Low: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  Medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  High: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

const STATUS_COLORS: Record<string, string> = {
  Open: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  "In Progress": "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  Blocked: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  Done: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

export function Tasks() {
  const [assigning, setAssigning] = useState<SampleTask | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
          <ListTodo className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">Tasks</h1>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              Phase 1
            </span>
          </div>
          <p className="text-sm text-gray-500">
            Jira-synced work items, delegated to teammates and bound to a domain KG.
          </p>
        </div>
      </div>

      <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-blue-50 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 text-sm">
        <Info className="h-4 w-4 shrink-0 mt-0.5" />
        <span>
          <strong>Demo data.</strong> P1 wires this board to Jira via the{" "}
          <code>anchor</code> MCP (cached in <code>tasks_cache</code>). Assignment + KG-binding
          (P2) will write to the shared <code>assignments</code> store.
        </span>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-800 text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="px-4 py-3 font-medium">Key</th>
              <th className="px-4 py-3 font-medium">Feature</th>
              <th className="px-4 py-3 font-medium">Domain</th>
              <th className="px-4 py-3 font-medium">Complexity</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Assignee</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {SAMPLE_TASKS.map((t) => (
              <tr key={t.key} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-4 py-3 font-mono text-xs text-blue-600 dark:text-blue-400 whitespace-nowrap">
                  {t.key}
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium">{t.title}</div>
                  <div className="text-xs text-gray-400 mt-0.5 max-w-md">{t.notes}</div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-xs">
                    {t.domain}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${COMPLEXITY_COLORS[t.complexity]}`}>
                    {t.complexity}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${STATUS_COLORS[t.status]}`}>
                    {t.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                  {t.assignee ?? "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => setAssigning(t)}
                    className="px-3 py-1.5 text-xs rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                  >
                    Assign
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {assigning && <AssignModal task={assigning} onClose={() => setAssigning(null)} />}
    </div>
  );
}

function AssignModal({ task, onClose }: { task: SampleTask; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold">Assign {task.key}</h3>
          <p className="text-xs text-gray-400 mt-0.5">{task.title}</p>
        </div>
        <div className="p-5 space-y-4 text-sm">
          <Field label="Assignee">
            <select className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent">
              <option>Local User</option>
              <option>A. Patel</option>
              <option>J. Nguyen</option>
            </select>
          </Field>
          <Field label="Execution tool">
            <div className="grid grid-cols-2 gap-2">
              <ToolChip icon={Bot} label="Devin session" />
              <ToolChip icon={Code2} label="Local coding tool" />
            </div>
          </Field>
          <Field label="Knowledge (auto-resolved from domain)">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800 text-xs">
              <BrainCircuit className="h-4 w-4 text-blue-500" />
              <span>
                KG bundle for <strong>{task.domain}</strong> will seed the session
                (knowledge_ids resolved at P2).
              </span>
            </div>
          </Field>
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300 text-xs">
            <Info className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            Preview only — assignment persistence ships in P2.
          </div>
        </div>
        <div className="px-5 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Close
          </button>
          <button
            disabled
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white opacity-50 cursor-not-allowed"
          >
            Assign (P2)
          </button>
        </div>
      </div>
    </div>
  );
}

function ToolChip({
  icon: Icon,
  label,
}: {
  icon: typeof Bot;
  label: string;
}) {
  return (
    <button className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-400 text-left">
      <Icon className="h-4 w-4 text-blue-500" />
      <span className="text-xs">{label}</span>
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-gray-500 mb-1">{label}</span>
      {children}
    </label>
  );
}
