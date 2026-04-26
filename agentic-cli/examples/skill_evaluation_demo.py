#!/usr/bin/env python3
"""
Skill Evaluation Demo Script

This script demonstrates the complete skill evaluation workflow using the
agentic-cli evaluation framework with Vertex AI integration.

Workflow:
1. Create an evaluation dataset
2. Validate a skill file
3. Run skill impact evaluation (with Vertex AI)
4. View evaluation results

Run:
    python examples/skill_evaluation_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_cli.evaluation import (
    DatasetManager,
    EvaluationSample,
    SkillValidator,
    AsyncSkillEvaluator,
    SkillEvaluationReporter,
    SkillEvaluationConfig,
    MockAgents,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def main():
    """Run the complete skill evaluation demo."""

    print_section("Skill Evaluation Demo with Vertex AI")
    print("\nThis demo shows:")
    print("  1. Creating evaluation datasets")
    print("  2. Validating skill files")
    print("  3. Running skill impact evaluation")
    print("  4. Interpreting results")

    # Setup paths
    demo_dir = Path(__file__).parent
    datasets_dir = demo_dir / "datasets"
    skills_dir = demo_dir / "skills"

    datasets_dir.mkdir(exist_ok=True)
    skills_dir.mkdir(exist_ok=True)

    # =========================================================================
    # STEP 1: Create Evaluation Dataset
    # =========================================================================
    print_section("Step 1: Create Evaluation Dataset")

    dataset_manager = DatasetManager(datasets_dir)

    print("\nCreating 'customer-qa' dataset with 5 test samples...")
    dataset = dataset_manager.create_dataset(
        dataset_id="customer-qa",
        name="Customer Support QA",
        description="Q&A pairs for testing customer support skills",
        tags=["customer-support", "faq"],
    )

    # Add test samples
    test_samples = [
        ("What is your return policy?", "We offer 30-day returns on all items."),
        ("How can I track my order?", "You can track your order in your account dashboard."),
        ("Do you offer international shipping?", "Yes, we ship to over 100 countries."),
        ("What payment methods do you accept?", "We accept credit cards, PayPal, and Apple Pay."),
        ("How long does delivery take?", "Standard delivery takes 5-7 business days."),
    ]

    for input_text, expected_output in test_samples:
        dataset.add_sample(
            EvaluationSample(
                input=input_text,
                expected_output=expected_output,
            )
        )

    dataset_manager.save_dataset(dataset)
    print(f"✓ Dataset created with {len(dataset.samples)} samples")
    print(f"  Location: {datasets_dir / 'customer-qa.json'}")

    # =========================================================================
    # STEP 2: Create and Validate a Skill File
    # =========================================================================
    print_section("Step 2: Create and Validate a Skill File")

    skill_content = """---
name: customer-support
description: >-
  Customer support skill providing FAQ responses and general assistance.
  This skill helps agents answer common customer questions about policies,
  shipping, payments, and order tracking.
role: customer-support
domain: ecommerce
---

# Customer Support Skill

Provides comprehensive customer support capabilities for e-commerce operations.

## Instructions

1. Read the customer question carefully
2. Search the knowledge base for relevant FAQ answers
3. Provide a helpful, concise response
4. Offer to escalate to human support if needed

## Available Tools

| Tool | Purpose | Parameters |
|------|---------|-----------|
| `search_faq` | Search customer FAQ database | query: string |
| `get_policy` | Retrieve company policies | policy_name: string |
| `escalate_ticket` | Escalate to human support | reason: string |
| `send_email` | Send customer email | email: string, subject: string, body: string |

## Workflow

1. Parse the incoming customer question
2. Extract key topics (shipping, returns, payments, etc)
3. Query FAQ database for matching answers
4. Provide response with relevant policy links
5. Offer escalation if complex issue

## Examples

**Example 1: Return Policy Question**
- Customer asks: "What is your return policy?"
- Skill searches FAQ for 'return policy'
- Response: "We offer 30-day returns on all items in original condition..."

**Example 2: Shipping Question**
- Customer asks: "How long does delivery take?"
- Skill returns standard delivery timeframe
- Response: "Standard delivery takes 5-7 business days..."

