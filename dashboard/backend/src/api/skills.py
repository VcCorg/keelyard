"""Skills API endpoints for KEEL Dashboard."""

import shutil
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


class SkillRemoveRequest(BaseModel):
    """Request model for removing a local skill."""
    skill_name: str
    project_path: str


class SkillRemoveResponse(BaseModel):
    """Response model for skill removal."""
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


class IntegrationTarget(BaseModel):
    """A place a skill can be installed/integrated into."""
    id: str
    label: str
    type: str  # "project" | "domain" | "custom"
    path: str
    available: bool = True
    detail: str = ""


class IntegrationTargetsResponse(BaseModel):
    targets: List[IntegrationTarget]


def _resolve_domain_repo_path(workspace: Path, slug: str) -> Optional[Path]:
    """Best-effort resolution of a domain's local context/meta repo on disk."""
    candidates = [
        workspace / slug / f"{slug}-context-meta",   # unified (post-cutover)
        workspace / slug / f"{slug}-domain-context",  # legacy
        workspace / slug / "repos" / "domain-context",
        workspace / slug / f"domain-{slug}-meta",     # legacy
        workspace / slug,
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


class ValidateWithDevinRequest(BaseModel):
    """Request to validate a skill with a Devin session."""
    skill_name: str
    target_path: Optional[str] = None
    extra_instructions: Optional[str] = None
    dry_run: bool = False


def _load_skill(skill_name: str) -> Dict[str, Any]:
    """Load a skill's metadata + SKILL.md content from the registry."""
    from agentic_cli.analyzer.matcher import load_registry
    from agentic_cli.commands.code import _ensure_registry

    reg_path = _ensure_registry()
    registry_data = load_registry(reg_path)
    skill = next((s for s in registry_data.get("skills", []) if s["name"] == skill_name), None)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found in registry")

    skill_file = reg_path / "skills" / skill_name / "SKILL.md"
    content = skill_file.read_text() if skill_file.exists() else ""
    return {
        "name": skill["name"],
        "description": skill.get("description", ""),
        "tags": skill.get("tags", []),
        "mcp": skill.get("mcp"),
        "content": content,
    }


def _build_validation_prompt(skill: Dict[str, Any], target_path: Optional[str], extra: Optional[str]) -> str:
    """Construct a structured skill-validation prompt for Devin."""
    parts = [
        f"You are validating an Agent Skill named **{skill['name']}**.",
        "",
        "## Goal",
        "Exercise this skill end-to-end and assess whether it works as documented.",
        "Follow the skill's own instructions, run any scripts or steps it defines, and",
        "test realistic and edge-case inputs.",
        "",
    ]
    if target_path:
        parts += [f"## Target repository / working directory\n`{target_path}`", ""]
    if extra:
        parts += [f"## Additional instructions\n{extra}", ""]
    parts += [
        "## Required structured output",
        "When finished, return a `structured_output` JSON object with exactly these fields:",
        "```json",
        "{",
        '  "verdict": "PASS | FAIL | PARTIAL",',
        '  "summary": "one-paragraph result",',
        '  "what_worked": ["..."],',
        '  "issues": ["..."],',
        '  "edge_cases_tested": ["..."],',
        '  "suggested_skill_edits": ["concrete SKILL.md improvements"]',
        "}",
        "```",
        "",
        "## SKILL.md under test",
        "```markdown",
        skill["content"] or "(SKILL.md content unavailable — fetch from the skill source.)",
        "```",
    ]
    return "\n".join(parts)


@router.post("/validate-with-devin")
async def validate_skill_with_devin(req: ValidateWithDevinRequest):
    """Create a Devin session that validates the given skill. Available to all users."""
    try:
        from src.services.devin_service import CreateSessionRequest, create_session
    except ImportError as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Devin service unavailable: {e}")

    skill = _load_skill(req.skill_name)
    prompt = _build_validation_prompt(skill, req.target_path, req.extra_instructions)

    session_req = CreateSessionRequest(
        prompt=prompt,
        title=f"Validate skill · {skill['name']}",
        tags=["skill-validation", skill["name"]],
        idempotent=True,
        dry_run=req.dry_run,
    )
    try:
        res = create_session(session_req)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to create Devin session: {e}")

    return {
        "skill_name": skill["name"],
        "dry_run": res.dry_run,
        "session_id": res.session_id,
        "url": res.url,
        "status": res.status,
        "is_new": res.is_new,
    }


class SecurityScanRequest(BaseModel):
    """Request to security-scan a skill. Provide a registry skill name or a path."""
    skill_name: Optional[str] = None
    path: Optional[str] = None
    # None = auto (LLM only if a provider key is configured); True/False = force.
    use_llm: Optional[bool] = None


@router.get("/security/status")
async def security_scanner_status():
    """Report whether the SkillSpector security scanner is available."""
    from src.services import skill_security_service as sec
    return sec.is_available()


@router.post("/security/scan")
async def security_scan_skill(req: SecurityScanRequest):
    """Scan a skill for vulnerabilities / malicious patterns via SkillSpector.

    Returns a normalized verdict (SAFE / CAUTION / DO_NOT_INSTALL) with the
    underlying risk score and individual issues.
    """
    from src.services import skill_security_service as sec

    if not req.skill_name and not req.path:
        raise HTTPException(status_code=400, detail="Provide a skill_name or a path to scan")

    try:
        if req.skill_name:
            return sec.scan_registry_skill(req.skill_name, use_llm=req.use_llm)
        return sec.scan_path(Path(req.path), use_llm=req.use_llm)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # Scanner missing or errored — 503 so the UI can show a clear banner.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Security scan failed: {str(e)}")


@router.get("/targets", response_model=IntegrationTargetsResponse)
async def list_integration_targets():
    """List places a skill can be integrated into: the current project and any
    on-disk domain repos under the configured code workspace."""
    targets: List[IntegrationTarget] = [
        IntegrationTarget(
            id="cwd",
            label="Current project",
            type="project",
            path=str(Path.cwd()),
            available=True,
            detail="Backend working directory",
        )
    ]

    # Resolve domain repos under the configured code workspace.
    try:
        from agentic_cli.commands.code import _get_config
        from src.services import domain_service as dsvc

        workspace_raw = (_get_config() or {}).get("code_workspace")
        workspace = Path(workspace_raw).expanduser() if workspace_raw else None

        for d in dsvc.list_domains():
            path = _resolve_domain_repo_path(workspace, d.name) if workspace else None
            targets.append(
                IntegrationTarget(
                    id=f"domain:{d.name}",
                    label=f"{d.domain} ({d.name})",
                    type="domain",
                    path=str(path) if path else "",
                    available=path is not None,
                    detail="Domain context repo" if path else "Repo not found locally",
                )
            )
    except Exception:  # noqa: BLE001
        # Domains are a best-effort convenience; never block the project target.
        pass

    return IntegrationTargetsResponse(targets=targets)


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

        # If no manifest, treat it as empty so the .skills/ scan still works.
        if not manifest:
            manifest = {}

        # Get installed skills from the manifest and by scanning .skills/.
        installed_names: set[str] = set(manifest.get("installed_skills", []))
        skills_dir = project_path / ".skills"
        if skills_dir.exists() and skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    installed_names.add(skill_dir.name)

        installed_skills = []
        for skill_name in sorted(installed_names):
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


@router.post("/remove", response_model=SkillRemoveResponse)
async def remove_skill(request: SkillRemoveRequest):
    """Remove a locally installed skill from a project.

    Only removes skills from the project's .skills/ or .claude/skills/
    directories; it will not touch the shared skills registry.
    """
    try:
        project_path = Path(request.project_path).resolve()
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found at {request.project_path}")

        # Local skill directories only.
        skill_dir = None
        for local_dir in (".skills", ".claude/skills"):
            candidate = project_path / local_dir / request.skill_name
            if candidate.exists() and (candidate / "SKILL.md").exists():
                skill_dir = candidate
                break

        if not skill_dir:
            raise HTTPException(
                status_code=404,
                detail=f"Local skill '{request.skill_name}' not found in {project_path}"
            )

        # Security: ensure the resolved directory is still under the project.
        try:
            skill_dir.relative_to(project_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid skill path") from e

        shutil.rmtree(skill_dir)

        # Update the onboard manifest, if one exists.
        try:
            from agentic_cli.commands.code import _update_manifest_removed
            _update_manifest_removed(project_path, request.skill_name)
        except Exception:
            # Manifest update is best-effort; the skill directory is already gone.
            pass

        return SkillRemoveResponse(
            success=True,
            message=f"Skill '{request.skill_name}' removed from {project_path}",
            skill_name=request.skill_name,
            project_path=str(project_path),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove skill: {str(e)}")


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
            # Use default location in ~/.keel/skills-registry
            target_path = Path.home() / ".keel" / "skills-registry"
        
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


# ── Skill trials: evaluate against a domain, then promote (lead) ─────────────

from fastapi import Depends, Request  # noqa: E402

from src.services.skill_trial_service import (  # noqa: E402
    PromoteResult,
    TrialScorecard,
    UploadResult,
    evaluate_trial,
    promote_trial,
    stage_uploaded_skill,
)


class TrialRequest(BaseModel):
    skill_name: str
    domain: str = ""
    run_security: bool = True


class UploadedSkillFile(BaseModel):
    path: str
    content: str


class UploadSkillRequest(BaseModel):
    skill_name: str = ""
    files: List[UploadedSkillFile]


def _require_promote():
    """Promotion writes to the domain's validated tier — knowledge:project (lead)."""
    from agentic_cli.auth import PERM_KNOWLEDGE_PROJECT
    from src.services.auth_service import require

    return require(PERM_KNOWLEDGE_PROJECT)


@router.post("/trial/evaluate", response_model=TrialScorecard)
async def api_trial_evaluate(req: TrialRequest, request: Request):
    """Run the trial scorecard for a skill against a domain (any role)."""
    from src.services.auth_service import actor_of, principal_from_request

    try:
        from agentic_cli.auth import persona_for

        persona = persona_for(principal_from_request(request))
    except Exception:  # noqa: BLE001
        persona = "dev"
    try:
        return evaluate_trial(req.skill_name, req.domain, persona,
                              actor=actor_of(request), run_security=req.run_security)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trial/upload", response_model=UploadResult)
async def api_trial_upload(req: UploadSkillRequest, request: Request):
    """Stage an uploaded candidate skill (file or folder) into the registry.

    Sent as JSON ({skill_name, files:[{path, content}]}) so it works in the
    packaged app without a multipart dependency. Any role can load a skill to
    trial it; promotion into a domain's validated tier stays a lead action.
    """
    from src.services.auth_service import actor_of

    files = [(f.path, f.content) for f in req.files]
    try:
        return stage_uploaded_skill(req.skill_name, files, actor=actor_of(request))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/install/stream")
async def security_install_stream():
    """Install the SkillSpector security scanner, streaming progress (SSE).

    Runs `uv tool install git+…/skillspector`. If `uv` isn't on the backend's
    PATH the stream surfaces the error with the manual command.
    """
    from sse_starlette.sse import EventSourceResponse
    from src.services.run_registry import registry

    cmd = ["uv", "tool", "install",
           "git+https://github.com/NVIDIA/skillspector.git"]
    rec = registry.create(kind="cli", label="install skillspector", cmd=cmd)

    async def gen():
        async for event in registry.stream(rec, cmd):
            yield event

    return EventSourceResponse(gen())


@router.post("/trial/promote", response_model=PromoteResult)
async def api_trial_promote(req: TrialRequest, request: Request,
                            _principal=Depends(_require_promote())):
    """Promote a trialed skill into the domain's validated tier (lead action)."""
    from src.services.auth_service import actor_of

    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="A domain is required to promote")
    try:
        return promote_trial(req.skill_name, req.domain.strip(), actor=actor_of(request))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


class JudgeRequest(BaseModel):
    skill_name: str
    domain: str = ""
    scenarios: int = 3
    model: Optional[str] = None


@router.post("/trial/judge")
async def api_trial_judge(req: JudgeRequest, request: Request):
    """LLM-as-judge impact evaluation: skill vs baseline over N scenarios."""
    from src.services.auth_service import actor_of
    from src.services.skill_trial_service import judge_trial

    if req.scenarios < 1 or req.scenarios > 5:
        raise HTTPException(status_code=400, detail="scenarios must be 1-5")
    try:
        import asyncio

        return await asyncio.to_thread(
            judge_trial, req.skill_name, req.domain, req.scenarios, req.model,
            actor_of(request))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit")
async def api_skill_audit(limit: int = Query(50, ge=1, le=500)):
    """Recent skill trial/judge/promote actions from the central audit trail."""
    try:
        from agentic_cli.tracker import get_activity

        rows = get_activity(command="skill", limit=limit)
    except Exception:  # noqa: BLE001
        rows = []
    trial_actions = {"trial_evaluate", "trial_judge", "trial_promote", "scan"}
    filtered = [r for r in rows if (r.get("subcommand") or r.get("action")) in trial_actions]
    return {"actions": filtered}
