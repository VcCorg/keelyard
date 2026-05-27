FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org "neo4j-agent-memory[mcp]"

# Neo4j connection (read by CLI via env vars)
ENV NEO4J_URI=bolt://dva-neo4j:7687
ENV NEO4J_USER=neo4j
ENV NEO4J_PASSWORD=password

# MCP server config
ENV MCP_TRANSPORT=sse
ENV MCP_PORT=8130
ENV MCP_HOST=0.0.0.0

EXPOSE 8130

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
  CMD curl --max-time 2 -s http://localhost:8130/sse > /dev/null 2>&1; test $? -eq 28

CMD ["neo4j-agent-memory", "mcp", "serve", \
     "--transport", "sse", \
     "--port", "8130", \
     "--host", "0.0.0.0", \
     "--profile", "extended", \
     "--session-strategy", "per_day"]
