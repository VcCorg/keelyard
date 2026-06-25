import { BrainCircuit } from "lucide-react";
import { PlaceholderPage } from "@/components/PlaceholderPage";

export function SharedKG() {
  return (
    <PlaceholderPage
      icon={BrainCircuit}
      title="Shared KG"
      subtitle="A team catalog of curated, version-pinned domain knowledge bundles."
      phase="Phase 4"
      planned={[
        "Promote per-user OKF domain bundles into a shared, versioned catalog.",
        "Assignees pull the same curated KG so every session shares identical context.",
        "Version pinning so a task's KG is reproducible across Devin and local tools.",
        "Backed by existing OKF bundles + kg_service, registered in the shared store.",
      ]}
    />
  );
}
