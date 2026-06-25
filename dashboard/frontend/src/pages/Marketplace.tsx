import { ExternalLink, Package, Puzzle, Server, FileText, ArrowRight, Boxes } from "lucide-react";
import { Link } from "react-router-dom";
import type { ComponentType } from "react";

const WEB_MARKETPLACE = "https://context-marketplace.ai-prod.example.com/";
const IDE_EXTENSION_VSIX =
  "https://gitlab.gcp.example.com/api/v4/projects/4273/packages/generic/example-ai/0.1.3/example-ai-0.1.3.vsix";
const SKILLS_REPO = "https://gitlab.gcp.example.com/ai/model-context/agent-skills";
const EXTENSIONS_REPO = "https://gitlab.gcp.example.com/ai/model-context/vibe-coding-extensions";

type Artifact = {
  icon: ComponentType<{ className?: string }>;
  title: string;
  type: string;
  description: string;
  href: string;
  cta: string;
};

const ARTIFACTS: Artifact[] = [
  {
    icon: Package,
    title: "Agent Skills",
    type: "agent-skill",
    description:
      "Reusable SKILL.md packages that teach AI assistants how to perform domain tasks. Browse and install them on the Skills page.",
    href: SKILLS_REPO,
    cta: "View skills repo",
  },
  {
    icon: Puzzle,
    title: "example AI IDE Extension",
    type: "ide-extension",
    description:
      "VS Code extension to connect to ACP-compatible coding agents (Copilot, Claude Code, Gemini CLI). Download the latest .vsix.",
    href: IDE_EXTENSION_VSIX,
    cta: "Download .vsix",
  },
  {
    icon: Server,
    title: "MCP Servers",
    type: "mcp-server",
    description:
      "Model Context Protocol servers published as marketplace artifacts. Manage connected servers on the MCP Servers page.",
    href: EXTENSIONS_REPO,
    cta: "View extensions repo",
  },
  {
    icon: FileText,
    title: "Rules / AGENTS.md",
    type: "rules",
    description:
      "Shared agent rule sets and AGENTS.md conventions distributed through the marketplace registry.",
    href: WEB_MARKETPLACE,
    cta: "Open marketplace",
  },
];

export function Marketplace() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Context Marketplace</h1>
          <p className="text-sm text-gray-500 mt-0.5 max-w-2xl">
            example's federated registry of AI lifecycle artifacts — agent skills, IDE extensions, MCP
            servers, and rules. The full marketplace is available in the browser and as an IDE extension.
          </p>
        </div>
        <a
          href={WEB_MARKETPLACE}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
        >
          <ExternalLink className="h-4 w-4" /> Open Marketplace
        </a>
      </div>

      {/* Skills callout */}
      <div className="rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 p-4 flex items-center gap-4">
        <Boxes className="h-6 w-6 text-blue-600 dark:text-blue-400 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-blue-900 dark:text-blue-200">
            Skills are integrated directly in this dashboard
          </p>
          <p className="text-xs text-blue-700/80 dark:text-blue-300/80 mt-0.5">
            Browse, view, and install marketplace skills into your projects, domain repos, or Devin.
          </p>
        </div>
        <Link
          to="/skills"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-white dark:bg-gray-900 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 hover:bg-blue-100/50 shrink-0"
        >
          Go to Skills <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* Artifact cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ARTIFACTS.map((a) => {
          const Icon = a.icon;
          return (
            <div
              key={a.title}
              className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col"
            >
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <Icon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">{a.title}</h3>
                  <span className="text-[10px] font-mono text-gray-400">{a.type}</span>
                </div>
              </div>
              <p className="text-sm text-gray-500 mt-3 flex-1">{a.description}</p>
              <a
                href={a.href}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
              >
                {a.cta} <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-gray-400">
        Note: the web marketplace and these repositories are protected by example SSO. You may be prompted
        to authenticate.
      </p>
    </div>
  );
}
