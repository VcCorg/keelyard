import { AlertTriangle, Wrench } from "lucide-react";
import { useSetup } from "@/context/SetupContext";

/**
 * Validation banner shown on pages whose workflow needs specific `dva init`
 * steps. Renders nothing when all `requires` items are configured (or while
 * the status is still loading). Clicking "Configure" opens the global setup
 * modal mounted in Layout.
 *
 * @example
 *   <SetupRequiredBanner requires={["workspaces", "neo4j"]} feature="KG ingest" />
 */
export function SetupRequiredBanner({
  requires,
  feature,
}: {
  requires: string[];
  feature: string;
}) {
  const { status, openPanel } = useSetup();
  if (!status) return null;

  if (!status.cli_available) {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3">
        <AlertTriangle className="h-4 w-4 mt-0.5 text-red-600 dark:text-red-400 shrink-0" />
        <div className="flex-1 text-sm text-red-700 dark:text-red-300">
          The <code>dva</code> CLI is not available. {feature} cannot run until it is installed.
        </div>
        <button
          onClick={openPanel}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-md bg-red-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-red-700"
        >
          <Wrench className="h-3.5 w-3.5" /> Setup
        </button>
      </div>
    );
  }

  const missing = status.items.filter((i) => requires.includes(i.key) && !i.configured);
  if (missing.length === 0) return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-4 py-3">
      <AlertTriangle className="h-4 w-4 mt-0.5 text-amber-600 dark:text-amber-400 shrink-0" />
      <div className="flex-1 text-sm text-amber-800 dark:text-amber-300">
        <span className="font-medium">CLI setup required for {feature}.</span> Configure:{" "}
        {missing.map((m) => m.label).join(", ")}.
      </div>
      <button
        onClick={openPanel}
        className="shrink-0 inline-flex items-center gap-1.5 rounded-md bg-amber-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
      >
        <Wrench className="h-3.5 w-3.5" /> Configure
      </button>
    </div>
  );
}
