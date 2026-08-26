// API client for Agent Playground dashboard.

// Configurable at build time via VITE_API_BASE.
//  - Default: relative "/api" so requests are same-origin and routed through
//    the Vite dev proxy (see vite.config.ts) or the production reverse proxy.
//    This avoids cross-origin CORS failures when the app is opened from any
//    host/port other than the backend's allowlisted origins (e.g. an IDE
//    browser-preview proxy or a LAN IP).
//  - Override with an absolute URL (e.g. http://localhost:8000/api) only when
//    talking to a backend that is not proxied on the same origin.
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

/* ============ Types ============ */

export interface AgentInfo {
  name: string;
  status: string;
  pid?: number;
  path?: string;
  review_mode?: string;
  poll_interval?: number;
  log_file?: string;
  agent_type: string;
}

export interface MCPServerInfo {
  name: string;
  type: string;
  enabled: boolean;
  url?: string;
  port?: number;
  description?: string;
  tools: string[];
  health_status: string;
  health_message: string;
  container_name?: string;
  container_status?: string;
  auth_status?: string; // ok, missing, invalid, unreachable, n/a, unknown
  auth_message?: string;
  source?: "docker" | "registry"; // registry = user-registered, editable
}

export interface DockerServiceStatus {
  name: string;
  description: string;
  container_name: string;
  port?: number | null;
  running: boolean;
  reachable: boolean;
  status: string; // running | exited | absent | <raw>
}

export interface DockerMcpStatus {
  docker_available: boolean; // docker CLI reachable from the backend (for start/stop)
  docker_message: string;
  stack_reachable: boolean;  // at least one MCP service port responds
  running_count: number;
  compose_found: boolean;
  compose_path?: string | null;
  services: DockerServiceStatus[];
}

export interface MCPServerUpsert {
  name: string;
  url: string;
  type?: "sse" | "http";
  description?: string;
  enabled?: boolean;
  tools?: string[];
}

export interface ActivityEntry {
  id: string;
  command: string;
  subcommand?: string;
  status: string;
  timestamp: string;
  duration_ms?: number;
  repo_path?: string;
  details?: Record<string, unknown> | null;
  source?: string | null;
  actor?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  correlation_id?: string | null;
}

export interface OverviewData {
  agents: {
    total: number;
    running: number;
    stopped: number;
  };
  mcp_servers: {
    total: number;
    healthy: number;
    unhealthy: number;
  };
  activity: {
    total_commands: number;
    total_errors: number;
    last_activity?: string;
    recent: ActivityEntry[];
  };
  projects: {
    total: number;
    valid: number;
    with_domain: number;
    items: any[];
  };
}

export interface DeploymentMetrics {
  cpu_percent?: number;
  memory_mb?: number;
  requests_per_min?: number;
  avg_latency_ms?: number;
  error_rate?: number;
  uptime_percent?: number;
}

export interface DeploymentConfig {
  agent_name: string;
  target: string;
  environment: string;
  max_instances: number;
  timeout_seconds?: number;
}

export interface DeploymentVersion {
  version: string;
  created_at: string;
  status: string;
  config: DeploymentConfig;
  metrics?: DeploymentMetrics;
}

export interface Deployment {
  id: string;
  agent_name: string;
  target: string;
  environment: string;
  status: string;
  created_at: string;
  updated_at: string;
  current_version?: string;
  replicas: number;
  metrics?: DeploymentMetrics;
  versions: DeploymentVersion[];
}

/* ============ KG Types ============ */

export interface DomainKGStats {
  domain: string;
  product: string;
  code_entities: number;
  requirement_docs: number;
  linked_edges: number;
  unlinked_docs: number;
  coverage_pct: number;
  relationship_breakdown: Record<string, number>;
  has_data: boolean;
}

export interface ProductKGSummary {
  product: string;
  total_domains: number;
  total_code_entities: number;
  total_requirement_docs: number;
  total_linked_edges: number;
  overall_coverage_pct: number;
  domains: DomainKGStats[];
}

export interface KGLinkRow {
  code_id: string;
  code_name: string;
  code_type: string;
  doc_id: string;
  doc_name: string;
  relationship: string;
  confidence: number;
  evidence: string;
  domain: string;
}

export interface KGGapRow {
  doc_id: string;
  doc_name: string;
  domain: string;
  jira_id?: string;
  content_preview: string;
}

export interface KGGraphNode {
  id: string;
  label: string;
  node_type: "code" | "document";
  domain?: string;
}

export interface KGGraphEdge {
  source: string;
  target: string;
  relationship: string;
  confidence: number;
}

export interface KGNeighborhood {
  nodes: KGGraphNode[];
  edges: KGGraphEdge[];
  center_id: string;
}

/* ============ KG Ingest Types ============ */

export interface IngestJobInfo {
  job_id: string;
  source: string;
  source_type: string;
  format?: string;
  provider: string;
  status: string;
  is_async: boolean;
  workspace?: string;
  domain?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: Record<string, any>;
}

export interface IngestableDomain {
  slug: string;
  product: string;
  domain: string;
  doc_count: number;
  repo_count: number;
  kg_ingested: number;
  confluence_space?: string;
  confluence_url?: string;
}

export interface IngestSubmitParams {
  domain?: string;
  product?: string;
  path?: string;
  source?: string;
  format?: string;
  provider?: string;
  workspace?: string;
  depth?: number;
  top?: number;
}

/* ============ OKF (Open Knowledge Format) Types ============ */

export interface OKFBundleInfo {
  domain: string;
  source: "authored" | "export";
  product: string;
  path: string;
  exists: boolean;
  concepts: number;
  freqs: number;
  has_report: boolean;
  freshness: "fresh" | "stale" | "unknown" | "n/a";
  stale_repos: string[];
  enriched_at: string | null;
}

export interface OKFFreqRow {
  freq_id: string;
  title: string;
  dev_gap: boolean;
  qa_gap: boolean;
  acceptance_criteria: number;
}

export interface OKFValidation {
  ok: boolean;
  concepts: number;
  links: number;
  typed_links: number;
  error_count: number;
  errors: string[];
}

export interface OKFBundleDetail {
  info: OKFBundleInfo;
  validation: OKFValidation;
  freqs: OKFFreqRow[];
  gap_count: number;
  unmapped_labels: number;
  unmapped_rels: number;
  quarantined_triples: number;
}

export interface OKFExportParams {
  domain: string;
  product?: string;
  mint_freqs?: boolean;
}

export interface ProjectionEntry {
  concept_id: string;
  name: string;
  source_ref: string;
  state: "in_sync" | "drift" | "unprojected" | "orphan";
  knowledge_id?: string | null;
  version: number;
  synced_at?: string | null;
}

export interface OKFProjectionStatus {
  domain: string;
  source: "authored" | "export";
  exists: boolean;
  state: "in_sync" | "drift" | "unprojected" | "empty";
  total_canonical: number;
  projected: number;
  in_sync: number;
  drift: number;
  unprojected: number;
  orphan: number;
  entries: ProjectionEntry[];
}

export interface OKFDevinStatus {
  api_key_present: boolean;
}

export interface OKFDevinPushParams {
  domain: string;
  source?: "authored" | "export";
  types?: string;
  dry_run?: boolean;
}

export interface DevinFolder {
  id: string;
  name: string;
  description: string;
}

export interface DevinKnowledgeItem {
  id: string;
  name: string;
  body: string;
  trigger_description: string;
  pinned_repo: string | null;
  parent_folder_id: string | null;
  folder_name: string | null;
  created_by: string | null;
  created_at: string | null;
}

export interface DevinKnowledgeUpdate {
  name?: string;
  body?: string;
  trigger_description?: string;
  pinned_repo?: string;
  parent_folder_id?: string;
}

export interface DevinKnowledgeList {
  folders: DevinFolder[];
  knowledge: DevinKnowledgeItem[];
}

/* ---- Integration status ---- */
export type IntegrationState = "ok" | "warn" | "error" | "unknown";

export interface IntegrationStatus {
  key: string;
  label: string;
  status: IntegrationState;
  detail: string;
  hint: string;
}

