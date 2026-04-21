FROM python:3.11-slim

WORKDIR /app

# Add /app to Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the MCP server code (KG modules will be mounted at runtime)
COPY src/mcp_server.py /app/src/
COPY src/__init__.py /app/src/

# Copy MCP protocol modules and resources
COPY src/mcp/ /app/src/mcp/
COPY src/resources/ /app/src/resources/
COPY src/prompts/ /app/src/prompts/

# Create directories for runtime mounts
RUN mkdir -p /root/.dva-agentic /app/src/kg

# Expose MCP server port
EXPOSE 8125

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD curl -f http://localhost:8125/health || exit 1

# Start MCP server
CMD ["python", "-m", "uvicorn", "src.mcp_server:app", "--host", "0.0.0.0", "--port", "8125"]
