"""Evaluation framework for the onboard agent.

Run against sample projects to measure:
- Precision: Are proposed skills actually relevant?
- Recall: Does it catch all important gaps?
- Quality: Is the generated SKILL.md content useful?

Usage:
    python eval/evaluate.py --test-projects eval/test_projects/
"""

import argparse
import json
import sys
from pathlib import Path


def load_ground_truth(project_dir: Path) -> dict:
    """Load expected.json from a test project directory."""
    expected_file = project_dir / "expected.json"
    if not expected_file.exists():
        return {}
    return json.loads(expected_file.read_text())


def evaluate_proposals(proposals: list[dict], expected: dict) -> dict:
    """Compare agent proposals against ground truth.

    Args:
        proposals: List of proposals from the agent.
        expected: Ground truth dict with "expected_skills" list.

    Returns:
        Metrics dict with precision, recall, f1.
    """
    proposed_names = {p["skill_name"] for p in proposals}
    expected_names = set(expected.get("expected_skills", []))

    if not expected_names:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "note": "No ground truth"}

    true_positives = proposed_names & expected_names
    false_positives = proposed_names - expected_names
    false_negatives = expected_names - proposed_names

    precision = len(true_positives) / len(proposed_names) if proposed_names else 0.0
    recall = len(true_positives) / len(expected_names) if expected_names else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate onboard agent")
    parser.add_argument("--test-projects", required=True, help="Directory containing test projects")
    parser.add_argument("--results", help="Path to agent results JSON")
    args = parser.parse_args()

    test_dir = Path(args.test_projects)
    if not test_dir.exists():
        print(f"Error: {test_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    print("Onboard Agent Evaluation")
    print("=" * 50)
    print(f"Test projects: {test_dir}")
    print()

    # Find test projects (dirs with expected.json)
    projects = [d for d in test_dir.iterdir() if d.is_dir() and (d / "expected.json").exists()]

    if not projects:
        print("No test projects found (need expected.json in each)")
        sys.exit(1)

    for project_dir in sorted(projects):
        expected = load_ground_truth(project_dir)
        print(f"Project: {project_dir.name}")
        print(f"  Expected skills: {expected.get('expected_skills', [])}")
        print(f"  (Run agent and pass results to evaluate)")
        print()


if __name__ == "__main__":
    main()