export interface IntegrationsResponse {
  integrations: IntegrationStatus[];
}

/* ---- Devin Sessions (standalone /api/devin) ---- */
export interface DevinStatus {
  api_key_present: boolean;
  base_url: string;
  default_max_acu: number;
  domains: Record<string, unknown>;
}

export interface DevinSession {
  session_id: string;
  url?: string | null;
  status?: string | null;
  title?: string | null;
  domain?: string | null;
  jira?: string | null;
  tags: string[];
  created_at?: string | null;
}

export interface CreateDevinSessionRequest {
  prompt: string;
  title?: string;
  domain?: string | null;
  jira?: string;
  bundle?: string | null;
  knowledge_from_sync?: boolean;
  knowledge_ids?: string[];
  snapshot_id?: string | null;
  playbook_id?: string | null;
  tags?: string[];
  max_acu?: number | null;
  idempotent?: boolean;
  unlisted?: boolean;
  dry_run?: boolean;
}

export interface CreateDevinSessionResponse {
  dry_run: boolean;
  session_id?: string | null;
  url?: string | null;
  status?: string | null;
  is_new: boolean;
  reused_local: boolean;
  payload: Record<string, unknown>;
  knowledge_count: number;
}

export interface AdminBranding {
  app_title: string;
  app_name: string;
}

export interface CodeAssistConfig {
  enabled: string[];
  default: string;
}

/** Onboarding-IDE tools = where `keel code onboard` writes SKILL.md so the
 *  IDE reads it. Same shape as CodeAssistConfig but a distinct concept from
 *  the execution engines above — see docs/GOVERNANCE_LAYERS.md. */
export interface OnboardingIdeConfig {
  enabled: string[];
  default: string;
}

export interface AdminSettings {
  branding: AdminBranding;
  nav_visibility: Record<string, string[]>;
  skill_enforcement: "off" | "enforce";
  build_governance_default: "off" | "warn" | "enforce";
  code_assist: CodeAssistConfig;
  onboarding_ide: OnboardingIdeConfig;
}

export interface BuildGovernanceInfo {
  domain: string;
  level: "off" | "warn" | "enforce";
  source: string;
  meta_repo_found: boolean;
  registered_repos: { slug: string; clone_url: string }[];
}

export interface AdminSettingsUpdate {
  branding?: AdminBranding;
  nav_visibility?: Record<string, string[]>;
  replace_nav?: boolean;
  skill_enforcement?: "off" | "enforce";
  build_governance_default?: "off" | "warn" | "enforce";
  code_assist?: CodeAssistConfig;
  onboarding_ide?: OnboardingIdeConfig;
}

export interface OnboardingIdeTool {
  name: string;
  label: string;
  description: string;
  deprecated: boolean;
  has_bridge: boolean;
}

export interface RoleAssignment {
  subject: string;
  roles: string[];
}

export interface RoleAssignments {
  valid_roles: string[];
  assignments: RoleAssignment[];
}

export interface RoleAssignmentUpdate {
  subject: string;
  roles: string[];
}

export interface ResetScope {
  scope: string;
  label: string;
  items: number;
}

export interface ResetPreview {
  scopes: ResetScope[];
}

/* ============ Watchers ============ */

// ---- Context trace (KeelTrace): what an agent actually read ----
export interface ContextRead {
  id: number;
  timestamp: string;
  source: string;            // mcp | kg | retriever
  operation: string;         // e.g. bitbucket/get_issue
  entity_id?: string | null;
  bytes: number;
  duration_ms?: number | null;
  status: string;
  args_digest?: string | null;
  payload_ref?: string | null;
}
export interface SourceRollup { source: string; reads: number; bytes: number; }
export interface SessionLedger {
  session_id: string;
  reads: number;
  bytes: number;
  errors: number;
  by_source: SourceRollup[];
  entries: ContextRead[];
}
export interface TraceSessionRef {
  session_id: string;
  reads: number;
  bytes: number;
  errors: number;
  sources: string[];
  earliest?: string | null;
  latest?: string | null;
}

export interface WatcherHandler {
  agent: string;
  chain: string[];
  input: Record<string, unknown>;
}

export interface WatcherSpec {
  name: string;
  trigger_type: string;
  handler: WatcherHandler;
  filter: Record<string, unknown>;
  domain: string;
  enabled: boolean;
  poll_seconds: number;
  description: string;
}

export interface WatcherStateInfo {
  cursor: string | null;
  last_polled: string | null;
  last_fired: string | null;
  last_error: string;
  delivered_count: number;
}

export interface WatcherView {
  spec: WatcherSpec;
  state: WatcherStateInfo;
}

export interface TriggerField {
  type: "string" | "int" | "bool" | "regex" | "duration" | string;
  label: string;
  required: boolean;
  help: string;
}

export interface TriggerInfo {
  name: string;
  label: string;
  description: string;
  source_mcp: string;
  filter_schema: Record<string, TriggerField>;
  default_poll_seconds: number;
}

export interface TestRunEvent {
  event_id: string;
  ts: string;
  data: Record<string, unknown>;
}

export interface TestRunResult {
  trigger_type: string;
  matched: number;
  events: TestRunEvent[];
  error: string;
}

export interface ResetResult {
  reset: string[];
  summary: Record<string, unknown>;
}

export interface AuthMe {
  subject: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  groups: string[];
  provider: string;
  authenticated: boolean;
  mode: string;
  persona?: string;
}

export interface RbacRole {
  role: string;
  permissions: string[];
  read_only: boolean;
}
export interface RbacPermission {
  permission: string;
  description: string;
}
export interface RbacPersona {
  persona: string;
  description: string;
}
export interface RbacModel {
  roles: RbacRole[];
  permissions: RbacPermission[];
  personas: RbacPersona[];
}
export interface PermissionCheck {
  subject: string;
  permission: string;
  allowed: boolean;
  roles: string[];
}

export interface ExecutionEngineInfo {
  name: string;
  available: boolean;
  kind: string; // "cloud" | "local" | "ide"
  description: string;
  detail: string;
  supports_ask?: boolean;
}

export interface SessionLaunchRequest {
  prompt: string;
  title?: string;
  jira?: string;
  domain?: string | null;
  tags?: string[];
  refs?: string[];
  engine?: string | null;
  dry_run?: boolean;
}

export interface SessionLaunchResult {
  engine: string;
  session_id?: string | null;
  url?: string | null;
  status?: string | null;
  is_new: boolean;
  dry_run: boolean;
  detail: Record<string, unknown>;
}

export interface EngineAskResult {
  engine: string;
  answer: string;
  authoritative: boolean;
  session_id?: string | null;
  url?: string | null;
}

export interface PortableContextRequest {
  prompt: string;
  title?: string;
  jira?: string;
  domain?: string | null;
  tags?: string[];
  refs?: string[];
}

export interface PortableContextResult {
  engine: string;
  bundle_id?: string | null;
  context_md: string;
  item_count: number;
  resolved: number;
}

export interface DevinSessionDetail {
  session_id: string;
  url?: string | null;
  status?: string | null;
  structured_output?: unknown;
  raw: Record<string, unknown>;
}

export type DevinSnapshotState =
  | "ok"
  | "drift"
  | "no-snapshot"
  | "meta-missing"
  | "unverifiable";

export interface DevinSnapshot {
  domain: string;
  snapshot_id?: string | null;
  blueprint_id?: string | null;
  knowledge_folder?: string | null;
  built_at?: string | null;
  meta_repo_path?: string | null;
  recorded_sha?: string | null;
  current_sha?: string | null;
  state: DevinSnapshotState;
  detail: string;
}

/* ============ Domain Onboarding Types ============ */

export interface ProductInfo {
  name: string;
  description?: string;
  tags: string[];
  domain_count: number;
}

export interface CreateProductBody {
  name: string;
  description?: string;
  tags?: string[];
}

export interface UpdateProductBody {
  description?: string;
  tags?: string[];
}

export interface RepoInfo {
  repo_slug: string;
  repo_name?: string;
  clone_url?: string;
  onboarded: boolean;
}