**Example 3: Complex Issue**
- Customer has unique situation
- Skill identifies need for escalation
- Response: "I'll connect you with a specialist who can help..."
"""

    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(skill_content)
    print(f"\nCreated skill file: {skill_file}")

    # Validate the skill
    print("\nValidating skill file...")
    validator = SkillValidator(skill_file)
    validation_result = validator.validate()

    print(f"  Quality Score: {validation_result.quality_score}/100")
    print(f"  Status: {'✓ PASSED' if validation_result.passed else '✗ FAILED'}")

    if validation_result.passed:
        print("  Checks passed:")
        for check in validation_result.checks:
            if check.passed:
                print(f"    ✓ {check.check_name}")
    else:
        print("  Issues found:")
        for error in validation_result.errors:
            print(f"    ✗ {error}")

    # =========================================================================
    # STEP 3: Run Skill Impact Evaluation
    # =========================================================================
    print_section("Step 3: Run Skill Impact Evaluation (with Vertex AI)")

    print("\nConfiguration:")
    print(f"  Agent: customer-support-bot")
    print(f"  Skill: customer-support")
    print(f"  Dataset: customer-qa ({len(dataset.samples)} samples)")
    print(f"  Metrics: accuracy, bleu_score, helpfulness")
    print(f"  Judge: anthropic (Vertex AI with Claude fallback)")
    print(f"  Parallel Workers: 1 (sequential evaluation)")

    # Create evaluator
    config = SkillEvaluationConfig(
        agent_name="customer-support-bot",
        skill_name="customer-support",
        dataset_id="customer-qa",
        metrics=["accuracy", "bleu_score", "helpfulness"],
        judge_type="anthropic",  # Vertex AI with fallback
        parallel_workers=1,
    )

    evaluator = AsyncSkillEvaluator(
        agent_name=config.agent_name,
        skill_name=config.skill_name,
        dataset=dataset,
        metrics=config.metrics,
        judge_type=config.judge_type,
        max_workers=config.parallel_workers,
    )

    # Use mock agents for demo
    agent_with_skill = MockAgents.get_agent("helpful")
    agent_without_skill = MockAgents.get_agent("simple")

    # Progress tracking
    def on_progress(msg: str) -> None:
        print(f"  → {msg}")

    print("\nRunning evaluation...")
    results = await evaluator.evaluate(
        agent_fn=agent_with_skill,
        baseline_agent_fn=agent_without_skill,
        on_progress=on_progress,
    )

    # =========================================================================
    # STEP 4: Display Results
    # =========================================================================
    print_section("Step 4: Evaluation Results")

    # Console report
    print(SkillEvaluationReporter.format_console(config, results))

    # Save results
    evals_dir = demo_dir / "evaluations"
    evals_dir.mkdir(exist_ok=True)
    saved_path = evaluator.save_results(results, evals_dir)

    print(f"✓ Results saved: {saved_path}")

    # =========================================================================
    # INTERPRETATION GUIDE
    # =========================================================================
    print_section("Understanding the Results")

    print("\n**Baseline (without skill):**")
    print("  The agent's performance without the skill enabled.")
    print("  This is the control/reference point.")

    print("\n**With Skill:**")
    print("  The agent's performance with the skill enabled.")
    print("  This shows the actual impact of the skill.")

    print("\n**Impact (Delta):**")
    print("  The difference between with-skill and baseline.")
    print("  - Positive delta = skill improved performance")
    print("  - Negative delta = skill hurt performance")

    print("\n**Effectiveness Score (0-10):**")
    print("  Overall assessment of skill value:")
    print("    8-10: Excellent - Strong improvement")
    print("    6-8:  Good - Moderate improvement")
    print("    4-6:  Fair - Minor improvement or mixed results")
    print("    0-4:  Needs work - Negative or minimal impact")

    # =========================================================================
    # NEXT STEPS
    # =========================================================================
    print_section("Next Steps")

    print("\n1. **Iterate the Skill:**")
    print("   If effectiveness < 7, improve the skill and re-evaluate")

    print("\n2. **Publish the Skill:**")
    print("   Once validated, publish to skill marketplace with metrics")

    print("\n3. **Monitor Performance:**")
    print("   Track skill effectiveness over time with different agents/datasets")

    print("\n4. **Share with Team:**")
    print("   Export results and share findings with stakeholders")

    print("\n" + "=" * 80)
    print("✓ Demo Complete!")
    print("=" * 80)

    print("\nFor more information:")
    print("  - Skill Validation: docs/SKILL_VALIDATION_GUIDE.md")
    print("  - Evaluation Framework: docs/SKILL_EVALUATION_INTEGRATION.md")
    print("  - Dataset Format: See 'customer-qa.json' in examples/datasets/")


if __name__ == "__main__":
    asyncio.run(main())
