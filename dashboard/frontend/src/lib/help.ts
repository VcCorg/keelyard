/**
 * Per-navigation contextual help. A single data-driven registry keyed by route
 * so the header's HelpButton can explain any page: what it is, who owns it,
 * what it needs first, and which `keel` command it mirrors. Kept next to
 * nav.ts so the two stay in sync.
 */

export type HelpEntry = {
  title: string;
  /** One or two sentences: what this page is for. */
  what: string;
  /** Persona/role that primarily drives this feature. */
  persona?: string;
  /** Setup or upstream steps needed before this page is useful. */
  prerequisites?: string[];
  /** The CLI command(s) this page mirrors, if any. */
  cli?: string[];
  /** Short, practical pointers. */
  tips?: string[];
};

/**
 * Route → help. Dynamic routes (e.g. /kg/:domain) fall back to their parent
 * via `helpFor`. Keep entries tight — this is a glance, not a manual.
 */
export const HELP: Record<string, HelpEntry> = {
  "/setup": {
    title: "Get started",
    what: "Guided first-run setup. Work top to bottom: required steps unlock onboarding; the rest you can add anytime.",
    persona: "Everyone (admin usually runs it once)",
    cli: ["keel init workspace", "keel doctor"],
    tips: ["The Environment health panel is `keel doctor` — green means you're ready."],
  },
  "/": {
    title: "Dashboard",
    what: "At-a-glance state of your platform: domains, sessions, recent activity and setup readiness.",
    persona: "Everyone",
  },
  "/activity": {
    title: "Activity",
    what: "A live feed of recent CLI/agent commands — quick pulse of what's happening.",
    persona: "Everyone",
    cli: ["keel history log"],
  },
  "/audit": {
    title: "Audit History",
    what: "The central audit trail — every governed action sliced by who acted (actor), from where (source: cli/dashboard), and on which entity. The frontend for `keel history`.",
    persona: "Leads / admins for oversight",
    cli: ["keel history log", "keel history summary"],
    tips: ["Filter by actor to see one principal's actions, or by source to separate CLI vs dashboard activity."],
  },
  "/onboarding": {
    title: "Domain onboarding",
    what: "Generate a governed domain context meta-repo: skills, governance policy and workspace scaffolding for a domain.",
    persona: "Tech lead (Governance)",
    prerequisites: ["Workspaces configured"],
    cli: ["keel domain onboard", "keel init"],
    tips: ["This is the governance phase — the meta-repo it produces is what Build workflows are held to."],
  },
  "/workspaces": {
    title: "Workspaces",
    what: "The code and docs directories Keel reads from and writes to, plus per-domain workspace registration.",
    persona: "Tech lead / admin",
    cli: ["keel workspace", "keel init workspace"],
  },
  "/skills/personas": {
    title: "Persona skills",
    what: "Governs which skills each persona (dev/qa/ba/sm/domain) may load, via the domain's skills.yaml allow/deny policy.",
    persona: "Domain lead (Governance)",
    cli: ["keel skill"],
    tips: ["Hard enforcement is an admin toggle in Administration; otherwise out-of-policy skills warn."],
  },
  "/marketplace": {
    title: "Marketplace",
    what: "Browse and adopt shared skills and domain packs published across the platform.",
    persona: "Leads",
  },
  "/kg": {
    title: "KG Context",
    what: "Browse the knowledge-graph context available to a domain — code entities and requirement docs the agents can draw on.",
    persona: "Everyone (devs consume it while building)",
    prerequisites: ["A domain ingested into the KG"],
    cli: ["keel kg context"],
  },
  "/kg/graph": {
    title: "KG Graph",
    what: "Visualize a domain's whole knowledge graph — code entities linked to requirements. The frontend equivalent of `keel kg visualize`.",
    persona: "Leads / devs for review",
    prerequisites: ["Neo4j configured", "Domain ingested + linked (keel kg link)"],
    cli: ["keel kg visualize"],
  },
  "/kg/onboard": {
    title: "KG Onboarding",
    what: "Wizard to ingest a knowledge graph — domain-scoped (loaded via a domain) or session-scoped (loaded before a build).",
    persona: "Domain lead initiates; any role can load session KGs",
    prerequisites: ["Neo4j configured"],
    cli: ["keel kg ingest"],
  },
  "/kg/ingest": {
    title: "KG Ingest",
    what: "Ingest code and documents into the knowledge graph for a domain.",
    persona: "Tech lead",
    prerequisites: ["Neo4j configured", "Workspaces configured"],
    cli: ["keel kg ingest"],
  },
  "/kg/okf": {
    title: "OKF Generation",
    what: "Generate an Organizational Knowledge Fabric export enriched from the KG.",
    persona: "Admin",
    prerequisites: ["A populated KG"],
    cli: ["keel kg okf"],
  },
  "/data": {
    title: "Data Sources",
    what: "Register and inspect the data sources (repos, docs, integrations) feeding knowledge and agents.",
    persona: "Leads",
    cli: ["keel data"],
  },
  "/ideate": {
    title: "Requirements (Ideate)",
    what: "Turn a product idea into structured requirements/stories, then push them downstream to Work Items.",
    persona: "BA / SM",
    cli: ["keel product"],
    tips: ["Pushing requirements needs the requirements:push permission (developer+)."],
  },
  "/code-onboard": {
    title: "Repository (Build)",
    what: "Onboard a repository for governed development — optionally graphify its structure into a code graph.",
    persona: "Developer (Build)",
    prerequisites: ["A governed domain (from onboarding)"],
    cli: ["keel code onboard", "keel code onboard --graphify"],
    tips: ["Build is held to the domain's governance meta-repo; admins set the enforcement dial per domain."],
  },
  "/code-graph": {
    title: "Code Graph",
    what: "Review a repo's graphify structural graph — validate what was captured before it feeds the KG.",
    persona: "Developer / lead for review",
    prerequisites: ["A repo onboarded with the Graphify option"],
    cli: ["keel code onboard --graphify"],
  },
  "/execution": {
    title: "Execution & Context",
    what: "The vendor-neutral execution engines (Devin today, swappable) and their status, plus a preview of the portable, engine-neutral context bundle a build receives. Mirrors `keel execution` and `keel context`.",
    persona: "Developer (Build)",
    prerequisites: ["context:build permission (developer+) to render a bundle"],
    cli: ["keel execution list", "keel context build"],
    tips: ["The preview writes nothing; `keel context build` writes the bundle to disk."],
  },
  "/skills": {
    title: "Skills",
    what: "Browse and manage the skills available to agents and builds.",
    persona: "Developers / leads",
    cli: ["keel skill"],
  },
  "/skills/trials": {
    title: "Skill Trials",
    what: "Load and test a candidate skill for a domain (structure, security scan, persona policy, AI review, LLM-as-judge) before promoting it to the master skills repo.",
    persona: "QA (Quality) — any role can trial",
    cli: ["keel skill", "keel skill scan"],
    tips: [
      "Load a new skill from a folder (preferred) or a single SKILL.md — it's staged into the registry for trialing.",
      "The security scan (NVIDIA SkillSpector) can be toggled per trial; if it isn't installed, use 'Install scanner'.",
      "Promote copies the skill into the domain's validated skills; QA out-of-policy warns, it doesn't block.",
    ],
  },
  "/devin": {
    title: "Devin Sessions",
    what: "Launch and track Devin cloud sessions for governed development.",
    persona: "Developer (Build)",
    prerequisites: ["Devin API key configured", "A governed domain"],
    cli: ["keel devin", "keel execution"],
    tips: ["Devin sessions follow the same domain governance as local builds."],
  },
  "/snapshots": {
    title: "Snapshots",
    what: "Point-in-time snapshots of a domain/workspace state for review or rollback.",
    persona: "Tech lead",
    cli: ["keel context"],
  },
  "/tasks": {
    title: "Tasks",
    what: "Work items and their status across the team.",
    persona: "Everyone",
  },
  "/assignments": {
    title: "Assignments",
    what: "Who owns what — assign work and personas across the team.",
    persona: "Leads",
  },
  "/eval": {
    title: "Evaluation",
    what: "Run and review agent/skill evaluations, including LLM-as-judge scoring.",
    persona: "QA / agent builders",
    cli: ["keel eval"],
  },
  "/quickstart": {
    title: "Quickstart",
    what: "Scaffold a new agent project fast from a template.",
    persona: "Agent builders (leads)",
    cli: ["keel project create", "keel agent-template"],
  },
  "/projects": {
    title: "Agent Projects",
    what: "Manage agent projects — the containers for agents, tools and configs.",
    persona: "Agent builders (leads)",
    cli: ["keel project"],
  },
  "/canvas": {
    title: "Project Canvas",
    what: "Visually compose an agent project — wire agents, tools and data flows.",
    persona: "Agent builders (leads)",
  },
  "/agents": {
    title: "Agents",
    what: "Create and manage agent instances within a project.",
    persona: "Agent builders (leads)",
    cli: ["keel agent"],
  },
  "/models": {
    title: "Models",
    what: "Configure the LLM/embedding models available to agents.",
    persona: "Agent builders / admin",
    cli: ["keel init vertex-ai", "keel init local-model", "keel init builtin-model"],
  },
  "/tools": {
    title: "Tools",
    what: "Register the tools agents can call.",
    persona: "Agent builders (leads)",
    cli: ["keel agent-tool"],
  },
  "/retrievers": {
    title: "Retrievers",
    what: "Configure retrieval backends agents use for grounding.",
    persona: "Agent builders (leads)",
    cli: ["keel retriever"],
  },
  "/databases": {
    title: "Databases",
    what: "Register databases agents and retrievers can query.",
    persona: "Agent builders / admin",
  },
  "/mcp": {
    title: "MCP Servers",
    what: "Register and health-check MCP connectors — local (Docker) or remote — that agents route calls through.",
    persona: "Leads / admin (Platform)",
    cli: ["keel mcp"],
  },
  "/deployments": {
    title: "Deployments",
    what: "Deploy and track running agent deployments.",
    persona: "Admin (Platform)",
  },
  "/cli": {
    title: "CLI Console",
    what: "Run keel commands from the browser with streamed output — the full CLI, in-app.",
    persona: "Leads / admin",
    cli: ["keel"],
  },
  "/terminal": {
    title: "Terminal",
    what: "A real PTY terminal in the browser — for interactive steps (e.g. gcloud auth) the forms can't run.",
    persona: "Leads / admin",
  },
  "/chat": {
    title: "Chat",
    what: "Converse with a Keel agent over your configured model and knowledge.",
    persona: "Everyone",
  },
  "/admin": {
    title: "Administration",
    what: "Platform-wide controls: skill enforcement, per-domain build-governance defaults, branding and nav visibility.",
    persona: "Admin",
    cli: ["keel admin"],
  },
  "/identity": {
    title: "Identity & Access",
    what: "Who you are (subject, roles, persona, permissions), the RBAC model as a role × permission matrix, personas, and a live permission checker. The frontend for `keel auth`.",
    persona: "Admin / leads",
    cli: ["keel auth whoami", "keel auth roles", "keel auth check <permission>"],
    tips: ["Roles are cumulative — each grants everything below it; viewer is read-only."],
  },
  "/people": {
    title: "People",
    what: "Manage users, roles and persona assignments.",
    persona: "Admin",
    cli: ["keel auth"],
  },
  "/shared/agents": {
    title: "Shared Agents",
    what: "Agents shared across teams/workspaces.",
    persona: "Admin",
  },
  "/shared/kg": {
    title: "Shared KG",
    what: "Knowledge graphs shared across domains/teams.",
    persona: "Admin",
  },
};

/**
 * Resolve help for a pathname, tolerating dynamic segments by walking up the
 * path (so /kg/payments → /kg). Returns undefined when nothing is registered.
 */
export function helpFor(pathname: string): HelpEntry | undefined {
  if (HELP[pathname]) return HELP[pathname];
  const parts = pathname.split("/").filter(Boolean);
  while (parts.length > 0) {
    parts.pop();
    const candidate = "/" + parts.join("/");
    if (HELP[candidate]) return HELP[candidate];
  }
  return undefined;
}
