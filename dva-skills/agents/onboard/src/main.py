"""DVA Onboard Agent — standalone entry point.

This agent can be run independently via:
    python src/main.py --project-path /path/to/repo
    dva agent run --path ./onboard-agent

Or invoked by the CLI via:
    dva code onboard --path /path/to/repo --agent

It imports the reusable pipeline from dva_agentic_cli.agents.onboard
and adds configurable prompts, model selection, and result handling.
"""

import argparse
import json
import sys
from pathlib import Path

from config import AgentConfig


def main():
    parser = argparse.ArgumentParser(description="DVA Onboard Agent")
    parser.add_argument("--project-path", required=True, help="Path to the project to analyze")
    parser.add_argument("--registry-path", help="Path to skills registry (default: ~/.dva/skills-registry)")
    parser.add_argument("--enrich", action="store_true", help="Enrich installed skills with project context")
    parser.add_argument("--model", help="Override model name (default: from config)")
    parser.add_argument("--output", help="Output file for results JSON (default: stdout)")
    parser.add_argument(
        "--mode", default="interactive", choices=["interactive", "daemon", "once"],
        help="Run mode",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path {project_path} does not exist", file=sys.stderr)
        sys.exit(1)

    # Load agent config
    config = AgentConfig.load()

    # Load prompts from local prompts/ dir (overrides defaults)
    from dva_agentic_cli.agents.onboard.prompts import load_prompts_from_dir
    agent_dir = Path(__file__).parent.parent
    prompts = load_prompts_from_dir(agent_dir / "prompts")

    # Initialize model (configurable)
    from dva_agentic_cli.agents.onboard.models import init_model
    model = init_model(
        model_name=args.model or config.model_name,
        project_id=config.gcp_project_id,
        location=config.gcp_location,
    )

    # Analyze project
    from dva_agentic_cli.analyzer.detector import analyze_project
    from dva_agentic_cli.analyzer.matcher import load_registry, match_skills, detect_mcp_servers

    print(f"Analyzing project: {project_path}")
    analysis = analyze_project(project_path)

    # Load registry
    registry_path = Path(args.registry_path) if args.registry_path else Path.home() / ".dva" / "skills-registry"
    if not (registry_path / "registry.json").exists():
        print(f"Warning: Registry not found at {registry_path}", file=sys.stderr)
        registry_data = {"skills": []}
    else:
        registry_data = load_registry(registry_path)

    # Match skills
    mcp_servers = detect_mcp_servers(project_path)
    matches = match_skills(analysis, registry_data, mcp_servers)
    installed_skills = [m.name for m in matches]

    # Run the pipeline
    from dva_agentic_cli.agents.onboard.pipeline import run_onboard_pipeline

    print(f"Running onboard agent (model: {args.model or config.model_name})...")
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

    # Output results
    output = {
        "project": str(project_path),
        "installed_skills": installed_skills,
        "proposals": result["proposals"],
        "enriched": [e["skill_name"] for e in result.get("enriched", [])],
        "errors": result.get("errors", []),
    }

    output_json = json.dumps(output, indent=2)
    if args.output:
        Path(args.output).write_text(output_json)
        print(f"Results written to {args.output}")
    else:
        print(output_json)

    # Summary
    print(f"\nProposals: {len(result['proposals'])}")
    for p in result["proposals"]:
        print(f"  - {p['skill_name']}: {p['description']}")

    if result.get("errors"):
        print(f"\nErrors: {len(result['errors'])}")
        for e in result["errors"]:
            print(f"  - {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