export interface DocInfo {
  source_page_id: string;
  source_space_key?: string;
  title?: string;
  source_version: number;
}

export interface DomainInfo {
  name: string;
  product: string;
  domain: string;
  description?: string;
  jira_project?: string;
  jira_board?: string;
  bitbucket_project?: string;
  bitbucket_url?: string;
  confluence_space?: string;
  confluence_url?: string;
  jira_dashboard?: string;
  tags: string[];
  kg_ingested: number;
  repo_count: number;
  doc_count: number;
}

export interface DomainDetail extends DomainInfo {
  repos: RepoInfo[];
  docs: DocInfo[];
}

/* ---- Persona-tiered workspaces ---- */

export interface WorkspaceRepoRef {
  slug?: string;
  mode?: string;        // code | graph-ref
  branch?: string;
  path?: string | null;
}

export interface WorkspaceInfo {
  tier: string;         // repo | domain | product
  persona: string;      // dev | tech-lead | solutions-architect
  root_path: string;
  product?: string | null;
  domain?: string | null;
  store_path?: string | null;
  repos: WorkspaceRepoRef[];
  created_at?: string | null;
  last_active?: string | null;
}

export interface WorkspaceTarget {
  persona: string;
  tier: string;                  // product | domain | repo
  path?: string | null;
  exists: boolean;
  ready: boolean;
  needs?: string | null;         // sync | open | onboard | null
  hint: string;
  /** Only present when requested with `drift: true` (the check re-renders the
   *  template, so it is not part of the fast target resolution). */
  drift?: TemplateDriftSummary | null;
}

export interface TemplateFileDrift {
  path: string;
  status: string;                // unchanged | template-updated | locally-modified | ...
  detail: string;
}

export interface TemplateDriftSummary {
  domain: string;
  meta_repo?: string | null;
  template_version: string;
  recorded_version?: string | null;
  has_baseline: boolean;
  version_behind: boolean;
  drifted: boolean;
  counts: Record<string, number>;
  upgradable: number;            // template moved ahead — safe to pull down
  promotable: number;            // local content ahead — candidate to push up
  conflicted: number;            // both sides moved — needs a human
  error?: string | null;         // the check could not run
}

export interface TemplateStatus extends TemplateDriftSummary {
  files: TemplateFileDrift[];
}

export interface TemplateOverlayInfo {
  overlay_root: string;
  files: string[];
  env_var: string;
}

export interface TemplatePromotable {
  domain: string;
  meta_repo?: string | null;
  overlay_root: string;
  files: TemplateFileDrift[];
}

export interface OpenIdeResult {
  success: boolean;
  editor: string;
  command: string;
  path: string;
  message: string;
}

export interface ScaffoldRepoPath {
  kind: "context" | "meta";
  path: string;
  exists: boolean;
}

export interface ScaffoldPaths {
  context: ScaffoldRepoPath;
  meta: ScaffoldRepoPath;
}

export interface BitbucketRepoCandidate {
  slug: string;
  name?: string;
  clone_url?: string;
  already_linked: boolean;
}

export interface ConfluencePageCandidate {
  page_id: string;
  title?: string;
  space_key?: string;
  version: number;
  already_tracked: boolean;
}

export interface CreateDomainBody {
  domain: string;
  product: string;
  description?: string;
  jira_project?: string;
  jira_board?: string;
  bitbucket_project?: string;
  bitbucket_url?: string;
  confluence_space?: string;
  confluence_url?: string;
  jira_dashboard?: string;
  tags?: string[];
}

/* ============ Persona Skills Types ============ */

export interface GeneratedPersonaInfo {
  id: string;
  title: string;
  source: "built-in" | "product";
  path: string;
  bytes: number;
}

export interface PersonaCatalogInfo {
  id: string;
  label: string;
  source: "built-in" | "product";
  ai_enrich: boolean;
}

export interface AddPersonaBody {
  id: string;
  label: string;
  description?: string;
  sections?: { title: string; body: string }[];
  ai_enrich?: boolean;
}

/* ============ Product Meta-Repo / Governance / Exceptions Types ============ */

export interface GovernanceInfo {
  found: boolean;
  path?: string;
  governance?: {
    branch_pattern?: string;
    require_ci_gates?: boolean;
    require_code_review?: boolean;
    min_reviewers?: number;
    require_tests?: boolean;
    test_coverage_min?: number;
    promotion_path?: string[];
    checkpoint_gate_map?: { checkpoint: string; gate: string; blocking?: boolean }[];
    inner_loop_floor?: string[];
    [k: string]: unknown;
  } | null;
  crosswalk?: {
    promotion_path?: string[];
    checkpoint_gate_map?: { checkpoint: string; gate: string; blocking?: boolean }[];
  } | null;
}

export interface ExceptionInfo {
  id: string;
  rule: string;
  reason: string;
  scope: string;
  owner: string;
  created_at: string;
  expires_at: string;
  status: string;
  effective: boolean;
}

export interface AddExceptionBody {
  rule: string;
  reason: string;
  scope: string;
  owner: string;
  expires?: string;
}

/* ============ Data Source Types ============ */

export interface DataSourceInfo {
  name: string;
  type: string;
  location: string;
  description: string;
  project: string;
  tags: string[];
  kg_status: string;
  confluence_space?: string;
  git_branch?: string;
  git_tag?: string;
  created_at?: string;
}

export interface CreateDataSourceBody {
  name: string;
  source_type: string;
  source_location: string;
  description?: string;
  tags?: string[];
  project?: string;
  confluence_space?: string;
  git_branch?: string;
  git_tag?: string;
}

/* ============ Code Onboard Types ============ */

export interface OnboardParams {
  repo?: string;
  path?: string;
  repo_slug?: string;
  domain?: string;
  kg?: boolean;
  extract_entities?: boolean;
  use_domain_skills?: boolean;
  link_kg?: boolean;
  graphify?: boolean;
  agent?: boolean;
  code_assist_tool?: string;
  okf_enrich?: boolean;
  okf_no_confluence?: boolean;
  okf_model?: string;
}

export interface OKFEnrichParams {
  domain: string;
  source?: "code" | "confluence" | "both";
  code_source?: "auto" | "graphify" | "analyze";
  generate_graphs?: boolean;
  no_confluence?: boolean;
  model?: string;
  dry_run?: boolean;
}

/* ============ Eval Types ============ */

export interface EvalConfigInfo {
  name: string;
  dataset: string;
  metrics: string[];
  framework: string;
  judge: string;
  llm_model?: string;
  description: string;
  created?: string;
  updated?: string;
}

export interface EvalDatasetInfo {
  name: string;
  versions: number[];
  latest?: number;
}

export interface EvalRunInfo {
  eval_id: string;
  eval_name: string;
  agent: string;
  dataset: string;
  dataset_version?: number;
  framework: string;
  judge: string;
  metrics: string[];
  timestamp: string;
  num_rows: number;
  aggregate: Record<string, number>;
  overall_score: number;
}

export interface EvalMetricInfo {
  name: string;
  kind: string;
  description: string;
}

export interface CreateEvalConfigBody {
  name: string;
  dataset: string;
  metrics: string[];
  framework?: string;
  judge?: string;
  llm_model?: string;
  description?: string;
  force?: boolean;
}

/* ============ Run History Types ============ */

export interface RunInfo {
  id: string;
  kind: string;
  label: string;
  command: string;
  status: string;
  exit_code?: number;
  created_at: string;
  completed_at?: string;
  line_count: number;
}

export interface RunDetail extends RunInfo {
  lines: string[];
}

export interface ValidationResult {
  valid: boolean;
  message: string;
  level: string;
}

/* ============ Terminal Types ============ */

export interface TerminalSession {
  id: string;
  title: string;
  alive: boolean;
  created_at: string;
}

/* ============ Chat Types ============ */

export interface ChatSessionInfo {
  id: string;
  agent_name: string;
  created_at: string;
  message_count?: number;
}

export type ChatStreamEventType =
  | "thinking_start"
  | "tool_call"
  | "tool_result"
  | "thinking_end"
  | "agent_response"
  | "agent_response_end"
  | "error";

