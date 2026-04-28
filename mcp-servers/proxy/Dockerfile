FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install mcp-proxy
RUN pip install --no-cache-dir mcp-proxy

# Copy and install bitbucket MCP server
COPY bitbucket/ /tmp/bitbucket-mcp/
RUN pip install --no-cache-dir /tmp/bitbucket-mcp && rm -rf /tmp/bitbucket-mcp

# Copy and install jira MCP server
COPY jira/ /tmp/jira-mcp/
RUN pip install --no-cache-dir /tmp/jira-mcp && rm -rf /tmp/jira-mcp

# Copy named-server config
COPY proxy/mcp-servers.json ./

EXPOSE 9091

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl --max-time 2 -s http://localhost:9091/sse > /dev/null 2>&1; test $? -eq 28

CMD ["mcp-proxy", "--pass-environment", "--port", "9091", "--host", "0.0.0.0", "--named-server-config", "mcp-servers.json"]
