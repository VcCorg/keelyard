import { ClipboardList } from "lucide-react";
import { PlaceholderPage } from "@/components/PlaceholderPage";

export function Assignments() {
  return (
    <PlaceholderPage
      icon={ClipboardList}
      title="Assignments"
      subtitle="Tasks delegated to you and your team, with live execution status."
      phase="Phase 2-3"
      planned={[
        "Per-user list of assigned tasks linking task → user → KG bundle → execution ref.",
        "Execution status rollup: which Devin session or local repo, last heartbeat, running/blocked/done.",
        "Local-tool status via `keel task status <key> --state ...` syncing to the shared assignments store.",
        "Optional git/PR link captured per assignment.",
      ]}
    />
  );
}
