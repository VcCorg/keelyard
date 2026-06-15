// API client for Agent Playground dashboard.

const API_BASE = "http://localhost:8000/api";

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
  status: string;
  port?: number;
  healthy: boolean;
  last_check?: string;
}

export interface ActivityEntry {
  id: string;
  command: string;
  subcommand?: string;
  status: string;
  timestamp: string;
  duration_ms?: number;
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
  path?: string;
  source?: string;
  format?: string;
  provider?: string;
  workspace?: string;
  depth?: number;
  top?: number;
}

/* ============ Domain Onboarding Types ============ */

export interface ProductInfo {
  name: string;
  description?: string;
  domain_count: number;
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
  confluence_space?: string;
  confluence_url?: string;
  jira_dashboard?: string;
  tags?: string[];
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

  /* ---- MCP Servers ---- */
  async listMCPServers(): Promise<MCPServerInfo[]> {
    return this.request("/api/mcp/servers");
  }

  /* ---- Activity ---- */
  async listActivity(params?: {
    command?: string;
    limit?: number;
  }): Promise<ActivityEntry[]> {
    const query = new URLSearchParams();
    if (params?.command) query.append("command", params.command);
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

  /** Build an SSE URL for `dva kg ingest submit ...`. */
  kgIngestStreamUrl(params: IngestSubmitParams): string {
    const q = new URLSearchParams();
    if (params.domain) q.append("domain", params.domain);
    if (params.path) q.append("path", params.path);
    if (params.source) q.append("source", params.source);
    if (params.format) q.append("format", params.format);
    if (params.provider) q.append("provider", params.provider);
    if (params.workspace) q.append("workspace", params.workspace);
    if (params.depth) q.append("depth", params.depth.toString());
    if (params.top) q.append("top", params.top.toString());
    return this.streamUrl(`/kg/ingest/submit/stream?${q.toString()}`);
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
    return this.streamUrl(`/code/onboard/stream?${q.toString()}`);
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

  evalRunAgentStreamUrl(agent: string, evalName: string, batch = 5): string {
    const q = new URLSearchParams({ agent, eval_name: evalName, batch: batch.toString() });
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

  async listDomains(product?: string): Promise<DomainInfo[]> {
    const q = product ? `?product=${encodeURIComponent(product)}` : "";
    return this.request(`/domains${q}`);
  }

  async getDomain(slug: string): Promise<DomainDetail> {
    return this.request(`/domains/${slug}`);
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

  /** Build an absolute URL for an SSE streaming endpoint. */
  streamUrl(path: string): string {
    return `${this.baseUrl}${path}`;
  }
}

export const api = new APIClient(API_BASE);
