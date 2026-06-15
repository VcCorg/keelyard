"""Skills API endpoints for DVA Dashboard."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillInfo(BaseModel):
    """Skill information model."""
    name: str
    description: str
    tags: List[str]
    mcp: Optional[Dict[str, Any]] = None
    auto_detect: Optional[Dict[str, Any]] = None


class SkillListResponse(BaseModel):
    """Response model for skills list."""
    skills: List[SkillInfo]
    total: int
    registry_path: Optional[str] = None


class SkillInstallRequest(BaseModel):
    """Request model for skill installation."""
    skill_name: str
    project_path: str


class SkillInstallResponse(BaseModel):
    """Response model for skill installation."""
    success: bool
    message: str
    skill_name: str
    project_path: str


class ProjectSkillsResponse(BaseModel):
    """Response model for project skills."""
    project_path: str
    project_name: str
    installed_skills: List[SkillInfo]
    suggested_skills: List[SkillInfo]
    total_installed: int
    total_suggested: int


@router.get("/list", response_model=SkillListResponse)
async def list_skills(
    registry_path: Optional[str] = Query(None, description="Override skills registry path"),
    tag: Optional[str] = Query(None, description="Filter skills by tag")
):
    """List all available skills from the registry."""
    try:
        # Import here to avoid circular imports
        from agentic_cli.analyzer.matcher import load_registry
        from agentic_cli.commands.code import _ensure_registry, _get_registry_path
    except ImportError as e:
        # agentic_cli not available - return empty list
        return SkillListResponse(
            skills=[],
            total=0,
            registry_path=None
        )

    try:
        # Get registry path
        if registry_path:
            reg_path = Path(registry_path)
            if not reg_path.exists() or not (reg_path / "registry.json").exists():
                raise HTTPException(status_code=404, detail=f"Registry not found at {registry_path}")
        else:
            try:
                reg_path = _ensure_registry()
            except Exception:
                # No registry configured - return empty list
                reg_path = _get_registry_path()
                return SkillListResponse(
                    skills=[],
                    total=0,
                    registry_path=str(reg_path) if reg_path else None
                )

        # Load registry data
        registry_data = load_registry(reg_path)
        skills = registry_data.get("skills", [])

        # Filter by tag if provided
        if tag:
            skills = [s for s in skills if tag.lower() in [t.lower() for t in s.get("tags", [])]]

        # Convert to SkillInfo models
        skill_infos = []
        for skill in skills:
            skill_infos.append(SkillInfo(
                name=skill["name"],
                description=skill.get("description", ""),
                tags=skill.get("tags", []),
                mcp=skill.get("mcp"),
                auto_detect=skill.get("auto_detect")
            ))

        return SkillListResponse(
            skills=skill_infos,
            total=len(skill_infos),
            registry_path=str(reg_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {str(e)}")


@router.get("/project/{project_name:path}", response_model=ProjectSkillsResponse)
async def get_project_skills(project_name: str):
    """Get skills installed and suggested for a specific project."""
    try:
        # Convert project name to path (handle both relative and absolute)
        project_path = Path(project_name).resolve()
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found at {project_path}")

        # Try to load onboard manifest - return empty if not available
        try:
            from agentic_cli.commands.code import _load_onboard_manifest
            manifest = _load_onboard_manifest(project_path)
        except (ImportError, AttributeError):
            manifest = None

        if not manifest:
            # Return empty response if no manifest
            return ProjectSkillsResponse(
                project_path=str(project_path),
                project_name=project_path.name,
                installed_skills=[],
                suggested_skills=[],
                total_installed=0,
                total_suggested=0
            )

        # Get installed skills
        installed_skills = []
        for skill_name in manifest.get("installed_skills", []):
            skill_path = project_path / ".skills" / skill_name / "SKILL.md"
            if skill_path.exists():
                # Parse skill description from SKILL.md
                description = _parse_skill_description(skill_path)
                installed_skills.append(SkillInfo(
                    name=skill_name,
                    description=description,
                    tags=[],
                    mcp=None,
                    auto_detect=None
                ))

        # Get suggested skills
        try:
            from agentic_cli.analyzer.matcher import load_registry, get_suggested_skills
            from agentic_cli.analyzer.detector import ProjectAnalysis
            from agentic_cli.commands.code import _ensure_registry

            analysis_data = manifest.get("analysis", {})
            registry_path = _ensure_registry()
            registry_data = load_registry(registry_path)

            # Recreate ProjectAnalysis from saved data
            analysis = ProjectAnalysis.from_dict(analysis_data)

            suggested_matches = get_suggested_skills(analysis, registry_data, manifest.get("installed_skills", []))
            suggested_skills = []
            for match in suggested_matches:
                suggested_skills.append(SkillInfo(
                    name=match.name,
                    description=match.description,
                    tags=match.tags,
                    mcp=match.mcp,
                    auto_detect=None
                ))
        except Exception:
            suggested_skills = []

        return ProjectSkillsResponse(
            project_path=str(project_path),
            project_name=project_path.name,
            installed_skills=installed_skills,
            suggested_skills=suggested_skills,
            total_installed=len(installed_skills),
            total_suggested=len(suggested_skills)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project skills: {str(e)}")


@router.post("/install", response_model=SkillInstallResponse)
async def install_skill(request: SkillInstallRequest):
    """Install a skill to a project."""
    try:
        from agentic_cli.commands.code import _ensure_registry, _install_skill_from_registry
        
        # Validate project path
        project_path = Path(request.project_path).resolve()
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found at {request.project_path}")
        
        # Get registry
        registry_path = _ensure_registry()
        
        # Install skill
        success = _install_skill_from_registry(request.skill_name, registry_path, project_path)
        
        if success:
            return SkillInstallResponse(
                success=True,
                message=f"Skill '{request.skill_name}' installed successfully",
                skill_name=request.skill_name,
                project_path=str(project_path)
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Skill '{request.skill_name}' not found in registry"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to install skill: {str(e)}")


@router.get("/show/{skill_name}")
async def show_skill(
    skill_name: str,
    registry_path: Optional[str] = Query(None, description="Override skills registry path")
):
    """Show details of a specific skill from the registry."""
    try:
        from agentic_cli.analyzer.matcher import load_registry
        from agentic_cli.commands.code import _ensure_registry
        
        # Get registry path
        if registry_path:
            reg_path = Path(registry_path)
            if not reg_path.exists() or not (reg_path / "registry.json").exists():
                raise HTTPException(status_code=404, detail=f"Registry not found at {registry_path}")
        else:
            reg_path = _ensure_registry()
        
        # Load registry and find skill
        registry_data = load_registry(reg_path)
        skills = registry_data.get("skills", [])
        
        skill = None
        for s in skills:
            if s["name"] == skill_name:
                skill = s
                break
        
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found in registry")
        
        # Get skill file content if available
        skill_file = reg_path / "skills" / skill_name / "SKILL.md"
        content = ""
        if skill_file.exists():
            content = skill_file.read_text()
        
        return {
            "name": skill["name"],
            "description": skill.get("description", ""),
            "tags": skill.get("tags", []),
            "mcp": skill.get("mcp"),
            "auto_detect": skill.get("auto_detect"),
            "content": content,
            "registry_path": str(reg_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to show skill: {str(e)}")


@router.get("/registry/info")
async def get_registry_info():
    """Get information about the skills registry."""
    try:
        from agentic_cli.commands.code import _ensure_registry, _get_registry_path
        from agentic_cli.analyzer.matcher import load_registry
    except ImportError:
        # agentic_cli not available - return basic info
        return {
            "registry_path": None,
            "exists": False,
            "skills_count": 0,
            "registry_data": {},
            "error": "agentic_cli not available"
        }

    try:
        # Get registry path
        registry_path = _get_registry_path()

        # Try to ensure registry (will clone if needed)
        try:
            actual_path = _ensure_registry()
            exists = True
        except Exception:
            exists = False
            actual_path = registry_path

        # Load registry if it exists
        registry_data = {}
        skills_count = 0
        if exists and (actual_path / "registry.json").exists():
            registry_data = load_registry(actual_path)
            skills_count = len(registry_data.get("skills", []))

        # Check if it's a git repo
        is_git_repo = exists and (actual_path / ".git").exists()

        # Get git remote info if it's a git repo
        git_remote = None
        if is_git_repo:
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(actual_path),
                    capture_output=True,
                    text=True,
                    check=True
                )
                git_remote = result.stdout.strip()
            except subprocess.CalledProcessError:
                pass

        return {
            "configured_path": str(registry_path) if registry_path else None,
            "actual_path": str(actual_path) if exists else None,
            "exists": exists,
            "is_git_repo": is_git_repo,
            "git_remote": git_remote,
            "skills_count": skills_count,
            "last_updated": None  # Could add git timestamp here
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get registry info: {str(e)}")


@router.post("/registry/configure")
async def configure_registry(
    bitbucket_url: str,
    branch: str = "develop",
    local_path: Optional[str] = None
):
    """Configure skills registry from a Bitbucket repository."""
    try:
        import subprocess
        from pathlib import Path
        
        # Determine local path
        if local_path:
            target_path = Path(local_path).expanduser().resolve()
        else:
            # Use default location in ~/.dva/skills-registry
            target_path = Path.home() / ".dva" / "skills-registry"
        
        # Create parent directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone or update the repository
        if target_path.exists():
            # Update existing repository
            if (target_path / ".git").exists():
                subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=str(target_path),
                    capture_output=True,
                    check=True
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Path {target_path} exists but is not a git repository"
                )
        else:
            # Clone new repository
            subprocess.run(
                ["git", "clone", "-b", branch, bitbucket_url, str(target_path)],
                capture_output=True,
                check=True
            )
        
        # Validate that it's a proper skills registry
        registry_file = target_path / "registry.json"
        skills_dir = target_path / "skills"
        
        if not registry_file.exists():
            raise HTTPException(
                status_code=400,
                detail="Repository does not contain registry.json - not a valid skills registry"
            )
        
        if not skills_dir.exists():
            raise HTTPException(
                status_code=400,
                detail="Repository does not contain skills/ directory - not a valid skills registry"
            )
        
        # Update the global config to point to this registry
        from agentic_cli.commands.code import _save_config, _get_config
        config = _get_config()
        config["skills_registry"] = str(target_path)
        _save_config(config)
        
        # Load and validate registry
        from agentic_cli.analyzer.matcher import load_registry
        registry_data = load_registry(target_path)
        skills_count = len(registry_data.get("skills", []))
        
        return {
            "success": True,
            "message": f"Skills registry configured from {bitbucket_url}",
            "local_path": str(target_path),
            "branch": branch,
            "skills_count": skills_count,
            "git_remote": bitbucket_url
        }
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure registry: {str(e)}")


@router.post("/registry/update")
async def update_registry():
    """Update the configured skills registry from its remote."""
    try:
        from agentic_cli.commands.code import _ensure_registry
        
        # Get the registry path
        registry_path = _ensure_registry()
        
        if not (registry_path / ".git").exists():
            raise HTTPException(
                status_code=400,
                detail="Registry is not a git repository - cannot update"
            )
        
        # Pull latest changes
        import subprocess
        result = subprocess.run(
            ["git", "pull", "origin"],
            cwd=str(registry_path),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Git pull failed: {result.stderr}"
            )
        
        # Load updated registry
        from agentic_cli.analyzer.matcher import load_registry
        registry_data = load_registry(registry_path)
        skills_count = len(registry_data.get("skills", []))
        
        return {
            "success": True,
            "message": "Registry updated successfully",
            "skills_count": skills_count,
            "git_output": result.stdout
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update registry: {str(e)}")


def _parse_skill_description(skill_file: Path) -> str:
    """Parse description from SKILL.md frontmatter."""
    try:
        content = skill_file.read_text()
        if not content.startswith("---"):
            return "No description"
        
        # Simple YAML frontmatter parser
        end = content.index("---", 3)
        frontmatter = content[3:end]
        
        for line in frontmatter.split("\n"):
            line = line.strip()
            if line.startswith("description:"):
                desc = line[len("description:"):].strip()
                if desc.startswith(">-") or desc.startswith(">"):
                    # Multi-line description
                    lines = frontmatter.split("\n")
                    desc_lines = []
                    capture = False
                    for fl in lines:
                        if fl.strip().startswith("description:"):
                            capture = True
                            continue
                        if capture:
                            stripped = fl.strip()
                            if stripped and not stripped.endswith(":"):
                                desc_lines.append(stripped)
                            else:
                                break
                    return " ".join(desc_lines) if desc_lines else "No description"
                return desc
    except (ValueError, OSError):
        pass
    return "No description"


def _load_onboard_manifest(project_path: Path) -> Optional[Dict]:
    """Load onboard manifest from project."""
    manifest_file = project_path / ".skills" / "onboard.json"
    if not manifest_file.exists():
        return None
    
    try:
        import json
        return json.loads(manifest_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
