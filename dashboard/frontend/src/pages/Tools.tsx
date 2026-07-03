import { Wrench } from "lucide-react";
import { ResourceCatalog } from "@/components/ResourceCatalog";
import { useCatalog } from "@/hooks/useCatalog";

export function Tools() {
  const { items, loading, error } = useCatalog("/api/build/tools");
  return (
    <ResourceCatalog
      title="Tools"
      subtitle="Built-in template tools and reusable registry tools your agents can call."
      icon={Wrench}
      accent="amber"
      items={items}
      loading={loading}
      error={error}
      groupByCategory
    />
  );
}
