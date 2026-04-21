import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: "running" | "stopped" | "healthy" | "unhealthy" | "unknown" | "success" | "error";
  className?: string;
}

const statusStyles: Record<string, string> = {
  running: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  healthy: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  stopped: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  unknown: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  unhealthy: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  error: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        statusStyles[status] ?? statusStyles.unknown,
        className
      )}
    >
      <span
        className={cn("h-1.5 w-1.5 rounded-full", {
          "bg-emerald-500": status === "running" || status === "healthy" || status === "success",
          "bg-gray-400": status === "stopped",
          "bg-yellow-500": status === "unknown",
          "bg-red-500": status === "unhealthy" || status === "error",
        })}
      />
      {status}
    </span>
  );
}
