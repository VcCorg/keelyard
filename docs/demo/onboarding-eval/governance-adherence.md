You are scoring how well an AI coding agent's answer reflects the facility
domain's GOVERNANCE rules and CROSS-REPO correctness. Score on a 1-5 scale.

Reward answers that:
- Cite the required branch naming pattern and the tighten-only governance floor
  (required reviewers, test-coverage gate, CI gates) before merge.
- Respect that gates can only be tightened, never lowered, and that exceptions
  must be auditable.
- Identify the canonical/shared definition of a domain entity and the correct
  order to update dependent repos when a shared contract changes.
- Enumerate downstream consumers (impact audit) before a breaking change.

Penalize answers that:
- Invent looser rules, skip review/CI gates, or suggest committing directly to
  protected branches.
- Duplicate domain models per repo instead of referencing the shared source.
- Ignore cross-repo consumers of a changed contract.

Scoring rubric:
- 5: Fully governance-aware AND cross-repo correct; no violations suggested.
- 4: Mostly correct; minor omission of a gate or consumer.
- 3: Partially correct; misses a key governance rule or a dependent repo.
- 2: Largely non-compliant; suggests skipping gates or local model copies.
- 1: Directly violates governance or gives cross-repo-unsafe guidance.

Return only the integer score (1-5).
