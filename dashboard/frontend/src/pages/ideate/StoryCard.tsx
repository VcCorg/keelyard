import { Trash2, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EditableStory, JiraMeta, PushResult } from "./types";
import { PRIORITIES, DEFAULT_ISSUE_TYPES } from "./types";

const PRIORITY_CHIP: Record<string, string> = {
  High: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
  Medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300",
  Low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

export function StoryCard({
  story,
  meta,
  onChange,
  onRemove,
  onPushOne,
  onDuplicate,
  pushed,
}: {
  story: EditableStory;
  meta: JiraMeta | null;
  onChange: (patch: Partial<EditableStory>) => void;
  onRemove: () => void;
  onPushOne?: () => void;
  onDuplicate?: () => void;
  pushed?: PushResult;
}) {
  const issueTypes = meta?.issue_types?.length ? meta.issue_types : DEFAULT_ISSUE_TYPES;
  const show = meta?.fields;
  const setAc = (i: number, val: string) => {
    const ac = [...story.acceptance_criteria];
    ac[i] = val;
    onChange({ acceptance_criteria: ac });
  };
  const addAc = () => onChange({ acceptance_criteria: [...story.acceptance_criteria, ""] });
  const removeAc = (i: number) =>
    onChange({ acceptance_criteria: story.acceptance_criteria.filter((_, j) => j !== i) });

  return (
    <div
      className={cn(
        "rounded-xl border p-3 bg-white dark:bg-gray-900 transition-opacity",
        story.keep
          ? "border-gray-200 dark:border-gray-800"
          : "border-gray-200 dark:border-gray-800 opacity-50"
      )}
    >
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={story.keep}
          onChange={(e) => onChange({ keep: e.target.checked })}
          className="h-4 w-4 accent-blue-600"
          title="Keep this story"
        />
        <select
          value={story.issue_type}
          onChange={(e) => onChange({ issue_type: e.target.value })}
          className="text-[10px] font-semibold rounded px-1.5 py-0.5 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 outline-none"
        >
          {issueTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <input
          value={story.title}
          onChange={(e) => onChange({ title: e.target.value })}
          className="flex-1 text-sm font-medium bg-transparent outline-none border-b border-transparent focus:border-gray-300 dark:focus:border-gray-700"
        />
        {(!show || show.priority) && (
          <select
            value={story.priority}
            onChange={(e) => onChange({ priority: e.target.value })}
            className={cn(
              "text-[10px] font-semibold rounded px-1.5 py-0.5 outline-none",
              PRIORITY_CHIP[story.priority] ?? PRIORITY_CHIP.Medium
            )}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={onRemove}
          className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
          title="Remove"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {(!show || show.epic_link) && (
          <select
            value={story.epic_key ?? ""}
            onChange={(e) => onChange({ epic_key: e.target.value || null })}
            className="text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none"
            title="Epic"
          >
            <option value="">No epic</option>
            {(meta?.epics ?? []).map((ep) => (
              <option key={ep.key} value={ep.key}>
                {ep.key} · {ep.summary}
              </option>
            ))}
          </select>
        )}
        {(!show || show.story_points) && (
          <input
            type="number"
            value={story.story_points ?? ""}
            placeholder="pts"
            onChange={(e) =>
              onChange({ story_points: e.target.value === "" ? null : Number(e.target.value) })
            }
            className="w-14 text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none"
          />
        )}
        {(!show || show.assignee) && (
          <input
            value={story.assignee ?? ""}
            placeholder="assignee"
            onChange={(e) => onChange({ assignee: e.target.value || null })}
            className="w-28 text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none"
          />
        )}
      </div>

      <textarea
        value={story.description}
        onChange={(e) => onChange({ description: e.target.value })}
        rows={2}
        className="mt-2 w-full text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800 px-2 py-1.5 outline-none"
      />

      <div className="mt-2">
        <div className="text-[11px] font-semibold text-gray-500 mb-1">Acceptance criteria</div>
        <div className="space-y-1">
          {story.acceptance_criteria.map((ac, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <input
                value={ac}
                onChange={(e) => setAc(i, e.target.value)}
                className="flex-1 text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none"
              />
              <button
                onClick={() => removeAc(i)}
                className="text-gray-400 hover:text-red-600"
                title="Remove criterion"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          <button
            onClick={addAc}
            className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700"
          >
            <Plus className="h-3 w-3" /> add criterion
          </button>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2 border-t border-gray-100 dark:border-gray-800 pt-2">
        {onDuplicate && (
          <button
            onClick={onDuplicate}
            className="text-[11px] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Duplicate
          </button>
        )}
        {onPushOne && !pushed?.ok && (
          <button
            onClick={onPushOne}
            className="text-[11px] font-medium text-emerald-700 hover:text-emerald-800"
          >
            Push this
          </button>
        )}
        {pushed?.ok && pushed.url && (
          <a
            href={pushed.url}
            target="_blank"
            rel="noopener"
            className="text-[11px] font-medium text-blue-600 hover:underline"
          >
            Created {pushed.key} ↗
          </a>
        )}
        {pushed && !pushed.ok && <span className="text-[11px] text-red-600">{pushed.error}</span>}
      </div>
    </div>
  );
}
