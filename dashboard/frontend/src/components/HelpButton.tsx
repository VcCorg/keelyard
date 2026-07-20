import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { HelpCircle, X, User, ListChecks, TerminalSquare, Lightbulb } from "lucide-react";
import { helpFor } from "@/lib/help";
import { cn } from "@/lib/utils";

/**
 * Contextual help for the current route. Renders a `?` in the header; clicking
 * opens a slide-over explaining the page — what it is, who owns it, what it
 * needs, and the CLI it mirrors. Data comes from lib/help.ts, so pages don't
 * each carry their own copy. Renders nothing on routes with no help entry.
 */
export function HelpButton() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const entry = helpFor(pathname);

  // Close on route change and on Escape.
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!entry) return null;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={`About: ${entry.title}`}
        aria-label={`Help for ${entry.title}`}
        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-gray-500 hover:text-gray-800 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800"
      >
        <HelpCircle className="h-4 w-4" />
        <span className="hidden sm:inline">Help</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex justify-end" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/30" />
          <div
            className="relative w-full max-w-sm h-full overflow-y-auto bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-blue-500" />
                <h2 className="text-base font-semibold">{entry.title}</h2>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close help"
                className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 space-y-5 text-sm">
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{entry.what}</p>

              {entry.persona && (
                <Section icon={User} label="Who uses this">
                  <p className="text-gray-600 dark:text-gray-400">{entry.persona}</p>
                </Section>
              )}

              {entry.prerequisites && entry.prerequisites.length > 0 && (
                <Section icon={ListChecks} label="Needs first">
                  <ul className="space-y-1">
                    {entry.prerequisites.map((p) => (
                      <li key={p} className="text-gray-600 dark:text-gray-400 flex gap-2">
                        <span className="text-gray-300 dark:text-gray-600">•</span> {p}
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {entry.cli && entry.cli.length > 0 && (
                <Section icon={TerminalSquare} label="Mirrors CLI">
                  <div className="space-y-1">
                    {entry.cli.map((c) => (
                      <code
                        key={c}
                        className="block font-mono text-[12px] text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded px-2 py-1"
                      >
                        {c}
                      </code>
                    ))}
                  </div>
                </Section>
              )}

              {entry.tips && entry.tips.length > 0 && (
                <Section icon={Lightbulb} label="Good to know">
                  <ul className="space-y-1.5">
                    {entry.tips.map((t) => (
                      <li key={t} className="text-gray-600 dark:text-gray-400">{t}</li>
                    ))}
                  </ul>
                </Section>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Section({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className={cn("flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1.5")}>
        <Icon className="h-3.5 w-3.5" /> {label}
      </p>
      {children}
    </div>
  );
}
