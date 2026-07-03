import { Search } from "lucide-react";
import { ResourceCatalog } from "@/components/ResourceCatalog";
import { useCatalog } from "@/hooks/useCatalog";

export function Retrievers() {
  const { items, loading, error } = useCatalog("/api/build/retrievers");
  return (
    <ResourceCatalog
      title="Retrievers"
      subtitle="Retriever backends for building semantic and full-text indexes. Named indexes are created during onboarding / RAG."
      icon={Search}
      accent="cyan"
      items={items}
      loading={loading}
      error={error}
    />
  );
}
