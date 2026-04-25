"""Skill validation for quality assurance and certification."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any
import yaml


@dataclass
class CheckResult:
    """Result of a single validation check."""
    check_name: str
    passed: bool
    score: float  # 0-1
    message: str
    severity: str = "info"  # info, warning, error


@dataclass
class ValidationResult:
    """Overall validation results for a skill."""
    skill_path: Path
    skill_name: str
    passed: bool
    quality_score: int  # 0-100
    checks: List[CheckResult] = field(default_factory=list)
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    sections: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SkillValidator:
    """Validates Agent Skills for quality, completeness, and structure."""

    REQUIRED_FRONTMATTER_FIELDS = {"name", "description"}
    REQUIRED_SECTIONS = {"Instructions", "Available Tools", "Workflow"}
    OPTIONAL_SECTIONS = {"Overview", "Examples", "Related Skills", "Notes"}

    def __init__(self, skill_path: Path):
        """Initialize validator with a skill file path."""
        self.skill_path = Path(skill_path)
        self.content = ""
        self.frontmatter: Dict[str, Any] = {}
        self.body = ""

    def validate(self) -> ValidationResult:
        """Run all validation checks and return results."""
        result = ValidationResult(
            skill_path=self.skill_path,
            skill_name=self.skill_path.parent.name,
            passed=False,
            quality_score=0,
        )

        try:
            self.content = self.skill_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            result.errors.append(f"Skill file not found: {self.skill_path}")
            return result
        except Exception as e:
            result.errors.append(f"Error reading skill file: {e}")
            return result

        # Parse frontmatter and body
        self._parse_content()
        result.frontmatter = self.frontmatter

        # Run checks
        checks = [
            self._check_file_exists(),
            self._check_frontmatter_present(),
            self._check_frontmatter_valid_yaml(),
            self._check_required_fields(),
            self._check_sections_present(),
            self._check_markdown_formatting(),
            self._check_tool_references(),
            self._check_completeness(),
            self._check_clarity(),
        ]

        result.checks = [c for c in checks if c is not None]
        result.sections = self._extract_sections()

        # Calculate overall score
        if result.errors:
            result.passed = False
            result.quality_score = max(0, 100 - (len(result.errors) * 20))
        else:
            passed_checks = sum(1 for c in result.checks if c.passed)
            total_checks = len(result.checks)
            result.quality_score = int((passed_checks / total_checks * 100)) if total_checks > 0 else 0
            result.passed = result.quality_score >= 70 and len(result.warnings) < 3

        # Collect warnings and errors
        for check in result.checks:
            if check.severity == "error" and not check.passed:
                result.errors.append(check.message)
            elif check.severity == "warning" and not check.passed:
                result.warnings.append(check.message)

        return result

    def _parse_content(self) -> None:
        """Parse YAML frontmatter and body from content."""
        if not self.content.startswith("---"):
            return

        try:
            end_index = self.content.index("---", 3)
            frontmatter_str = self.content[3:end_index].strip()
            self.body = self.content[end_index + 3:].strip()

            if frontmatter_str:
                self.frontmatter = yaml.safe_load(frontmatter_str) or {}
        except (ValueError, yaml.YAMLError):
            pass

    def _check_file_exists(self) -> CheckResult:
        """Verify skill file exists and is readable."""
        exists = self.skill_path.exists()
        return CheckResult(
            check_name="File Existence",
            passed=exists,
            score=1.0 if exists else 0.0,
            message="Skill file exists and is readable" if exists else "Skill file not found",
            severity="error" if not exists else "info",
        )

    def _check_frontmatter_present(self) -> CheckResult:
        """Check if YAML frontmatter is present."""
        has_frontmatter = self.content.startswith("---")
        return CheckResult(
            check_name="Frontmatter Present",
            passed=has_frontmatter,
            score=1.0 if has_frontmatter else 0.0,
            message="YAML frontmatter detected" if has_frontmatter else "Missing YAML frontmatter (---...---)",
            severity="error" if not has_frontmatter else "info",
        )

    def _check_frontmatter_valid_yaml(self) -> CheckResult:
        """Verify frontmatter is valid YAML."""
        if not self.content.startswith("---"):
            return CheckResult(
                check_name="Valid YAML",
                passed=False,
                score=0.0,
                message="No frontmatter to validate",
                severity="error",
            )

        try:
            # frontmatter dict is already parsed, so just check if it exists
            if not self.frontmatter:
                return CheckResult(
                    check_name="Valid YAML",
                    passed=False,
                    score=0.0,
                    message="Frontmatter is empty or invalid YAML",
                    severity="error",
                )
            return CheckResult(
                check_name="Valid YAML",
                passed=True,
                score=1.0,
                message="Frontmatter is valid YAML",
                severity="info",
            )
        except Exception as e:
            return CheckResult(
                check_name="Valid YAML",
                passed=False,
                score=0.0,
                message=f"Invalid YAML in frontmatter: {str(e)[:100]}",
                severity="error",
            )

    def _check_required_fields(self) -> CheckResult:
        """Check for required frontmatter fields."""
        if not self.frontmatter:
            return CheckResult(
                check_name="Required Fields",
                passed=False,
                score=0.0,
                message=f"Missing required fields: {', '.join(self.REQUIRED_FRONTMATTER_FIELDS)}",
                severity="error",
            )

        missing = self.REQUIRED_FRONTMATTER_FIELDS - set(self.frontmatter.keys())
        has_all = len(missing) == 0

        return CheckResult(
            check_name="Required Fields",
            passed=has_all,
            score=1.0 if has_all else 0.5,
            message=(
                "All required fields present (name, description)"
                if has_all
                else f"Missing required fields: {', '.join(missing)}"
            ),
            severity="error" if not has_all else "info",
        )

    def _check_sections_present(self) -> CheckResult:
        """Check for required sections in skill body."""
        sections = self._extract_sections()
        missing = self.REQUIRED_SECTIONS - set(sections.keys())
        has_all = len(missing) == 0

        return CheckResult(
            check_name="Required Sections",
            passed=has_all,
            score=1.0 if has_all else 0.6,
            message=(
                "All required sections present (Instructions, Available Tools, Workflow)"
                if has_all
                else f"Missing sections: {', '.join(missing)}"
            ),
            severity="error" if not has_all else "info",
        )

    def _check_markdown_formatting(self) -> CheckResult:
        """Verify basic Markdown formatting."""
        issues = []

        # Check for heading structure
        lines = self.body.split("\n")
        has_h1 = any(line.startswith("# ") for line in lines)
        if not has_h1:
            issues.append("No top-level heading (# Title)")

        # Check for unmatched brackets
        bracket_count = self.body.count("[") - self.body.count("]")
        paren_count = self.body.count("(") - self.body.count(")")
        if bracket_count != 0:
            issues.append("Unmatched brackets in body")
        if paren_count != 0:
            issues.append("Unmatched parentheses in body")

        passed = len(issues) == 0
        return CheckResult(
            check_name="Markdown Formatting",
            passed=passed,
            score=1.0 if passed else 0.7,
            message="; ".join(issues) if issues else "Markdown formatting looks good",
            severity="warning" if not passed else "info",
        )

    def _check_tool_references(self) -> CheckResult:
        """Check for valid tool references in Available Tools section."""
        sections = self._extract_sections()
        if "Available Tools" not in sections or not sections["Available Tools"]:
            return CheckResult(
                check_name="Tool References",
                passed=False,
                score=0.0,
                message="Available Tools section is empty or not found",
                severity="warning",
            )

        # Extract tool section content
        body_lines = self.body.split("\n")
        tool_section_start = None
        for i, line in enumerate(body_lines):
            if "Available Tools" in line:
                tool_section_start = i
                break

        if tool_section_start is None:
            return CheckResult(
                check_name="Tool References",
                passed=False,
                score=0.0,
                message="Available Tools section header not found",
                severity="warning",
            )

        # Collect lines until next section
        tool_content = []
        for i in range(tool_section_start + 1, len(body_lines)):
            line = body_lines[i]
            if line.startswith("##"):
                break
            tool_content.append(line.strip())

        tool_text = "\n".join(tool_content).strip()
        has_tools = len(tool_text) > 10

        return CheckResult(
            check_name="Tool References",
            passed=has_tools,
            score=1.0 if has_tools else 0.5,
            message="Tool references documented" if has_tools else "Available Tools section appears empty",
            severity="warning" if not has_tools else "info",
        )

    def _check_completeness(self) -> CheckResult:
        """Assess completeness of skill definition."""
        min_body_length = 200  # Reasonable minimum for a skill definition

        completeness_score = 0.0
        issues = []

        # Check body length
        if len(self.body) >= min_body_length:
            completeness_score += 0.3
        else:
            issues.append(f"Skill definition too short ({len(self.body)} chars, min {min_body_length})")

        # Check for examples
        if "Example" in self.body or "example" in self.body:
            completeness_score += 0.3
        else:
            issues.append("No examples provided")

        # Check for step-by-step workflow
        workflow_found = "Workflow" in self.body or "workflow" in self.body
        if workflow_found and any(line.strip().startswith(f"{i}.") for i in range(1, 6) for line in self.body.split("\n")):
            completeness_score += 0.4
        else:
            issues.append("Workflow section missing or not properly numbered")

        return CheckResult(
            check_name="Completeness",
            passed=completeness_score >= 0.7,
            score=min(1.0, completeness_score),
            message=(
                "Skill is well-documented with examples and workflow"
                if completeness_score >= 0.7
                else f"Skill completeness issues: {'; '.join(issues)}"
            ),
            severity="warning" if completeness_score < 0.7 else "info",
        )

    def _check_clarity(self) -> CheckResult:
        """Assess clarity of skill instructions and documentation."""
        clarity_score = 0.0
        issues = []

        # Check for clear instructions
        if "Instructions" in self.body or "instructions" in self.body:
            clarity_score += 0.3
        else:
            issues.append("Clear instructions section not found")

        # Check description in frontmatter
        description = self.frontmatter.get("description", "")
        if isinstance(description, str) and len(description) > 30:
            clarity_score += 0.3
        else:
            issues.append("Description in frontmatter is too short or missing")

        # Check for readable structure (headings, lists)
        has_lists = "-" in self.body or "*" in self.body or any(
            line.strip().startswith(f"{i}.") for i in range(1, 6) for line in self.body.split("\n")
        )
        if has_lists:
            clarity_score += 0.4
        else:
            issues.append("Content structure could be clearer (use lists/bullets)")

        return CheckResult(
            check_name="Clarity",
            passed=clarity_score >= 0.7,
            score=min(1.0, clarity_score),
            message=(
                "Instructions are clear and well-structured"
                if clarity_score >= 0.7
                else f"Clarity issues: {'; '.join(issues)}"
            ),
            severity="warning" if clarity_score < 0.7 else "info",
        )

    def _extract_sections(self) -> Dict[str, bool]:
        """Extract sections found in skill body."""
        sections = {}
        for section in self.REQUIRED_SECTIONS | self.OPTIONAL_SECTIONS:
            # Match heading with exact case or case-insensitive
            pattern = rf"^##\s+{re.escape(section)}\s*$"
            found = any(re.match(pattern, line) for line in self.body.split("\n"))
            sections[section] = found

        return sections
