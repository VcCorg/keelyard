"""Generate Docker files."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig


def generate_docker_files(target_dir: Path, config: TemplateConfig) -> None:
    """Generate Docker files."""
    dockerfile = '''FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

CMD ["python", "src/main.py"]
'''
    (target_dir / "Dockerfile").write_text(dockerfile)
    
    compose = f'''version: "3.8"

services:
  agent:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
'''
    (target_dir / "docker-compose.yml").write_text(compose)
