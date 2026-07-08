import { Send, Loader2 } from "lucide-react";
import { ActivityPanel } from "./ActivityPanel";

export function StepPush({
  project,
  keepCount,
  pushing,
  onPushAll,
  refreshKey,
}: {
  project: string;
  keepCount: number;
  pushing: boolean;
  onPushAll: () => void;
  refreshKey: number;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-sm">
          Push <b>{keepCount}</b> kept {keepCount === 1 ? "story" : "stories"} to <b>{project || "—"}</b>.
        </span>
        <button
          onClick={onPushAll}
          disabled={pushing || !keepCount || !project}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {pushing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Push all
        </button>
      </div>
      <ActivityPanel refreshKey={refreshKey} />
    </div>
  );
}
