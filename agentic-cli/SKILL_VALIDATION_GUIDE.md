# Skill Validation Guide

## Overview

The skill validation system (Phase A of Skill Evaluation Integration) provides comprehensive quality checks for Agent Skills before publication or deployment. It validates structure, completeness, and clarity using a 9-point validation framework.

## Quick Start

### Validate a Skill

```bash
# Basic validation
agent eval validate-skill .skills/my-skill/SKILL.md

# JSON output for automation
agent eval validate-skill .skills/my-skill/SKILL.md --output json

# Specific checks only
agent eval validate-skill .skills/my-skill/SKILL.md --check structure
```

### Understanding the Quality Score

Quality scores range from 0-100:

| Score | Rating | Meaning |
|-------|--------|---------|
| 90-100 | ⭐⭐⭐⭐⭐ Excellent | Production-ready skill |
| 70-89 | ⭐⭐⭐⭐ Good | Minor improvements needed |
| 50-69 | ⭐⭐⭐ Fair | Significant improvements required |
| < 50 | ⭐⭐ Poor | Major issues prevent use |

## Validation Checks

The validator performs 9 comprehensive checks:

### 1. **File Existence**
- Ensures the skill file exists and is readable
- **Severity**: Error (blocks validation)

### 2. **Frontmatter Present**
- Checks for YAML frontmatter (between `---` markers)
- **Required**: Yes
- **Severity**: Error

### 3. **Valid YAML**
- Verifies frontmatter is valid YAML syntax
- **Severity**: Error

### 4. **Required Fields**
- Checks for mandatory fields: `name`, `description`
- **Severity**: Error

### 5. **Required Sections**
- Validates presence of required markdown sections:
  - `## Instructions` — How to use the skill
  - `## Available Tools` — Tools and capabilities
  - `## Workflow` — Step-by-step process
- **Severity**: Error

### 6. **Markdown Formatting**
- Checks for:
  - Valid heading structure
  - Matched brackets and parentheses
  - Proper link syntax
- **Severity**: Warning

### 7. **Tool References**
- Ensures `Available Tools` section is populated
- Checks for actual tool descriptions (not empty)
- **Severity**: Warning

### 8. **Completeness**
- Evaluates:
  - Minimum body length (200 characters)
  - Presence of examples
  - Numbered workflow steps
- **Severity**: Warning

### 9. **Clarity**
- Assesses:
  - Clear instructions
  - Meaningful description
  - Proper content structure (lists, bullets)
- **Severity**: Warning

## Skill File Structure

A valid skill file follows this structure:

```markdown
---
name: skill-name
description: >-
  A brief, meaningful description of what this skill does
  and when to use it.
---

# Skill Title

Brief introduction to the skill and its purpose.

## Instructions

Step-by-step instructions for using the skill:

1. First instruction
2. Second instruction
3. Third instruction

## Available Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `tool_name` | What it does | param1, param2 |
| `other_tool` | Another tool | params |

## Workflow

1. Explain the first step
2. Explain the second step
3. Explain the third step

## Examples

Provide concrete examples:

**Example 1:** Using the skill for task X
- Step by step walkthrough

**Example 2:** Using the skill for task Y
- Step by step walkthrough
```

## Example Outputs

### Console Output (Valid Skill)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ Skill Validation Results                     ┃
┃                                                 ┃
┃ Skill: pr-reviewer                              ┃
┃ Quality Score: 95/100                           ┃
┃ Status: ✓ PASSED                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Validation Checks:

Check                       Status   Message
─────────────────────────────────────────────────
File Existence              ✓        Skill file exists and is readable
Frontmatter Present         ✓        YAML frontmatter detected
Valid YAML                  ✓        Frontmatter is valid YAML
Required Fields             ✓        All required fields present (name, description)
Required Sections           ✓        All required sections present
Markdown Formatting         ✓        Markdown formatting looks good
Tool References             ✓        Tool references documented
Completeness                ✓        Skill is well-documented with examples and workflow
Clarity                     ✓        Instructions are clear and well-structured

Sections Found:

