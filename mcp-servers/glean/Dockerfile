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
ENV MCP_PORT=8127
ENV MCP_HOST=0.0.0.0

EXPOSE 8127

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8127/sse || exit 1

CMD ["python", "-m", "glean_mcp.server"]
