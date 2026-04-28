# DVA Onboard Agent

AI-powered skill gap detection and proposal generation for project onboarding.

## Overview

This agent analyzes a project's tech stack and compares it against the DVA skills registry to identify gaps — technologies, patterns, or frameworks that aren't covered by existing skills. It then generates SKILL.md files and registry entries for proposed new skills.

## Architecture

```
onboard/
├── src/
│   ├── main.py          # Agent entry point
│   └── config.py        # Agent-specific configuration
├── prompts/             # Editable prompt templates (override defaults)
│   ├── gap_detection.md
│   ├── skill_content.md
│   └── skill_enrichment.md
├── eval/                # Evaluation framework
│   ├── evaluate.py
│   └── test_projects/   # Sample repos for accuracy testing
├── tests/
├── agent.json           # Agent configuration
└── pyproject.toml
```

The agent imports reusable components from `dva_agentic_cli.agents.onboard`:
- **`pipeline.run_onboard_pipeline()`** — Full pipeline orchestrator
- **`gap_detector.detect_skill_gaps()`** — AI gap detection
- **`skill_generator.generate_skill_content()`** — SKILL.md generation
- **`models.init_model()`** — Configurable model factory
- **`prompts.load_prompts_from_dir()`** — Load prompt overrides from files

## Usage

### Via CLI (recommended)
```bash
# Uses this default agent from the skills registry
`agent code onboard --path ./my-repo --agent

# Uses a custom agent project
`agent code onboard --path ./my-repo --agent-path /path/to/custom-onboard-agent
```

### Standalone
```bash
python src/main.py --project-path /path/to/repo
python src/main.py --project-path /path/to/repo --model gemini-pro --enrich
```

### Via agent agent commands
```bash
`agent agent run --path ./onboard-agent
```

## Customization

### Prompts
Edit files in `prompts/` to tune the agent's behavior. Each file overrides the corresponding default prompt from the library.

### Model
Edit `agent.json` or set environment variables:
```bash
export ONBOARD_AGENT_MODEL=gemini-pro
export GOOGLE_CLOUD_PROJECT=my-project
export GOOGLE_CLOUD_LOCATION=us-central1
```

### Evaluation
Add test projects to `eval/test_projects/` with an `expected.json`:
```json
{
  "expected_skills": ["spring-cloud-gcp", "liquibase-spanner"]
}
```
Run: `python eval/evaluate.py --test-projects eval/test_projects/`

## Creating a Custom Agent

```bash
`agent project create my-onboard-agent --use-case onboard
```

This scaffolds a new agent project with the same structure, ready for customization.
