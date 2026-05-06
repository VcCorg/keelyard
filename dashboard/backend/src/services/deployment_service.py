"""Deployment service — manages agent deployments across environments."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


DEPLOYMENTS_DIR = Path.home() / ".dva" / "deployments"


class DeploymentConfig(BaseModel):
    """Configuration for a deployment."""
    agent_name: str
    target: str  # "local", "docker", "cloud-run", "kubernetes"
    environment: str = "development"
    max_instances: int = 1
    timeout_seconds: int = 300


class DeploymentMetrics(BaseModel):
    """Metrics for a deployment."""
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    requests_per_min: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    uptime_percent: Optional[float] = None


class DeploymentVersion(BaseModel):
    """A specific version of a deployed agent."""
    version: str
    created_at: str
    status: str  # "active", "inactive", "failed"
    config: DeploymentConfig
    metrics: Optional[DeploymentMetrics] = None


class Deployment(BaseModel):
    """Agent deployment information."""
    id: str
    agent_name: str
    target: str
    environment: str
    status: str  # "running", "stopped", "failed"
    created_at: str
    updated_at: str
    current_version: Optional[str] = None
    replicas: int = 1
    metrics: Optional[DeploymentMetrics] = None
    versions: list[DeploymentVersion] = []


class DeploymentLog(BaseModel):
    """Deployment operation log entry."""
    timestamp: str
    operation: str  # "deploy", "rollback", "scale", "restart"
    status: str  # "success", "failure", "in_progress"
    message: str
    error: Optional[str] = None


def _ensure_deployments_dir():
    """Create deployments directory if it doesn't exist."""
    DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)


def create_deployment(
    agent_name: str,
    target: str,
    environment: str = "development",
    max_instances: int = 1,
) -> Deployment:
    """Create a new deployment for an agent."""
    _ensure_deployments_dir()

    deployment_id = f"{agent_name}-{target}-{environment}"
    config = DeploymentConfig(
        agent_name=agent_name,
        target=target,
        environment=environment,
        max_instances=max_instances,
    )

    now = datetime.utcnow().isoformat()
    version = "1.0.0"

    deployment = Deployment(
        id=deployment_id,
        agent_name=agent_name,
        target=target,
        environment=environment,
        status="stopped",
        created_at=now,
        updated_at=now,
        current_version=version,
        replicas=1,
        versions=[
            DeploymentVersion(
                version=version,
                created_at=now,
                status="inactive",
                config=config,
            )
        ],
    )

    # Save to file
    dep_file = DEPLOYMENTS_DIR / f"{deployment_id}.json"
    with open(dep_file, "w") as f:
        json.dump(deployment.model_dump(), f, indent=2)

    return deployment


def list_deployments() -> list[Deployment]:
    """List all deployments."""
    _ensure_deployments_dir()
    deployments = []

    for dep_file in DEPLOYMENTS_DIR.glob("*.json"):
        try:
            with open(dep_file) as f:
                data = json.load(f)
                deployments.append(Deployment(**data))
        except Exception:
            pass

    return deployments


def get_deployment(deployment_id: str) -> Optional[Deployment]:
    """Get a specific deployment by ID."""
    _ensure_deployments_dir()
    dep_file = DEPLOYMENTS_DIR / f"{deployment_id}.json"

    if dep_file.exists():
        try:
            with open(dep_file) as f:
                data = json.load(f)
                return Deployment(**data)
        except Exception:
            pass

    return None


def update_deployment(deployment_id: str, status: str) -> Optional[Deployment]:
    """Update deployment status."""
    deployment = get_deployment(deployment_id)
    if not deployment:
        return None

    deployment.status = status
    deployment.updated_at = datetime.utcnow().isoformat()

    # Save updated deployment
    dep_file = DEPLOYMENTS_DIR / f"{deployment_id}.json"
    with open(dep_file, "w") as f:
        json.dump(deployment.model_dump(), f, indent=2)

    return deployment


def delete_deployment(deployment_id: str) -> bool:
    """Delete a deployment."""
    _ensure_deployments_dir()
    dep_file = DEPLOYMENTS_DIR / f"{deployment_id}.json"

    if dep_file.exists():
        dep_file.unlink()
        return True

    return False


def rollback_deployment(deployment_id: str, target_version: str) -> Optional[Deployment]:
    """Rollback a deployment to a previous version."""
    deployment = get_deployment(deployment_id)
    if not deployment:
        return None

    # Find target version
    target = None
    for v in deployment.versions:
        if v.version == target_version:
            target = v
            break

    if not target:
        return None

    # Create new version entry marking the rollback
    deployment.current_version = target_version
    deployment.updated_at = datetime.utcnow().isoformat()
    deployment.status = "running"

    # Save updated deployment
    dep_file = DEPLOYMENTS_DIR / f"{deployment_id}.json"
    with open(dep_file, "w") as f:
        json.dump(deployment.model_dump(), f, indent=2)

    return deployment


def get_deployment_logs(deployment_id: str, limit: int = 50) -> list[DeploymentLog]:
    """Get deployment operation logs."""
    # Placeholder for log retrieval
    # In a full implementation, this would read from a database or log file
    return []
