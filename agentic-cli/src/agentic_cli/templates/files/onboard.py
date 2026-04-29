"""Template file generators for the onboard agent use case."""

from pathlib import Path

from agentic_cli.templates.config import TemplateConfig


def generate_onboard_files(target_dir: Path, config: TemplateConfig) -> None:
    """Generate all onboard-agent-specific files."""
    _generate_main(target_dir, config)
    _generate_config(target_dir, config)
    _generate_agent_json(target_dir, config)
    _generate_prompts(target_dir)
    _generate_eval(target_dir)
    _generate_readme(target_dir, config)


def _generate_main(target_dir: Path, config: TemplateConfig) -> None:
    """Generate src/main.py for the onboard agent."""
    main_py = target_dir / "src" / "main.py"
    main_py.parent.mkdir(parents=True, exist_ok=True)
    main_py.write_text(f'''"""Agent-CLI Onboard Agent — {config.name}

Standalone onboard agent project.
Imports reusable pipeline from agentic_cli.agents.onboard.
Customize prompts in prompts/ and config in agent.json.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for local config import
sys.path.insert(0, str(Path(__file__).parent))
from config import AgentConfig


def main():
    parser = argparse.ArgumentParser(description="{config.name} — Onboard Agent")
    parser.add_argument("--project-path", required=True, help="Path to the project to analyze")
    parser.add_argument("--registry-path", help="Path to skills registry")
    parser.add_argument("--enrich", action="store_true", help="Enrich installed skills")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--output", help="Output file for results JSON")
    parser.add_argument(
        "--mode", default="interactive", choices=["interactive", "daemon", "once"],
        help="Run mode",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path {{project_path}} does not exist", file=sys.stderr)
        sys.exit(1)

    # Load config
    agent_config = AgentConfig.load()

    # Load custom prompts from prompts/ directory
    from agentic_cli.agents.onboard.prompts import load_prompts_from_dir
    agent_dir = Path(__file__).parent.parent
    prompts = load_prompts_from_dir(agent_dir / "prompts")

    # Initialize model
    from agentic_cli.agents.onboard.models import init_model
    model = init_model(
        model_name=args.model or agent_config.model_name,
        project_id=agent_config.gcp_project_id,
        location=agent_config.gcp_location,
    )

    # Analyze project
    from agentic_cli.analyzer.detector import analyze_project
    from agentic_cli.analyzer.matcher import load_registry, match_skills, detect_mcp_servers

    print(f"Analyzing: {{project_path}}")
    analysis = analyze_project(project_path)

    # Load registry
    registry_path = Path(args.registry_path) if args.registry_path else Path.home() / ".dva" / "skills-registry"
    registry_data = {{"skills": []}}
    if (registry_path / "registry.json").exists():
        registry_data = load_registry(registry_path)

    # Match existing skills
    mcp_servers = detect_mcp_servers(project_path)
    matches = match_skills(analysis, registry_data, mcp_servers)
    installed_skills = [m.name for m in matches]

    # Run pipeline with custom model + prompts
    from agentic_cli.agents.onboard.pipeline import run_onboard_pipeline

    print(f"Running agent (model: {{args.model or agent_config.model_name}})...")
    result = run_onboard_pipeline(
        analysis=analysis,
        installed_skills=installed_skills,
        registry=registry_data,
        registry_path=registry_path,
        project_path=project_path,
        enrich=args.enrich,
        model=model,
        prompts=prompts,
    )

    # Output
    output = {{
        "project": str(project_path),
        "installed_skills": installed_skills,
        "proposals": result["proposals"],
        "enriched": [e["skill_name"] for e in result.get("enriched", [])],
        "errors": result.get("errors", []),
    }}

    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2))
        print(f"Results: {{args.output}}")
    else:
        print(json.dumps(output, indent=2))

    # Summary
    print(f"\\nProposals: {{len(result['proposals'])}}")
    for p in result["proposals"]:
        print(f"  - {{p['skill_name']}}: {{p['description']}}")


if __name__ == "__main__":
    main()
''')


