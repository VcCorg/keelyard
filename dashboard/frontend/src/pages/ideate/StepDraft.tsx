import { Sparkles, Loader2 } from "lucide-react";

export function StepDraft({
  count,
  onCount,
  onDraft,
  drafting,
  source,
}: {
  count: number;
  onCount: (n: number) => void;
  onDraft: () => void;
  drafting: boolean;
  source: "llm" | "heuristic" | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium">How many stories</label>
        <input
          type="number"
          min={1}
          max={20}
          value={count}
          onChange={(e) => onCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
          className="w-16 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
        />
        <button
          onClick={onDraft}
          disabled={drafting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {drafting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Draft
          stories
        </button>
      </div>
      {source && (
        <p className="text-xs text-gray-500">
          Drafted via{" "}
          {source === "llm" ? "the configured LLM" : "a deterministic heuristic (no LLM configured)"}.
        </p>
      )}
    </div>
  );
}
