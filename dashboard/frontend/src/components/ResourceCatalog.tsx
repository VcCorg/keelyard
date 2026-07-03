import { useMemo, useState, type ComponentType } from "react";
import { Search, Loader2, AlertCircle, PackageOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CatalogItem } from "@/hooks/useCatalog";

type Accent = "amber" | "cyan" | "rose" | "fuchsia" | "blue" | "emerald" | "slate";

const ACCENT: Record<Accent, string> = {
  amber: "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300",
  cyan: "bg-cyan-50 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-300",
  rose: "bg-rose-50 text-rose-600 dark:bg-rose-900/30 dark:text-rose-300",
  fuchsia: "bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-900/30 dark:text-fuchsia-300",
  blue: "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300",
  emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300",
  slate: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

export function ResourceCatalog({
  title,
  subtitle,
  icon: Icon,
  accent = "blue",
  items,
  loading,
  error,
  groupByCategory = false,
  emptyHint,
}: {
  title: string;
  subtitle: string;
  icon: ComponentType<{ className?: string }>;
  accent?: Accent;
  items: CatalogItem[];
  loading: boolean;
  error?: string | null;
  groupByCategory?: boolean;
  emptyHint?: string;
}) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) =>
      `${i.name} ${i.description ?? ""} ${(i.tags ?? []).join(" ")}`.toLowerCase().includes(q)
    );
  }, [items, search]);

  const groups = useMemo(() => {
    if (!groupByCategory) return null;
    const map = new Map<string, CatalogItem[]>();
    for (const it of filtered) {
      const k = it.category || "Other";
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(it);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered, groupByCategory]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center", ACCENT[accent])}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            {!loading && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500">
                {items.length}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          placeholder={`Search ${title.toLowerCase()}…`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-blue-500/40"
        />
      </div>

      {/* Body */}
      {loading ? (
        <div className="flex items-center justify-center h-48 text-gray-500">
          <Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading {title.toLowerCase()}…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300 px-3 py-2 text-sm">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
          <PackageOpen className="h-10 w-10 mx-auto text-gray-300 dark:text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">{emptyHint ?? `No ${title.toLowerCase()} found.`}</p>
        </div>
      ) : groups ? (
        <div className="space-y-6">
          {groups.map(([cat, list]) => (
            <div key={cat}>
              <h2 className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2">
                {cat} <span className="text-gray-300 dark:text-gray-600">· {list.length}</span>
              </h2>
              <CardGrid items={list} />
            </div>
          ))}
        </div>
      ) : (
        <CardGrid items={filtered} />
      )}
    </div>
  );
}

function CardGrid({ items }: { items: CatalogItem[] }) {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {items.map((it) => (
        <div
          key={it.id}
          className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 hover:border-gray-300 dark:hover:border-gray-700 transition-colors"
        >
          <div className="flex items-center gap-2">
            {it.available === false ? (
              <span className="h-1.5 w-1.5 rounded-full bg-gray-300 dark:bg-gray-600" title="Not configured" />
            ) : (
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" title="Available" />
            )}
            <span className="font-medium text-sm truncate">{it.name}</span>
            {it.type && (
              <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 shrink-0">
                {it.type}
              </span>
            )}
          </div>
          {it.description && (
            <p className="text-xs text-gray-500 mt-1.5 line-clamp-2 leading-relaxed">{it.description}</p>
          )}
          {(it.tags?.length || it.detail) && (
            <div className="flex flex-wrap items-center gap-1 mt-2">
              {it.detail && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
                  {it.detail}
                </span>
              )}
              {it.tags?.slice(0, 4).map((t) => (
                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-400">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