export interface ChatStreamEvent {
  type: ChatStreamEventType;
  data: Record<string, any>;
}

/* ============ Agent Project Types ============ */

export interface ProjectValidation {
  path_exists?: boolean;
  has_src?: boolean;
  has_pyproject?: boolean;
  has_env?: boolean;
  has_domain_context?: boolean;
  has_persona_skills?: boolean;
  has_mcp_clients?: boolean | null;
  has_sprint_manager?: boolean | null;
  has_standup_generator?: boolean | null;
  has_domain_loader?: boolean | null;
  has_watcher?: boolean | null;
  has_reviewer?: boolean | null;
  score: number;
  total: number;
  [check: string]: boolean | number | null | undefined;
}

export interface AgentProject {
  name: string;
  path: string;
  framework?: string;
  use_case?: string;
  tools: string[];
  agent_type: string;
  created_at?: string;
  domain?: string;
  validation?: ProjectValidation;
}

/* ============ CLI Setup Types ============ */

export interface SetupItem {
  key:
    | "workspaces"
    | "vertex_ai"
    | "neo4j"
    | "devin"
    | "jira"
    | "bitbucket"
    | "confluence"
    | string;
  label: string;
  configured: boolean;
  required: boolean;
  detail: string;
  fix_hint: string;
}

export interface SetupStatus {
  cli_available: boolean;
  cli_version: string;
  ready: boolean;
  items: SetupItem[];
}

export type DoctorStatus = "ok" | "warn" | "fail" | "skip";
export interface DoctorCheck {
  group: string;
  name: string;
  status: DoctorStatus;
  detail: string;
  fix: string;
}
export interface DoctorSection {
  name: string;
  required: boolean;
  results: DoctorCheck[];
}
export interface DoctorReport {
  healthy: boolean;
  sections: DoctorSection[];
  summary: { ok: number; warn: number; fail: number; skip: number; total: number };
}