def _generate_config(target_dir: Path, config: TemplateConfig) -> None:
    """Generate src/config.py for the onboard agent."""
    config_py = target_dir / "src" / "config.py"
    config_py.write_text('''"""Agent configuration — loaded from agent.json or environment variables."""

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentConfig:
    """Configuration for the onboard agent."""

    model_name: str = "gemini-2.5-flash-lite"
    gcp_project_id: str | None = None
    gcp_location: str | None = None
    max_proposals: int = 10
    auto_accept: bool = False

    @classmethod
    def load(cls, config_path: Path | None = None) -> "AgentConfig":
        """Load config from agent.json, falling back to env vars."""
        cfg = cls()

        if config_path is None:
            config_path = Path(__file__).parent.parent / "agent.json"

        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                cfg.model_name = data.get("model_name", cfg.model_name)
                cfg.gcp_project_id = data.get("gcp_project_id", cfg.gcp_project_id)
                cfg.gcp_location = data.get("gcp_location", cfg.gcp_location)
                cfg.max_proposals = data.get("max_proposals", cfg.max_proposals)
                cfg.auto_accept = data.get("auto_accept", cfg.auto_accept)
            except (json.JSONDecodeError, OSError):
                pass

        cfg.model_name = os.environ.get("ONBOARD_AGENT_MODEL", cfg.model_name)
        cfg.gcp_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", cfg.gcp_project_id)
        cfg.gcp_location = os.environ.get("GOOGLE_CLOUD_LOCATION", cfg.gcp_location)

        return cfg
''')


def _generate_agent_json(target_dir: Path, config: TemplateConfig) -> None:
    """Generate agent.json."""
    import json
    agent_json = target_dir / "agent.json"
    agent_json.write_text(json.dumps({
        "name": config.name,
        "description": f"Onboard agent for skill gap detection — {config.name}",
        "version": "0.1.0",
        "model_name": "gemini-2.5-flash-lite",
        "gcp_project_id": config.google_project_id,
        "gcp_location": config.google_location,
        "max_proposals": 10,
        "auto_accept": False,
    }, indent=2) + "\n")


def _generate_prompts(target_dir: Path) -> None:
    """Generate editable prompt files in prompts/."""
    from agentic_cli.agents.onboard.prompts import DEFAULTS

    prompts_dir = target_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for key, template in DEFAULTS.items():
        (prompts_dir / f"{key}.md").write_text(template.strip() + "\n")


def _generate_eval(target_dir: Path) -> None:
    """Generate eval/ scaffolding."""
    eval_dir = target_dir / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)

    (eval_dir / "evaluate.py").write_text('''"""Evaluation framework for the onboard agent.

Add test projects under eval/test_projects/ with expected.json files.

Usage:
    python eval/evaluate.py --test-projects eval/test_projects/
"""

import argparse
import json
import sys
from pathlib import Path


def evaluate_proposals(proposals, expected):
    proposed = {p["skill_name"] for p in proposals}
    expected_set = set(expected.get("expected_skills", []))
    if not expected_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = proposed & expected_set
    prec = len(tp) / len(proposed) if proposed else 0.0
    rec = len(tp) / len(expected_set) if expected_set else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1": round(f1, 3),
        "true_positives": sorted(tp),
        "false_positives": sorted(proposed - expected_set),
        "false_negatives": sorted(expected_set - proposed),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-projects", required=True)
    args = parser.parse_args()
    test_dir = Path(args.test_projects)
    for d in sorted(test_dir.iterdir()):
        exp_file = d / "expected.json"
        if exp_file.exists():
            print(f"Project: {d.name}")
            print(f"  Expected: {json.loads(exp_file.read_text()).get('expected_skills', [])}")
''')

    # Create test_projects dir with a sample
    tp_dir = eval_dir / "test_projects"
    tp_dir.mkdir(parents=True, exist_ok=True)
    (tp_dir / ".gitkeep").touch()


def _generate_readme(target_dir: Path, config: TemplateConfig) -> None:
    """Generate README.md."""
    readme = target_dir / "README.md"
    readme.write_text(f"""# {config.name}

AI-powered onboard agent for skill gap detection and proposal generation.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run against a project
python src/main.py --project-path /path/to/repo

# With custom model
python src/main.py --project-path /path/to/repo --model gemini-pro

# With skill enrichment
python src/main.py --project-path /path/to/repo --enrich
```

## Customization

- **Prompts**: Edit files in `prompts/` to tune detection and generation
- **Model**: Edit `agent.json` or set `ONBOARD_AGENT_MODEL` env var
- **Evaluation**: Add test projects to `eval/test_projects/` with `expected.json`

## Integration with Agent-CLI

```bash
# Register this agent
agent-cli agent register --path . --target opencode

# Use via CLI
agent-cli code onboard --path /path/to/repo --agent-path .
```

## Architecture

This agent imports reusable components from `agentic_cli.agents.onboard`:
- `pipeline.run_onboard_pipeline()` — Orchestrates the full flow
- `gap_detector.detect_skill_gaps()` — AI-powered gap detection
- `skill_generator.generate_skill_content()` — SKILL.md generation
- `models.init_model()` — Configurable model factory
- `prompts.load_prompts_from_dir()` — Load custom prompts
""")
