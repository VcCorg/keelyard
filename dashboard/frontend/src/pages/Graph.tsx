import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Share2, GitBranch, FolderGit2 } from "lucide-react";
import { KGGraph } from "@/pages/KGGraph";
import { CodeGraph } from "@/pages/CodeGraph";
import { cn } from "@/lib/utils";

/**
 * Graph — one home for both graph views. The Knowledge Graph is the ingested,
 * linked graph (code entities ↔ requirements, Neo4j); the Code Graph is a
 * repo's structural graphify graph captured at onboarding. `?view=code` deep-links
 * the code view (e.g. from the Repository page).
 */

type View = "kg" | "code";

export function Graph() {
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState<View>(params.get("view") === "code" ? "code" : "kg");

  const select = (v: View) => {
    setView(v);
    const next = new URLSearchParams(params);
    next.set("view", v);
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <Share2 className="h-7 w-7 text-blue-500" /> Graph
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Visualize your knowledge — the ingested knowledge graph, or a repo's structural code graph
        </p>
      </div>

      {/* View toggle */}
      <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-800 p-0.5 bg-gray-50 dark:bg-gray-900">
        {([
          { id: "kg" as const, label: "Knowledge Graph", icon: GitBranch },
          { id: "code" as const, label: "Code Graph", icon: FolderGit2 },
        ]).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => select(id)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              view === id
                ? "bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-300 shadow-sm"
                : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            )}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>

      {view === "kg" ? <KGGraph embedded /> : <CodeGraph embedded />}
    </div>
  );
}
