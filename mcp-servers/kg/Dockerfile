FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project files and install dependencies
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Default to SSE transport for Docker
ENV MCP_TRANSPORT=sse
ENV MCP_PORT=8131
ENV MCP_HOST=0.0.0.0

# KG backend defaults (overridden via docker-compose env)
ENV KG_NEO4J_URI=bolt://dva-neo4j:7687
ENV KG_NEO4J_USER=neo4j
ENV KG_LIGHTRAG_URL=http://dva-lightrag:8001
ENV KG_DEFAULT_PROVIDER=lightrag
ENV KG_SOURCE_REGISTRY_PATH=/root/.dva-agentic/config.json

EXPOSE 8131

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8131/sse || exit 1

CMD ["python", "-m", "kg_mcp.server"]
