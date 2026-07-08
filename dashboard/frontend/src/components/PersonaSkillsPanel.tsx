import { useEffect, useState } from "react";
import {
  Eye,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { StreamConsole } from "@/components/StreamConsole";
import {
  api,
  type GeneratedPersonaInfo,
  type PersonaCatalogInfo,
} from "@/lib/api";
import { useUser } from "@/context/UserContext";

/**
 * Role-aware persona skills panel.
 *  - All users: review generated persona skills + recreate repo-level skills.
 *  - Admins: manage the product persona catalog + regenerate across all domains.
 *
 * Reused by the admin Domain Onboarding wizard and the standalone
 * /personas page (which non-admins can access).
 */
export function PersonaSkillsPanel({
  slug,
  product,
}: {
  slug: string;
  product: string;
}) {
  const { user } = useUser();
  const isAdmin = user.role === "admin";

  const [generated, setGenerated] = useState<GeneratedPersonaInfo[]>([]);
  const [catalog, setCatalog] = useState<PersonaCatalogInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewing, setViewing] = useState<{ id: string; content: string } | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [enrich, setEnrich] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, c] = await Promise.all([
        api.listGeneratedPersonas(slug),
        api.listProductPersonas(product),
      ]);
      setGenerated(g);
      setCatalog(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, product]);

  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const regenRepo = () => {
    setStreamUrl(api.regenPersonasStreamUrl(slug, { personas: selected, enrich }));
  };

  const viewPersona = async (id: string) => {
    try {
      const res = await api.getPersonaContent(slug, id);
      setViewing(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 px-3 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Review generated metadata skills */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Eye className="h-4 w-4" /> Review generated persona skills
          </h2>
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh
          </Button>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          Skills generated into <code>{`${slug}-context-meta/.agents/skills/personas/`}</code>
        </p>
        {generated.length === 0 ? (
          <p className="text-sm text-gray-400">
            No persona skills generated yet. Use “Recreate” below, or run domain init-meta in the
            onboarding Scaffold step.
          </p>
        ) : (
          <div className="space-y-2">
            {generated.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between gap-2 rounded-md border border-gray-100 dark:border-gray-800 px-3 py-2"
              >
                <label className="flex items-center gap-2 min-w-0">
                  <input
                    type="checkbox"
                    checked={selected.includes(p.id)}
                    onChange={() => toggle(p.id)}
                  />
                  <span className="font-mono text-sm">{p.id}</span>
                  <Badge variant={p.source === "built-in" ? "secondary" : "default"}>
                    {p.source}
                  </Badge>
                  <span className="text-xs text-gray-400 truncate">{p.title}</span>
                </label>
                <Button variant="ghost" size="sm" onClick={() => viewPersona(p.id)}>
                  <Eye className="h-4 w-4" /> View
                </Button>
              </div>
            ))}
          </div>
        )}

        {viewing && (
          <div className="mt-3 rounded-md border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-800">
              <span className="font-mono text-sm">{viewing.id}/SKILL.md</span>
              <Button variant="ghost" size="sm" onClick={() => setViewing(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <pre className="max-h-80 overflow-auto p-3 text-xs whitespace-pre-wrap">
              {viewing.content}
            </pre>
          </div>
        )}
      </div>

      {/* Repo / domain-level regeneration — available to all users */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <h2 className="font-semibold mb-1">Recreate repo-level skills</h2>
        <p className="text-xs text-gray-500 mb-3">
          Regenerates persona skills into this domain’s meta-repo. Select specific personas above,
          or recreate all. Available to all team members.
        </p>
        <div className="flex flex-wrap gap-2 items-center">
          <Button onClick={regenRepo}>
            <RefreshCw className="h-4 w-4" />
            {selected.length > 0 ? `Recreate ${selected.length} selected` : "Recreate all"}
          </Button>
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
            <input type="checkbox" checked={enrich} onChange={(e) => setEnrich(e.target.checked)} />
            AI-enrich (personas marked ai_enrich)
          </label>
          {selected.length > 0 && (
            <Button variant="ghost" size="sm" onClick={() => setSelected([])}>
              Clear selection
            </Button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Runs <code>keel domain regen-personas {slug}</code> via the CLI.
        </p>
        <StreamConsole url={streamUrl} title="keel domain regen-personas" onDone={refresh} />
      </div>

      {/* Product-level catalog — admin only */}
      <ProductPersonaPanel
        product={product}
        isAdmin={isAdmin}
        catalog={catalog}
        onChanged={refresh}
        onError={setError}
      />
    </div>
  );
}

/* ── Admin: product-level persona catalog management ──────────────────────── */
function ProductPersonaPanel({
  product,
  isAdmin,
  catalog,
  onChanged,
  onError,
}: {
  product: string;
  isAdmin: boolean;
  catalog: PersonaCatalogInfo[];
  onChanged: () => void;
  onError: (msg: string) => void;
}) {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [enrich, setEnrich] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ id: "", label: "", description: "" });
  const [busy, setBusy] = useState(false);

  const add = async () => {
    if (!form.id.trim() || !form.label.trim()) {
      onError("Persona id and label are required.");
      return;
    }
    setBusy(true);
    try {
      await api.addProductPersona(product, {
        id: form.id.trim(),
        label: form.label.trim(),
        description: form.description.trim() || undefined,
        ai_enrich: enrich,
      });
      setForm({ id: "", label: "", description: "" });
      setAdding(false);
      onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    setBusy(true);
    try {
      await api.removeProductPersona(product, id);
      onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <div className="flex items-center justify-between mb-1">
        <h2 className="font-semibold flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" /> Product-level persona catalog
          <Badge variant="secondary">{product}</Badge>
        </h2>
        {!isAdmin && (
          <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <Lock className="h-3 w-3" /> Admin only
          </span>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Personas defined here apply to every domain under <strong>{product}</strong>. Built-ins are
        always available; product-specific personas (e.g. Tech Lead, Product Owner) are added here.
      </p>

      {/* Catalog table */}
      <div className="space-y-1 mb-3">
        {catalog.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between gap-2 rounded-md border border-gray-100 dark:border-gray-800 px-3 py-1.5"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-mono text-sm">{p.id}</span>
              <Badge variant={p.source === "built-in" ? "secondary" : "default"}>{p.source}</Badge>
              {p.ai_enrich && <Badge variant="outline">ai-enrich</Badge>}
              <span className="text-xs text-gray-400 truncate">{p.label}</span>
            </div>
            {isAdmin && p.source === "product" && (
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => remove(p.id)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
      </div>

      {isAdmin ? (
        <>
          {adding ? (
            <div className="space-y-2 rounded-md border border-gray-200 dark:border-gray-800 p-3 mb-3">
              <div className="grid grid-cols-2 gap-2">
                <Input
                  placeholder="id (e.g. tech-lead)"
                  value={form.id}
                  onChange={(e) => setForm({ ...form, id: e.target.value })}
                />
                <Input
                  placeholder="Label (e.g. Tech Lead)"
                  value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                />
              </div>
              <Input
                placeholder="Description (optional)"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={enrich}
                  onChange={(e) => setEnrich(e.target.checked)}
                />
                Mark for AI enrichment
              </label>
              <div className="flex gap-2">
                <Button onClick={add} disabled={busy}>
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  Add persona
                </Button>
                <Button variant="ghost" onClick={() => setAdding(false)}>
                  Cancel
                </Button>
              </div>
              <p className="text-xs text-gray-400">
                For rich multi-section content, edit <code>personas.yaml</code> in the product
                meta-repo directly.
              </p>
            </div>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setAdding(true)} className="mb-3">
              <Plus className="h-4 w-4" /> Add product persona
            </Button>
          )}

          <div className="border-t border-gray-100 dark:border-gray-800 pt-3">
            <div className="flex flex-wrap gap-2 items-center">
              <Button
                variant="outline"
                onClick={() => setStreamUrl(api.productRegenPersonasStreamUrl(product, enrich))}
              >
                <RefreshCw className="h-4 w-4" /> Regenerate across all {product} domains
              </Button>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Runs <code>keel domain regen-personas</code> for every domain under {product}.
            </p>
            <StreamConsole
              url={streamUrl}
              title="keel product regen-personas"
              onDone={onChanged}
            />
          </div>
        </>
      ) : (
        <p className="text-xs text-gray-400">
          Only admins can add/remove product personas or regenerate product-level skills. You can
          recreate repo-level skills for this domain above.
        </p>
      )}
    </div>
  );
}
