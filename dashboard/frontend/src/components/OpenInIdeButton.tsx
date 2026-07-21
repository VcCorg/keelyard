import { useEffect, useState } from "react";
import { ExternalLink, Loader2, Check, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

const EDITOR_LABELS: Record<string, string> = {
  devin: "Devin",
  windsurf: "Windsurf",
  cursor: "Cursor",
  code: "VS Code",
  open: "Finder",
};

function editorLabel(id: string): string {
  return EDITOR_LABELS[id] ?? id;
}

/**
 * Opens a working folder/file in a local editor or agent (Devin preferred) via
 * the backend `POST /workspaces/open-ide`. Lets the user review and edit files
 * at their on-disk location, then continue.
 */
export function OpenInIdeButton({
  path,
  label = "Open in IDE",
  variant = "outline",
  size = "default",
}: {
  path: string;
  label?: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm";
}) {
  const [editors, setEditors] = useState<string[]>([]);
  const [editor, setEditor] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listEditors()
      .then((r) => {
        if (cancelled) return;
        const list = r.editors ?? [];
        setEditors(list);
        setEditor(list[0] ?? "");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const open = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.openInIde(path, editor || undefined);
      setMsg({ ok: true, text: res.message || `Opened in ${editorLabel(res.editor)}` });
    } catch (e) {
      setMsg({ ok: false, text: String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Only offer a picker when the admin has enabled more than one IDE tool. */}
      {editors.length > 1 && (
        <select
          value={editor}
          onChange={(e) => setEditor(e.target.value)}
          title="Editor / agent (from Admin → Code assist tools)"
          className="h-9 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 text-sm"
        >
          {editors.map((ed) => (
            <option key={ed} value={ed}>
              {editorLabel(ed)}
            </option>
          ))}
        </select>
      )}
      <Button variant={variant} size={size} onClick={open} disabled={busy}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
        {label}
      </Button>
      {msg && (
        <span
          className={`text-xs flex items-center gap-1 ${
            msg.ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
          }`}
        >
          {msg.ok ? <Check className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
          {msg.text}
        </span>
      )}
    </div>
  );
}
