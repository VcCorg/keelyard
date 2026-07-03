import { Database } from "lucide-react";
import { ResourceCatalog } from "@/components/ResourceCatalog";
import { useCatalog } from "@/hooks/useCatalog";

export function Databases() {
  const { items, loading, error } = useCatalog("/api/build/databases");
  return (
    <ResourceCatalog
      title="Databases"
      subtitle="Structured data connectors the platform supports for agent queries."
      icon={Database}
      accent="rose"
      items={items}
      loading={loading}
      error={error}
      emptyHint="No database connectors found in the skills registry."
    />
  );
}
