import { useCallback, useEffect, useState } from "react";

/** A single build ingredient, normalized across component types. */
export interface CatalogItem {
  id: string;
  name: string;
  description?: string;
  category?: string | null;
  tags?: string[];
  type?: string | null;
  available?: boolean;
  detail?: string | null;
}

/** Fetch a build-component catalog endpoint ({ items, total, source }). */
export function useCatalog(endpoint: string) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async (): Promise<CatalogItem[]> => {
    const res = await fetch(endpoint);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).items ?? [];
  }, [endpoint]);

  // Initial load — state only updates after the await, never synchronously.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const it = await fetchItems();
        if (!cancelled) {
          setItems(it);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message);
          setItems([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchItems]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await fetchItems());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [fetchItems]);

  return { items, loading, error, reload };
}
