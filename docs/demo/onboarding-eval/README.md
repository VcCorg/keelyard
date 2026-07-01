# Domain Onboarding Impact — Eval Starter Kit

This folder contains the assets to quantify the value of **domain onboarding**
by comparing a **baseline** agent (no domain context) against a **governed**
agent (domain skills + KG + governance floor + Devin snapshot) on the same
facility-domain task set.

## Files

- `facility-qa.csv` — starter dataset. Tasks are grouped by `category`
  (`governance`, `cross-repo`, `domain-knowledge`, `persona`). The `category`
  column is for demo organization; the eval reads the Ragas-style columns
  (`user_input`, `reference`, `reference_contexts`).
- `governance-adherence.md` — scoring prompt for the custom
  `governance_adherence` LLM-judge metric (1-5), rewarding governance-aware and
  cross-repo-correct answers.

## Run the comparison

```bash
# 1. Register the dataset (creates a versioned copy)
dva eval dataset register cwow-facility-qa ./facility-qa.csv

# 2. Register the custom governance metric (prompt-based LLM judge, 1-5)
dva eval metric register governance_adherence -f ./governance-adherence.md \
  --description "Governance + cross-repo correctness for the facility domain"

# 3. Define one eval config used by BOTH arms (same dataset, metrics, judge)
dva eval create facility-eval cwow-facility-qa \
  --metrics relevance,helpfulness,accuracy,clarity,governance_adherence,latency_ms \
  --judge anthropic

# 4. Run both agents. Every scaffolded agent ships a module-level `answer`
#    entrypoint, so no glue code is needed:
dva eval run agent my_agents.facility.baseline:answer  facility-eval
dva eval run agent my_agents.facility.governed:answer  facility-eval

# 5. Compare -> delta table + HTML report (the demo artifact)
dva eval compare facility-eval --output facility-impact.html
```

## How the agent specs resolve

`dva eval run agent <spec> <eval>` accepts:

- `module.path:answer` — the module-level entrypoint every scaffolded agent now
  ships with (evaluation-ready by default).
- `module.path:ClassName` — a `BaseAgent`-style class; the runner instantiates
  it and auto-wraps `process(dict) -> dict` into `fn(str) -> str`.
- `module.path:function` — any plain `fn(str) -> str`.
- `mock:<type>` — built-in mock (`simple|qa|helpful`) for smoke tests only.

## Honesty notes

- The `reference` answers here are **illustrative placeholders** for the demo;
  replace them with verified golden answers from the facility knowledge base
  before quoting headline numbers.
- For credible numbers, use real `baseline`/`governed` agents (same model + same
  tools); the only difference should be the presence of domain context.