/* ============ API Client ============ */

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /* ---- Agents ---- */
  async listAgents(): Promise<AgentInfo[]> {
    return this.request("/agents");
  }

  async getAgent(name: string): Promise<AgentInfo> {
    return this.request(`/agents/${name}`);
  }

  async startAgent(
    name: string,
    data: { path: string; review_mode?: string; poll_interval?: number }
  ): Promise<{ success: boolean; message: string; agent?: AgentInfo }> {
    return this.request(`/agents/${name}/start`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async stopAgent(
    name: string
  ): Promise<{ success: boolean; message: string }> {
    return this.request(`/agents/${name}/stop`, {
      method: "POST",
    });
  }

  async testAgent(
    path: string,
    message: string
  ): Promise<{ ok: boolean; response?: string; error?: string }> {
    return this.request(`/agents/test`, {
      method: "POST",
      body: JSON.stringify({ path, message }),
    });
  }

  async getAgentEvalSpec(
    path: string
  ): Promise<{ spec: string; module: string; src: string }> {
    return this.request(`/agents/eval-spec?path=${encodeURIComponent(path)}`);
  }

  /* ---- MCP Servers ---- */
  async listMCPServers(): Promise<MCPServerInfo[]> {
    return this.request("/mcp/servers");
  }

  /** Docker availability + the bundled MCP stack's per-service container status. */
  async getDockerMcpStatus(): Promise<DockerMcpStatus> {
    return this.request("/mcp/docker");
  }

  async startMCPServer(name: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/mcp/servers/${encodeURIComponent(name)}/start`, { method: "POST" });
  }

  async stopMCPServer(name: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/mcp/servers/${encodeURIComponent(name)}/stop`, { method: "POST" });
  }

  async addMCPServer(body: MCPServerUpsert): Promise<MCPServerInfo> {
    return this.request("/mcp/servers", { method: "POST", body: JSON.stringify(body) });
  }

  async updateMCPServer(name: string, body: MCPServerUpsert): Promise<MCPServerInfo> {
    return this.request(`/mcp/servers/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  async deleteMCPServer(name: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/mcp/servers/${encodeURIComponent(name)}`, { method: "DELETE" });
  }

  /* ---- Activity ---- */
  async listActivity(params?: {
    command?: string;
    subcommand?: string;
    status?: string;
    source?: string;
    actor?: string;
    entity_type?: string;
    limit?: number;
  }): Promise<ActivityEntry[]> {
    const query = new URLSearchParams();
    if (params?.command) query.append("command", params.command);
    if (params?.subcommand) query.append("subcommand", params.subcommand);
    if (params?.status) query.append("status", params.status);
    if (params?.source) query.append("source", params.source);
    if (params?.actor) query.append("actor", params.actor);
    if (params?.entity_type) query.append("entity_type", params.entity_type);
    if (params?.limit) query.append("limit", params.limit.toString());
    return this.request(`/activity${query.toString() ? "?" + query.toString() : ""}`);
  }

  /* ---- Overview ---- */
  async getOverview(): Promise<OverviewData> {
    return this.request("/overview");
  }

  /* ---- Deployments ---- */
  async listDeployments(): Promise<Deployment[]> {
    return this.request("/deployments");
  }

  async getDeployment(deploymentId: string): Promise<Deployment> {
    return this.request(`/deployments/${deploymentId}`);
  }

  async createDeployment(data: {
    agent_name: string;
    target: string;
    environment: string;
    max_instances: number;
  }): Promise<{ success: boolean; message: string; deployment?: Deployment }> {
    return this.request("/deployments", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateDeployment(
    deploymentId: string,
    data: { status: string }
  ): Promise<{ success: boolean; message: string; deployment?: Deployment }> {
    return this.request(`/deployments/${deploymentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteDeployment(
    deploymentId: string
  ): Promise<{ success: boolean; message: string }> {
    return this.request(`/deployments/${deploymentId}`, {
      method: "DELETE",
    });
  }

  async rollbackDeployment(
    deploymentId: string,
    targetVersion: string
  ): Promise<{ success: boolean; message: string; deployment?: Deployment }> {
    return this.request(`/deployments/${deploymentId}/rollback`, {
      method: "POST",
      body: JSON.stringify({ target_version: targetVersion }),
    });
  }

  async getDeploymentLogs(deploymentId: string, limit?: number): Promise<any[]> {
    const query = new URLSearchParams();
    if (limit) query.append("limit", limit.toString());
    return this.request(
      `/deployments/${deploymentId}/logs${
        query.toString() ? "?" + query.toString() : ""
      }`
    );
  }

  /* ---- KG Context ---- */
  async getKGProducts(): Promise<ProductKGSummary[]> {
    return this.request("/kg/products");
  }

  async getKGDomainLinks(domain: string, limit = 200): Promise<KGLinkRow[]> {
    return this.request(`/kg/${domain}/links?limit=${limit}`);
  }

  async getKGDomainGaps(domain: string): Promise<KGGapRow[]> {
    return this.request(`/kg/${domain}/gaps`);
  }

  async getKGNodeNeighborhood(domain: string, nodeId: string): Promise<KGNeighborhood> {
    return this.request(`/kg/${domain}/graph/${encodeURIComponent(nodeId)}`);
  }

  /* ---- KG Ingest ---- */
  async listKGIngestJobs(params?: { status?: string; limit?: number }): Promise<IngestJobInfo[]> {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.limit) q.append("limit", params.limit.toString());
    return this.request(`/kg/ingest/jobs${q.toString() ? "?" + q.toString() : ""}`);
  }

  async getKGIngestJob(jobId: string): Promise<IngestJobInfo> {
    return this.request(`/kg/ingest/jobs/${jobId}`);
  }

  async listIngestableDomains(): Promise<IngestableDomain[]> {
    return this.request("/kg/ingest/domains");
  }

  /** Build an SSE URL for `keel kg ingest submit ...`. */
  kgIngestStreamUrl(params: IngestSubmitParams): string {
    const q = new URLSearchParams();
    if (params.domain) q.append("domain", params.domain);
    if (params.product) q.append("product", params.product);
    if (params.path) q.append("path", params.path);
    if (params.source) q.append("source", params.source);
    if (params.format) q.append("format", params.format);
    if (params.provider) q.append("provider", params.provider);
    if (params.workspace) q.append("workspace", params.workspace);
    if (params.depth) q.append("depth", params.depth.toString());
    if (params.top) q.append("top", params.top.toString());
    return this.streamUrl(`/kg/ingest/submit/stream?${q.toString()}`);
  }

  /* ---- OKF Bundles ---- */
  async listOKFBundles(): Promise<OKFBundleInfo[]> {
    return this.request("/kg/okf/bundles");
  }

  async getOKFBundle(domain: string, source: "authored" | "export" = "export"): Promise<OKFBundleDetail> {
    return this.request(`/kg/okf/bundles/${encodeURIComponent(domain)}?source=${source}`);
  }

  /** Canonical → Devin projection status (drift + provenance); local read, no Devin call. */
  async getOKFProjection(domain: string, source: "authored" | "export" = "export"): Promise<OKFProjectionStatus> {
    return this.request(`/kg/okf/projection/${encodeURIComponent(domain)}?source=${source}`);
  }

  /** Build an SSE URL for `keel kg okf export ...` (no reindex). */
  okfExportStreamUrl(params: OKFExportParams): string {
    const q = new URLSearchParams();
    q.append("domain", params.domain);
    if (params.product) q.append("product", params.product);
    q.append("mint_freqs", String(params.mint_freqs ?? true));
    return this.streamUrl(`/kg/okf/export/stream?${q.toString()}`);
  }

  /** Whether the backend has a Devin API key (gates live push). */
  async getOKFDevinStatus(): Promise<OKFDevinStatus> {
    return this.request("/kg/okf/devin/status");
  }

  /** Build an SSE URL for `keel kg okf push-devin ...`. */
  okfDevinPushStreamUrl(params: OKFDevinPushParams): string {
    const q = new URLSearchParams();
    q.append("domain", params.domain);
    q.append("source", params.source ?? "export");
    q.append("types", params.types ?? "FREQ,Requirement");
    q.append("dry_run", String(params.dry_run ?? true));
    return this.streamUrl(`/kg/okf/devin/push/stream?${q.toString()}`);
  }

  /** List all Devin Knowledge entries + folders. */
  async listDevinKnowledge(): Promise<DevinKnowledgeList> {
    return this.request("/kg/okf/devin/knowledge");
  }

  /** Delete a single Devin Knowledge entry. */
  async deleteDevinKnowledge(noteId: string): Promise<{ deleted: string }> {
    return this.request(`/kg/okf/devin/knowledge/${encodeURIComponent(noteId)}`, {
      method: "DELETE",
    });
  }

  /** Move a Devin Knowledge entry to a folder (empty folderId = root). */
  async moveDevinKnowledge(noteId: string, folderId?: string): Promise<{ moved: string }> {
    const q = new URLSearchParams();
    if (folderId) q.append("folder_id", folderId);
    return this.request(`/kg/okf/devin/knowledge/${encodeURIComponent(noteId)}/move?${q.toString()}`, {
      method: "POST",
    });
  }

  /** Partial update of a Devin Knowledge entry (trigger only, repo, body, or all). */
  async updateDevinKnowledge(noteId: string, fields: DevinKnowledgeUpdate): Promise<{ updated: string }> {
    return this.request(`/kg/okf/devin/knowledge/${encodeURIComponent(noteId)}`, {
      method: "PUT",
      body: JSON.stringify(fields),
    });
  }

  /** Delete multiple Devin Knowledge entries at once. */
  async bulkDeleteDevinKnowledge(ids: string[]): Promise<{ deleted: string[]; failed: [string, string][] }> {
    return this.request(`/kg/okf/devin/knowledge/bulk-delete`, {
      method: "POST",
      body: JSON.stringify({ ids }),
    });
  }

  /* ---- Data Sources ---- */
  async listDataSources(): Promise<DataSourceInfo[]> {
    return this.request("/data/sources");
  }

  async validateDataLocation(sourceType: string, location: string): Promise<ValidationResult> {
    const q = new URLSearchParams({ source_type: sourceType, location });
    return this.request(`/data/validate?${q.toString()}`);
  }

  async createDataSource(body: CreateDataSourceBody): Promise<{ success: boolean; output: string }> {
    return this.request("/data/sources", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async deleteDataSource(name: string): Promise<{ success: boolean; output: string }> {
    return this.request(`/data/sources/${encodeURIComponent(name)}`, { method: "DELETE" });
  }

  /* ---- CLI Setup ---- */
  /** Report which `keel init` steps are done (drives sidebar + banners). */
  async getSetupStatus(): Promise<SetupStatus> {
    return this.request("/setup/status");
  }

  /** Structured `keel doctor` diagnostics — powers the setup wizard health panel. */
  async getDoctorReport(probe = false): Promise<DoctorReport> {
    return this.request(`/setup/doctor${probe ? "?probe=true" : ""}`);
  }

  setupWorkspaceStreamUrl(code: string, docs: string): string {
    const q = new URLSearchParams({ code, docs });
    return this.streamUrl(`/setup/init/workspace/stream?${q.toString()}`);
  }

  setupVertexStreamUrl(params: { project_id: string; location?: string; model?: string }): string {
    const q = new URLSearchParams({ project_id: params.project_id });
    if (params.location) q.append("location", params.location);
    if (params.model) q.append("model", params.model);
    return this.streamUrl(`/setup/init/vertex/stream?${q.toString()}`);
  }

  setupNeo4jStreamUrl(params: { uri?: string; username?: string; password: string }): string {
    const q = new URLSearchParams({ password: params.password });
    if (params.uri) q.append("uri", params.uri);
    if (params.username) q.append("username", params.username);
    return this.streamUrl(`/setup/init/neo4j/stream?${q.toString()}`);
  }

  /** Persist a Jira/Bitbucket/Confluence URL + token to ~/.keel/.env via the CLI. */
  setupIntegrationStreamUrl(
    kind: "jira" | "bitbucket" | "confluence",
    url: string,
    token: string
  ): string {
    const q = new URLSearchParams({ url, token });
    return this.streamUrl(`/setup/init/integration/${kind}/stream?${q.toString()}`);
  }

  setupDevinStreamUrl(apiKey: string): string {
    const q = new URLSearchParams({ api_key: apiKey });
    return this.streamUrl(`/setup/init/devin/stream?${q.toString()}`);
  }

  setupBuiltinModelStreamUrl(force = false): string {
    const q = new URLSearchParams(force ? { force: "true" } : {});
    return this.streamUrl(`/setup/init/builtin-model/stream?${q.toString()}`);
  }

  setupGleanStreamUrl(params: {
    url: string;
    mode: "token" | "sso";
    token?: string;
    issuer?: string;
    client_id?: string;
    client_secret?: string;
    scope?: string;
  }): string {
    const q = new URLSearchParams({ url: params.url, mode: params.mode });
    if (params.token) q.append("token", params.token);
    if (params.issuer) q.append("issuer", params.issuer);
    if (params.client_id) q.append("client_id", params.client_id);
    if (params.client_secret) q.append("client_secret", params.client_secret);
    if (params.scope) q.append("scope", params.scope);
    return this.streamUrl(`/setup/init/glean/stream?${q.toString()}`);
  }

  /* ---- Code Onboard ---- */
  codeOnboardStreamUrl(params: OnboardParams): string {
    const q = new URLSearchParams();
    if (params.repo) q.append("repo", params.repo);
    if (params.path) q.append("path", params.path);
    if (params.repo_slug) q.append("repo_slug", params.repo_slug);
    if (params.domain) q.append("domain", params.domain);
    if (params.kg) q.append("kg", "true");
    if (params.extract_entities) q.append("extract_entities", "true");
    if (params.use_domain_skills) q.append("use_domain_skills", "true");
    if (params.link_kg) q.append("link_kg", "true");
    if (params.graphify) q.append("graphify", "true");
    if (params.agent) q.append("agent", "true");
    if (params.code_assist_tool) q.append("code_assist_tool", params.code_assist_tool);
    if (params.okf_enrich) q.append("okf_enrich", "true");
    if (params.okf_no_confluence) q.append("okf_no_confluence", "true");
    if (params.okf_model) q.append("okf_model", params.okf_model);
    return this.streamUrl(`/code/onboard/stream?${q.toString()}`);
  }

  /** Build an SSE URL for `keel kg okf enrich ...` (graphify structural + Confluence). */
  okfEnrichStreamUrl(params: OKFEnrichParams): string {
    const q = new URLSearchParams();
    q.append("domain", params.domain);
    if (params.source) q.append("source", params.source);
    if (params.code_source) q.append("code_source", params.code_source);
    if (params.generate_graphs === false) q.append("generate_graphs", "false");
    if (params.no_confluence) q.append("no_confluence", "true");
    if (params.model) q.append("model", params.model);
    if (params.dry_run) q.append("dry_run", "true");
    return this.streamUrl(`/kg/okf/enrich/stream?${q.toString()}`);
  }

  /* ---- Eval ---- */
  async listEvalFrameworks(): Promise<string[]> {
    return this.request("/eval/frameworks");
  }

  async listEvalConfigs(): Promise<EvalConfigInfo[]> {
    return this.request("/eval/configs");
  }

  async listEvalDatasets(): Promise<EvalDatasetInfo[]> {
    return this.request("/eval/datasets");
  }

  async listEvalRuns(evalName?: string): Promise<EvalRunInfo[]> {
    const q = evalName ? `?eval_name=${encodeURIComponent(evalName)}` : "";
    return this.request(`/eval/runs${q}`);
  }

  async listEvalMetrics(): Promise<EvalMetricInfo[]> {
    return this.request("/eval/metrics");
  }

  async createEvalConfig(body: CreateEvalConfigBody): Promise<{ success: boolean; output: string }> {
    return this.request("/eval/configs", { method: "POST", body: JSON.stringify(body) });
  }

  async evalReportExists(evalName: string): Promise<{ exists: boolean }> {
    return this.request(`/eval/report/exists?eval_name=${encodeURIComponent(evalName)}`);
  }

  evalReportViewUrl(evalName: string): string {
    return this.streamUrl(`/eval/report/view?eval_name=${encodeURIComponent(evalName)}`);
  }

  evalRunAgentStreamUrl(agent: string, evalName: string, batch = 5, projectPath?: string): string {
    const q = new URLSearchParams({ agent, eval_name: evalName, batch: batch.toString() });
    if (projectPath) q.append("project_path", projectPath);
    return this.streamUrl(`/eval/run-agent/stream?${q.toString()}`);
  }

  evalCompareStreamUrl(evalName: string, compareVersions = false): string {
    const q = new URLSearchParams({ eval_name: evalName });
    if (compareVersions) q.append("compare_versions", "true");
    return this.streamUrl(`/eval/compare/stream?${q.toString()}`);
  }

  evalReportStreamUrl(evalName: string): string {
    return this.streamUrl(`/eval/report/stream?eval_name=${encodeURIComponent(evalName)}`);
  }

  /* ---- Generic CLI Runner ---- */
  async listCliGroups(): Promise<string[]> {
    return this.request("/cli/groups");
  }

  async listCliBlocked(): Promise<string[]> {
    return this.request("/cli/blocked");
  }

  cliRunStreamUrl(command: string, allowDestructive = false): string {
    const q = new URLSearchParams({ command });
    if (allowDestructive) q.append("allow_destructive", "true");
    return this.streamUrl(`/cli/run/stream?${q.toString()}`);
  }

  /* ---- Run History ---- */
  async listRunHistory(kind?: string, limit = 50): Promise<RunInfo[]> {
    const q = new URLSearchParams();
    if (kind) q.append("kind", kind);
    q.append("limit", limit.toString());
    return this.request(`/runs?${q.toString()}`);
  }

  async getRunDetail(runId: string): Promise<RunDetail> {
    return this.request(`/runs/${runId}`);
  }

  /* ---- Terminal Sessions ---- */
  async listTerminalSessions(): Promise<TerminalSession[]> {
    return this.request("/terminal/sessions");
  }

  async createTerminalSession(data: {
    title: string;
  }): Promise<TerminalSession> {
    return this.request("/terminal/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async killTerminalSession(id: string): Promise<{ success: boolean }> {
    return this.request(`/terminal/sessions/${id}`, {
      method: "DELETE",
    });
  }

  /* ---- Domain Onboarding ---- */
  async listProducts(): Promise<ProductInfo[]> {
    return this.request("/domains/products");
  }

  async createProduct(body: CreateProductBody): Promise<ProductInfo> {
    return this.request("/domains/products", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async updateProduct(name: string, body: UpdateProductBody): Promise<ProductInfo> {
    return this.request(`/domains/products/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async deleteProduct(
    name: string,
    opts?: { cascade?: boolean; wipeMeta?: boolean }
  ): Promise<{ success: boolean; message: string }> {
    const q = new URLSearchParams();
    if (opts?.cascade) q.append("cascade", "true");
    if (opts?.wipeMeta) q.append("wipe_meta", "true");
    const qs = q.toString();
    return this.request(
      `/domains/products/${encodeURIComponent(name)}${qs ? "?" + qs : ""}`,
      { method: "DELETE" }
    );
  }

  async listDomains(product?: string): Promise<DomainInfo[]> {
    const q = product ? `?product=${encodeURIComponent(product)}` : "";
    return this.request(`/domains${q}`);
  }

  /* ---- Persona-tiered workspaces ---- */

  /** List tracked persona workspaces (optionally by tier). */
  async listWorkspaces(tier?: string): Promise<WorkspaceInfo[]> {
    const q = tier ? `?tier=${encodeURIComponent(tier)}` : "";
    return this.request(`/workspaces${q}`);
  }

  /** Editor tools offered for Open-in-IDE + the org default's editor key so
   *  the UI can flag it as missing when it's not installed. */
  async listEditors(): Promise<{ editors: string[]; default?: string | null }> {
    return this.request(`/workspaces/editors`);
  }

  /** Resolve the folder a persona should open + whether an action is needed. */
  async resolveWorkspaceTarget(params: {
    persona: string;
    product?: string;
    domain?: string;
    repo?: string;
    drift?: boolean;
  }): Promise<WorkspaceTarget> {
    const q = new URLSearchParams({ persona: params.persona });
    if (params.product) q.append("product", params.product);
    if (params.domain) q.append("domain", params.domain);
    if (params.repo) q.append("repo", params.repo);
    if (params.drift) q.append("drift", "true");
    return this.request(`/workspaces/target?${q.toString()}`);
  }

  /** Template drift for a domain meta-repo (slow: re-renders the template). */
  async getTemplateStatus(domain: string, meta?: string): Promise<TemplateStatus> {
    const q = new URLSearchParams({ domain });
    if (meta) q.append("meta", meta);
    return this.request(`/workspaces/template/status?${q.toString()}`);
  }

  /** Files the shared template overlay provides (i.e. promoted content). */
  async getTemplateOverlay(): Promise<TemplateOverlayInfo> {
    return this.request(`/workspaces/template/overlay`);
  }

  /** Local files a domain could contribute back to the template. */
  async getTemplatePromotable(domain: string): Promise<TemplatePromotable> {
    return this.request(`/workspaces/template/promotable?domain=${encodeURIComponent(domain)}`);
  }

  /** SSE: `keel domain template upgrade` — pull template updates down.
   *  Previews unless `apply`. */
  templateUpgradeStreamUrl(
    domain: string,
    opts?: { apply?: boolean; prune?: boolean; force?: boolean },
  ): string {
    const q = new URLSearchParams({ domain });
    if (opts?.apply) q.append("apply", "true");
    if (opts?.prune) q.append("prune", "true");
    if (opts?.force) q.append("force", "true");
    return this.streamUrl(`/workspaces/template/upgrade/stream?${q.toString()}`);
  }

  /** SSE: `keel domain template promote` — push local improvements up.
   *  Previews unless `apply`; publishing needs `push`. */
  templatePromoteStreamUrl(
    domain: string,
    files: string[],
    opts?: { apply?: boolean; push?: boolean; allowUnreviewed?: boolean },
  ): string {
    const q = new URLSearchParams({ domain });
    files.forEach((f) => q.append("file", f));
    if (opts?.apply) q.append("apply", "true");
    if (opts?.push) q.append("push", "true");
    if (opts?.allowUnreviewed) q.append("allow_unreviewed", "true");
    return this.streamUrl(`/workspaces/template/promote/stream?${q.toString()}`);
  }

  /** Launch a local editor/agent (devin/windsurf/cursor/code) at a folder. */
  async openInIde(path: string, editor?: string): Promise<OpenIdeResult> {
    return this.request(`/workspaces/open-ide`, {
      method: "POST",
      body: JSON.stringify({ path, editor }),
    });
  }

  /** SSE: `keel domain sync` (tech-lead domain-tier assembly). */
  workspaceSyncStreamUrl(domain: string, opts?: { persona?: string; graphify?: boolean; editor?: string }): string {
    const q = new URLSearchParams({ domain });
    if (opts?.persona) q.append("persona", opts.persona);
    q.append("graphify", String(opts?.graphify ?? true));
    if (opts?.editor) q.append("editor", opts.editor);
    return this.streamUrl(`/workspaces/sync/stream?${q.toString()}`);
  }

  /** SSE: `keel workspace open` (dev repo-tier worktree). */
  workspaceOpenStreamUrl(domain: string, repo: string, opts?: { persona?: string; graphify?: boolean; editor?: string }): string {
    const q = new URLSearchParams({ domain, repo });
    if (opts?.persona) q.append("persona", opts.persona);
    q.append("graphify", String(opts?.graphify ?? false));
    if (opts?.editor) q.append("editor", opts.editor);
    return this.streamUrl(`/workspaces/open/stream?${q.toString()}`);
  }

  async getDomain(slug: string): Promise<DomainDetail> {
    return this.request(`/domains/${slug}`);
  }

  /** Resolve the domain context-repo & meta-repo paths (+ existence) for Open-in-IDE. */
  async getScaffoldPaths(slug: string): Promise<ScaffoldPaths> {
    return this.request(`/domains/${slug}/scaffold-paths`);
  }

  async createDomain(body: CreateDomainBody): Promise<DomainDetail> {
    return this.request("/domains", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async updateDomain(slug: string, body: Partial<CreateDomainBody>): Promise<DomainDetail> {
    return this.request(`/domains/${slug}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async deleteDomain(slug: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/domains/${slug}`, { method: "DELETE" });
  }

  async getBitbucketCandidates(slug: string, filter?: string): Promise<BitbucketRepoCandidate[]> {
    const q = filter ? `?filter=${encodeURIComponent(filter)}` : "";
    return this.request(`/domains/${slug}/bitbucket-repos${q}`);
  }

  async linkRepo(
    slug: string,
    body: { repo_slug: string; repo_name?: string; clone_url?: string }
  ): Promise<{ success: boolean; message: string }> {
    return this.request(`/domains/${slug}/repos`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async unlinkRepo(slug: string, repoSlug: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/domains/${slug}/repos/${repoSlug}`, { method: "DELETE" });
  }

  async getConfluenceCandidates(slug: string, filter?: string): Promise<ConfluencePageCandidate[]> {
    const q = filter ? `?filter=${encodeURIComponent(filter)}` : "";
    return this.request(`/domains/${slug}/confluence-pages${q}`);
  }

  async addDoc(
    slug: string,
    body: { source_page_id: string; source_space_key?: string; title?: string; source_version?: number }
  ): Promise<{ success: boolean; message: string }> {
    return this.request(`/domains/${slug}/docs`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async removeDoc(slug: string, pageId: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/domains/${slug}/docs/${pageId}`, { method: "DELETE" });
  }

  /* ---- Persona Skills (review + regenerate) ---- */

  /** Review: list persona skills generated into a domain meta-repo. */
  async listGeneratedPersonas(slug: string): Promise<GeneratedPersonaInfo[]> {
    return this.request(`/domains/${slug}/personas`);
  }

  /** Review: read one generated persona's SKILL.md content. */
  async getPersonaContent(slug: string, personaId: string): Promise<{ id: string; content: string }> {
    return this.request(`/domains/${slug}/personas/${encodeURIComponent(personaId)}`);
  }

  /** Repo/domain-level regenerate (all users). */
  regenPersonasStreamUrl(slug: string, opts?: { personas?: string[]; enrich?: boolean }): string {
    const q = new URLSearchParams();
    for (const p of opts?.personas ?? []) q.append("persona", p);
    if (opts?.enrich) q.append("enrich", "true");
    const qs = q.toString();
    return this.streamUrl(`/domains/${slug}/regen-personas/stream${qs ? "?" + qs : ""}`);
  }

  /** Effective persona catalog for a product (built-ins + customs). */
  async listProductPersonas(name: string): Promise<PersonaCatalogInfo[]> {
    return this.request(`/domains/products/${encodeURIComponent(name)}/personas`);
  }

  /** Admin: add (or replace) a product-specific persona. */
  async addProductPersona(name: string, body: AddPersonaBody): Promise<PersonaCatalogInfo> {
    return this.request(`/domains/products/${encodeURIComponent(name)}/personas`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /** Admin: remove a product-specific persona. */
  async removeProductPersona(name: string, personaId: string): Promise<{ success: boolean; message: string }> {
    return this.request(
      `/domains/products/${encodeURIComponent(name)}/personas/${encodeURIComponent(personaId)}`,
      { method: "DELETE" }
    );
  }

  /** Admin: regenerate personas across all domains in a product (SSE). */
  productRegenPersonasStreamUrl(name: string, enrich = false): string {
    const q = new URLSearchParams();
    if (enrich) q.append("enrich", "true");
    const qs = q.toString();
    return this.streamUrl(
      `/domains/products/${encodeURIComponent(name)}/regen-personas/stream${qs ? "?" + qs : ""}`
    );
  }

  /* ---- Product Meta-Repo / Governance / Exceptions ---- */

  /** Build an SSE URL for `keel product init-meta <name>`. */
  productInitMetaStreamUrl(
    name: string,
    orgMethodology?: string,
    force?: boolean
  ): string {
    const q = new URLSearchParams();
    if (orgMethodology) q.append("org_methodology", orgMethodology);
    if (force) q.append("force", "true");
    const qs = q.toString();
    return this.streamUrl(
      `/domains/products/${encodeURIComponent(name)}/init-meta/stream${qs ? "?" + qs : ""}`
    );
  }

  async getProductGovernance(name: string): Promise<GovernanceInfo> {
    return this.request(`/domains/products/${encodeURIComponent(name)}/governance`);
  }

  async listProductExceptions(name: string): Promise<ExceptionInfo[]> {
    return this.request(`/domains/products/${encodeURIComponent(name)}/exceptions`);
  }

  async addProductException(name: string, body: AddExceptionBody): Promise<ExceptionInfo> {
    return this.request(`/domains/products/${encodeURIComponent(name)}/exceptions`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /* ---- Integrations ---- */
  async getIntegrations(): Promise<IntegrationsResponse> {
    return this.request("/integrations/status");
  }

  /* ---- Jira Work Items ---- */
  async getJiraStatus(): Promise<JiraStatus> {
    return this.request("/jira/status");
  }

  /** Issues assigned to the current user across onboarded domain projects. */
  async getMyJiraIssues(status?: string): Promise<MyJiraIssuesResponse> {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.request(`/jira/my-issues${q}`);
  }

  /** Assemble the governed Task Contract for a Jira issue ("Start work"). */
  async getJiraContract(key: string): Promise<TaskContract> {
    return this.request(`/jira/issues/${encodeURIComponent(key)}/contract`);
  }

  /* ---- Devin ---- */
  async getDevinStatus(): Promise<DevinStatus> {
    return this.request("/devin/status");
  }

  async listDevinSessions(): Promise<DevinSession[]> {
    return this.request("/devin/sessions");
  }

  async createDevinSession(body: CreateDevinSessionRequest): Promise<CreateDevinSessionResponse> {
    return this.request("/devin/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /* ---- Auth (identity resolved by the configured provider) ---- */
  async getMe(): Promise<AuthMe> {
    return this.request("/auth/me");
  }

  /** The RBAC model — roles, permissions, personas (mirrors `keel auth roles`). */
  async getRbacModel(): Promise<RbacModel> {
    return this.request("/auth/roles");
  }

  /** Whether the current principal has a permission (mirrors `keel auth check`). */
  async checkPermission(permission: string): Promise<PermissionCheck> {
    return this.request(`/auth/check?permission=${encodeURIComponent(permission)}`);
  }

  /* ---- Admin (branding + nav visibility) ---- */
  async getBuildGovernance(domain?: string): Promise<BuildGovernanceInfo> {
    const q = domain ? `?domain=${encodeURIComponent(domain)}` : "";
    return this.request(`/execution/governance${q}`);
  }

  async getAdminSettings(): Promise<AdminSettings> {
    return this.request("/admin/settings");
  }

  async updateAdminSettings(body: AdminSettingsUpdate): Promise<AdminSettings> {
    return this.request("/admin/settings", { method: "PUT", body: JSON.stringify(body) });
  }

  async getRoleAssignments(): Promise<RoleAssignments> {
    return this.request("/admin/roles");
  }

  async getResetPreview(): Promise<ResetPreview> {
    return this.request("/admin/reset/preview");
  }

  async resetPlatform(body: { scopes: string[]; confirm: string }): Promise<ResetResult> {
    return this.request("/admin/reset", { method: "POST", body: JSON.stringify(body) });
  }

  async setRoleAssignment(body: RoleAssignmentUpdate): Promise<RoleAssignments> {
    return this.request("/admin/roles", { method: "PUT", body: JSON.stringify(body) });
  }

  /* ---- Watchers ---- */
  async listTraceSessions(limit = 25): Promise<TraceSessionRef[]> {
    return this.request(`/trace/sessions?limit=${limit}`);
  }
  async getSessionLedger(sessionId: string): Promise<SessionLedger> {
    return this.request(`/trace/sessions/${encodeURIComponent(sessionId)}`);
  }
  async listWatchers(): Promise<WatcherView[]> {
    return this.request("/watchers");
  }
  async listTriggers(): Promise<TriggerInfo[]> {
    return this.request("/watchers/triggers");
  }
  async watchersForAgent(agent: string): Promise<WatcherView[]> {
    return this.request(`/watchers/for-agent/${encodeURIComponent(agent)}`);
  }
  async getWatcher(name: string): Promise<WatcherView> {
    return this.request(`/watchers/${encodeURIComponent(name)}`);
  }
  async createWatcher(spec: WatcherSpec): Promise<WatcherView> {
    return this.request("/watchers", { method: "POST", body: JSON.stringify(spec) });
  }
  async updateWatcher(spec: WatcherSpec): Promise<WatcherView> {
    return this.request(`/watchers/${encodeURIComponent(spec.name)}`, {
      method: "PUT", body: JSON.stringify(spec),
    });
  }
  async deleteWatcher(name: string): Promise<{ deleted: string }> {
    return this.request(`/watchers/${encodeURIComponent(name)}`, { method: "DELETE" });
  }
  async pauseWatcher(name: string): Promise<WatcherView> {
    return this.request(`/watchers/${encodeURIComponent(name)}/pause`, { method: "POST" });
  }
  async resumeWatcher(name: string): Promise<WatcherView> {
    return this.request(`/watchers/${encodeURIComponent(name)}/resume`, { method: "POST" });
  }
  async testRunWatcher(name: string): Promise<TestRunResult> {
    return this.request(`/watchers/${encodeURIComponent(name)}/test-run`, { method: "POST" });
  }

  /* ---- Execution engines (vendor-neutral seam) ---- */
  async listExecutionEngines(): Promise<ExecutionEngineInfo[]> {
    return this.request("/execution/engines");
  }

  /** Render a task's portable, engine-neutral context bundle (preview, no files). */
  async previewPortableContext(body: PortableContextRequest): Promise<PortableContextResult> {
    return this.request("/execution/context/preview", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /** Launch a build session on the selected (or org-default) engine. */
  async launchSession(body: SessionLaunchRequest): Promise<SessionLaunchResult> {
    return this.request("/execution/session", { method: "POST", body: JSON.stringify(body) });
  }

  /** Ask the selected (or org-default) engine about the codebase/domain. */
  async askEngine(body: { prompt: string; domain?: string | null; refs?: string[]; engine?: string | null }): Promise<EngineAskResult> {
    return this.request("/execution/ask", { method: "POST", body: JSON.stringify(body) });
  }

  async getDevinSession(sessionId: string): Promise<DevinSessionDetail> {
    return this.request(`/devin/sessions/${sessionId}`);
  }

  async sendDevinMessage(sessionId: string, message: string): Promise<unknown> {
    return this.request(`/devin/sessions/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  }

  /** Locally-registered per-domain Devin snapshots with meta-repo drift status. */
  async listDevinSnapshots(): Promise<DevinSnapshot[]> {
    return this.request("/devin/snapshots");
  }

  /** Re-verify a single domain's snapshot against its meta-repo. */
  async verifyDevinSnapshot(domain: string): Promise<DevinSnapshot> {
    return this.request(`/devin/snapshots/${encodeURIComponent(domain)}/verify`);
  }

  /* ---- Agent Projects ---- */
  async discoverProjects(workspace?: string): Promise<AgentProject[]> {
    const q = workspace ? `?workspace=${encodeURIComponent(workspace)}` : "";
    return this.request(`/agents/projects${q}`);
  }

  /* ---- Chat ---- */
  async listChatSessions(): Promise<ChatSessionInfo[]> {
    return this.request("/chat/sessions");
  }

  async createChatSession(agentName: string = "keel-assistant"): Promise<ChatSessionInfo> {
    return this.request("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ agent_name: agentName }),
    });
  }

  async deleteChatSession(id: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/chat/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  /** Build a WebSocket URL for the streaming chat endpoint. */
  chatWebSocketUrl(sessionId: string): string {
    const base = this.baseUrl.startsWith("http")
      ? this.baseUrl
      : `${window.location.origin}${this.baseUrl}`;
    return `${base.replace(/^http/, "ws")}/chat/${encodeURIComponent(sessionId)}/stream`;
  }

  /** Build an absolute URL for an SSE streaming endpoint. */
  streamUrl(path: string): string {
    return `${this.baseUrl}${path}`;
  }
}

export interface JiraStatus {
  configured: boolean;
  server_url: string;
  projects: string[];
}

export interface JiraIssue {
  key: string;
  summary: string;
  status: string;
  status_category: string;
  priority: string;
  issuetype: string;
  project: string;
  updated: string;
  created: string;
  labels: string[];
  link: string;
}

export interface MyJiraIssuesResponse {
  configured: boolean;
  projects: string[];
  jql: string;
  total: number;
  issues: JiraIssue[];
  error?: string | null;
}

/* ---- Task Contract (governed "Start work" launcher) ---- */

export interface TaskContract {
  issue: {
    key: string;
    summary: string;
    description: string;
    priority: string;
    issuetype: string;
    project: string;
    labels: string[];
    link: string;
  };
  domain: {
    found: boolean;
    slug?: string | null;
    label?: string | null;
    product?: string | null;
  };
  governance: {
    found: boolean;
    branch_pattern?: string | null;
    require_code_review?: boolean | null;
    min_reviewers?: number | null;
    require_tests?: boolean | null;
    test_coverage_min?: number | null;
    require_ci_gates?: boolean | null;
    gates: string[];
  };
  devin: {
    snapshot_id?: string | null;
    playbook_id?: string | null;
    knowledge_folder?: string | null;
    snapshot_state?: string | null;
    snapshot_detail?: string | null;
  };
  local_workspace: {
    persona: string;
    tier: string;
    path?: string | null;
    exists: boolean;
    ready: boolean;
    needs?: string | null;
    hint: string;
  };
  branch_name: string;
  prompt: string;
  warnings: string[];
  can_launch_local: boolean;
  can_launch_devin: boolean;
}

export const api = new APIClient(API_BASE);
