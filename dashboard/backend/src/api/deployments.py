"""Deployment management API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.deployment_service import (
    Deployment,
    DeploymentConfig,
    DeploymentLog,
    create_deployment,
    list_deployments,
    get_deployment,
    update_deployment,
    delete_deployment,
    rollback_deployment,
    get_deployment_logs,
)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])


class CreateDeploymentRequest(BaseModel):
    """Request to create a new deployment."""
    agent_name: str
    target: str  # "local", "docker", "cloud-run", "kubernetes"
    environment: str = "development"
    max_instances: int = 1


class UpdateDeploymentRequest(BaseModel):
    """Request to update deployment status."""
    status: str  # "running", "stopped", "failed"


class RollbackRequest(BaseModel):
    """Request to rollback a deployment."""
    target_version: str


class DeploymentResponse(BaseModel):
    """Response containing deployment information."""
    success: bool
    message: str
    deployment: Optional[Deployment] = None


@router.get("", response_model=list[Deployment])
async def api_list_deployments():
    """List all deployments."""
    return list_deployments()


@router.post("", response_model=DeploymentResponse)
async def api_create_deployment(req: CreateDeploymentRequest):
    """Create a new deployment for an agent."""
    try:
        deployment = create_deployment(
            agent_name=req.agent_name,
            target=req.target,
            environment=req.environment,
            max_instances=req.max_instances,
        )
        return DeploymentResponse(
            success=True,
            message=f"Deployment '{deployment.id}' created",
            deployment=deployment,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{deployment_id}", response_model=Deployment)
async def api_get_deployment(deployment_id: str):
    """Get a specific deployment."""
    deployment = get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")
    return deployment


@router.patch("/{deployment_id}", response_model=DeploymentResponse)
async def api_update_deployment(deployment_id: str, req: UpdateDeploymentRequest):
    """Update deployment status."""
    deployment = update_deployment(deployment_id, req.status)
    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")

    return DeploymentResponse(
        success=True,
        message=f"Deployment '{deployment_id}' updated to status '{req.status}'",
        deployment=deployment,
    )


@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
async def api_rollback_deployment(deployment_id: str, req: RollbackRequest):
    """Rollback deployment to a previous version."""
    deployment = rollback_deployment(deployment_id, req.target_version)
    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' or version not found")

    return DeploymentResponse(
        success=True,
        message=f"Deployment rolled back to version '{req.target_version}'",
        deployment=deployment,
    )


@router.delete("/{deployment_id}", response_model=DeploymentResponse)
async def api_delete_deployment(deployment_id: str):
    """Delete a deployment."""
    success = delete_deployment(deployment_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")

    return DeploymentResponse(
        success=True,
        message=f"Deployment '{deployment_id}' deleted",
    )


@router.get("/{deployment_id}/logs", response_model=list[DeploymentLog])
async def api_deployment_logs(deployment_id: str, limit: int = 50):
    """Get deployment operation logs."""
    # Verify deployment exists
    deployment = get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")

    return get_deployment_logs(deployment_id, limit)
