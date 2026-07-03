import { Cpu } from "lucide-react";
import { ResourceCatalog } from "@/components/ResourceCatalog";
import { useCatalog } from "@/hooks/useCatalog";

export function Models() {
  const { items, loading, error } = useCatalog("/api/build/models");
  return (
    <ResourceCatalog
      title="Models"
      subtitle="LLM models available to agents (Vertex AI / Gemini). The configured default is flagged."
      icon={Cpu}
      accent="fuchsia"
      items={items}
      loading={loading}
      error={error}
    />
  );
}
