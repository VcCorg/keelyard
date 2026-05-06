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
}

export const api = new APIClient(API_BASE);