Section              Status
─────────────────────────────
Instructions         ✓
Available Tools      ✓
Workflow             ✓
Examples             ✓
```

### Console Output (Invalid Skill)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ⚠️ Skill Validation Results                    ┃
┃                                                ┃
┃ Skill: bad-skill                               ┃
┃ Quality Score: 45/100                          ┃
┃ Status: ⚠ NEEDS IMPROVEMENT                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Validation Checks:

Check                       Status   Message
─────────────────────────────────────────────────
File Existence              ✓        Skill file exists and is readable
Frontmatter Present         ✓        YAML frontmatter detected
Valid YAML                  ✓        Frontmatter is valid YAML
Required Fields             ✗        Missing required fields: description
Required Sections           ✗        Missing sections: Available Tools, Workflow
Markdown Formatting         ✓        Markdown formatting looks good
Tool References             ✗        Available Tools section is empty
Completeness                ✗        Skill definition too short (48 chars); No examples
Clarity                     ✗        No instructions section; Description too short

Sections Found:

Section              Status
─────────────────────────────
Instructions         ✓
Available Tools      ✗
Workflow             ✗

Errors:
  ✗ Missing required fields: description
  ✗ Missing sections: Available Tools, Workflow
  ✗ Available Tools section is empty or not found

Warnings:
  ⚠ Skill completeness issues: Skill definition too short...
  ⚠ Clarity issues: Clear instructions section not found...

Recommendations:
  • Skill quality score is low (45/100)
  • Review error messages above and fix critical issues
  • Ensure all required sections are present
  • Fix 2 error(s) before publishing
```

### JSON Output

```json
{
  "skill_name": "pr-reviewer",
  "skill_path": "/path/to/SKILL.md",
  "passed": true,
  "quality_score": 95,
  "checks": [
    {
      "name": "File Existence",
      "passed": true,
      "score": 1.0,
      "message": "Skill file exists and is readable",
      "severity": "info"
    },
    {
      "name": "Required Sections",
      "passed": true,
      "score": 1.0,
      "message": "All required sections present",
      "severity": "info"
    }
  ],
  "sections": {
    "Instructions": true,
    "Available Tools": true,
    "Workflow": true,
    "Examples": true
  },
  "frontmatter": {
    "name": "pr-reviewer",
    "description": "Review pull requests with AI assistance",
    "role": "dev"
  },
  "errors": [],
  "warnings": []
}
```

## Best Practices

### 1. **Write Clear Instructions**
- Use numbered lists for steps
- Be specific about what the skill does
- Include prerequisites if needed

### 2. **Document All Tools**
- List every tool in a table format
- Include purpose and key parameters
- Show example usage

### 3. **Provide Examples**
- Include at least 2 concrete examples
- Show different use cases
- Explain expected outcomes

### 4. **Use Consistent Formatting**
- Use standard markdown headings
- Maintain consistent punctuation
- Align table columns properly

### 5. **Keep Descriptions Meaningful**
- Write 30+ character descriptions
- Explain when to use the skill
- Mention any dependencies

## Next Steps

After validation passes with a score ≥ 70:

1. **Publish the skill** - Make it available to other agents
2. **Measure impact** - Run Phase B to measure agent performance improvement
3. **Monitor usage** - Track adoption and user feedback
4. **Iterate** - Update based on real-world usage data

## Troubleshooting

### Low Quality Score?

**Check the following:**
- Ensure all 9 checks pass
- Add missing required sections
- Increase documentation length
- Provide concrete examples
- Review error and warning messages

### Frontmatter Issues?

**Valid frontmatter format:**
```yaml
---
name: your-skill-name
description: >-
  Multi-line description
  can span multiple lines
other_field: value
---
```

### Markdown Parsing Issues?

**Common problems:**
- Unmatched brackets: `[text` without closing `]`
- Unmatched parentheses: `(text` without closing `)`
- Invalid heading syntax: `# Heading` (use single space after `#`)

## For More Information

- See [Skill Evaluation Integration](../docs/SKILL_EVALUATION_INTEGRATION.md) for the full evaluation framework
- See [Agent Skills Format](https://agentskills.io) for the agentskills.io specification
