import { Share2 } from "lucide-react";
import { PlaceholderPage } from "@/components/PlaceholderPage";

export function SharedAgents() {
  return (
    <PlaceholderPage
      icon={Share2}
      title="Shared Agents"
      subtitle="A team catalog of agents that anyone can discover and pull."
      phase="Phase 4"
      planned={[
        "Publish a local agent project to the shared `shared_agents` catalog.",
        "Discover and pull/clone teammates' published agents.",
        "Reuses the existing skills publish → discover → pull mental model.",
        "Owner + published-at metadata tracked in the shared store.",
      ]}
    />
  );
}
