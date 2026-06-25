import { Bot } from "lucide-react";
import { PlaceholderPage } from "@/components/PlaceholderPage";

export function Sessions() {
  return (
    <PlaceholderPage
      icon={Bot}
      title="Sessions (Fleet)"
      subtitle="All Devin sessions across the team, grouped by task and assignee."
      phase="Phase 3"
      planned={[
        "Graduates the local-only Devin view into a team fleet view backed by the shared store.",
        "Sessions grouped by task / assignee with rolled-up status badges.",
        "Each session shows its seeded KG bundle so everyone works from the same context.",
        "Drill into any session for live status and output (reuses the Devin detail panel).",
      ]}
    />
  );
}
