import type { ComponentType, ReactNode } from "react";

interface PlaceholderPageProps {
  icon: ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
  phase: string;
  /** Bullet points describing the planned capability. */
  planned: string[];
  children?: ReactNode;
}

/**
 * Consistent placeholder for management-view pages whose backend is not yet
 * implemented. Documents the planned capability and its rollout phase so the
 * navigation is fully wired before the data layer lands.
 */
export function PlaceholderPage({
  icon: Icon,
  title,
  subtitle,
  phase,
  planned,
  children,
}: PlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
          <Icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              {phase}
            </span>
          </div>
          <p className="text-sm text-gray-500">{subtitle}</p>
        </div>
      </div>

      <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Planned capability
        </h2>
        <ul className="space-y-2">
          {planned.map((p, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0" />
              <span>{p}</span>
            </li>
          ))}
        </ul>
        {children && <div className="mt-5">{children}</div>}
      </div>
    </div>
  );
}
