# OpenSkill Compliance Mapping

**Document Version**: 1.0  
**Date**: May 2, 2026  
**Status**: Reference Document

---

## Overview

This document maps DVA evaluation framework components to the OpenSkill format as recommended by Claude's skill creator tool. It ensures our evaluation system is compatible with the broader skill ecosystem.

---

## 1. OpenSkill Format Specification

### 1.1 Skill Metadata (YAML Frontmatter)

**OpenSkill Standard**:
```yaml
---
name: skill-name
description: >-
  One-line description of what the skill does
tags: [category, use-case, domain]
version: 1.0.0
author: creator-name
license: MIT
created: 2026-05-02
updated: 2026-05-02
---
```

**DVA Implementation**:
```python
# From SKILL.md frontmatter
@dataclass
class SkillMetadata:
    name: str
    description: str
    tags: List[str]
    version: str  # NEW: Add version tracking
    author: str   # NEW: Add author tracking
    license: str  # NEW: Add license tracking
    created: datetime
    updated: datetime
```

**Mapping Status**: ✅ Mostly Complete (need to add version, author, license)

---

### 1.2 Skill Structure

**OpenSkill Standard**:
```
SKILL.md
├── Frontmatter (metadata)
├── Overview (optional)
├── Instructions (required)
├── Available Tools (required)
├── Workflow (required)
├── Examples (recommended)
├── Related Skills (optional)
└── Notes (optional)
```

**DVA Implementation**:
```python
# From validator.py
REQUIRED_SECTIONS = {"Instructions", "Available Tools", "Workflow"}
OPTIONAL_SECTIONS = {"Overview", "Examples", "Related Skills", "Notes"}
```

**Mapping Status**: ✅ Complete

---

## 2. Evaluation Metrics Mapping

### 2.1 Quantitative Metrics

| OpenSkill Metric | DVA Implementation | Unit | Range | Notes |
|------------------|-------------------|------|-------|-------|
| **Accuracy** | `accuracy` in metrics.py | Ratio | 0-1 | Exact match with expected output |
| **F1 Score** | `f1_score` in metrics.py | Ratio | 0-1 | Harmonic mean of precision/recall |
| **BLEU Score** | `bleu_score` in metrics.py | Ratio | 0-1 | N-gram overlap with reference |
| **Latency** | `latency_ms` in runner.py | Milliseconds | 0-∞ | Time to generate response |
| **Token Usage** | `tokens_used` in runner.py | Count | 0-∞ | Input + output tokens |
| **Cost** | `cost_usd` in metrics.py | USD | 0-∞ | API call cost |

**Status**: ✅ All Implemented

---

### 2.2 Qualitative Metrics (1-5 Scale, LLM-Judged)

| OpenSkill Metric | DVA Implementation | Threshold | Judge | Notes |
|------------------|-------------------|-----------|-------|-------|
| **Helpfulness** | `helpfulness` in llm_judges.py | 3.0 | Vertex AI/Claude/GPT-4 | Does it help solve the problem? |
| **Clarity** | `clarity` in llm_judges.py | 3.0 | Vertex AI/Claude/GPT-4 | Is the output clear and understandable? |
| **Relevance** | `relevance` in llm_judges.py | 3.0 | Vertex AI/Claude/GPT-4 | Is the output relevant to the input? |
| **Safety** | `safety` in llm_judges.py | 3.0 | Vertex AI/Claude/GPT-4 | Does it avoid harmful outputs? |
| **Completeness** | `completeness` in llm_judges.py | 3.0 | Vertex AI/Claude/GPT-4 | Does it fully address the request? |

**Status**: ✅ All Implemented

---

### 2.3 Boolean Metrics

| OpenSkill Metric | DVA Implementation | Notes |
|------------------|-------------------|-------|
| **Contains Hallucination** | `contains_hallucination` in llm_judges.py | Detected via LLM judgment |
| **Is Complete** | `is_complete` in validator.py | Structural completeness check |
| **Meets Requirements** | `meets_requirements` in validator.py | Validation check |

**Status**: ✅ All Implemented

---

## 3. Evaluation Process Mapping

### 3.1 Baseline Evaluation

**OpenSkill Standard**:
> Establish baseline performance without the skill to measure impact

**DVA Implementation**:
```python
# From runner.py - SkillImpactEvaluator
baseline_runner = EvaluationRunner(
    agent_fn=baseline_agent_fn,  # Agent without skill
    dataset=dataset,
    metrics=metrics,
    eval_id=f"baseline-{uuid}",
    agent_name=agent_name,
    judge_type=judge_type,
)
baseline_result = await baseline_runner.run()
```

**Mapping Status**: ✅ Complete

---

### 3.2 Impact Evaluation

**OpenSkill Standard**:
> Measure performance with the skill enabled

**DVA Implementation**:
```python
# From runner.py - SkillImpactEvaluator
impact_runner = EvaluationRunner(
    agent_fn=agent_fn,  # Agent with skill
    dataset=dataset,
    metrics=metrics,
    eval_id=f"impact-{uuid}",
    agent_name=agent_name,
    judge_type=judge_type,
    skill_name=skill_name,
)
impact_result = await impact_runner.run()
```

**Mapping Status**: ✅ Complete

---

### 3.3 Delta Calculation

**OpenSkill Standard**:
> Calculate improvement (delta) between baseline and impact

**DVA Implementation**:
```python
# From runner.py - SkillImpactEvaluator
@staticmethod
def _calculate_deltas(baseline_metrics, impact_metrics):
    deltas = {}
    for metric_name, baseline_score in baseline_metrics.items():
        impact_score = impact_metrics[metric_name]
        metric = get_metric(metric_name)
        
        if metric.lower_is_better:
            delta = baseline_score - impact_score  # Negative = improvement
        else:
            delta = impact_score - baseline_score  # Positive = improvement
        
        deltas[metric_name] = delta
    return deltas
```

**Mapping Status**: ✅ Complete

---

### 3.4 Quality Scoring

**OpenSkill Standard**:
> Aggregate metrics into 0-100 quality score

**DVA Implementation**:
```python
# NEW: To be implemented in Phase 1
@dataclass
class QualityScorer:
    def calculate_quality_score(
        self,
        metrics: Dict[str, float],
        weights: Dict[str, float],
    ) -> int:
        """Calculate 0-100 quality score from metrics."""
        # Normalize metrics to 0-1 range
        # Apply weights
        # Aggregate
        # Scale to 0-100
        pass
```

**Mapping Status**: ⚠️ Partial (needs implementation)

---

### 3.5 Certification

**OpenSkill Standard**:
> Assign certification level based on quality score

**DVA Implementation**:
```python
# NEW: To be implemented in Phase 5
class CertificationLevel(Enum):
    CERTIFIED = "CERTIFIED"  # Score ≥ 80
    CONDITIONAL = "CONDITIONAL"  # Score 60-79
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"  # Score < 60
    DEPRECATED = "DEPRECATED"  # Older version

@dataclass
class SkillCertification:
    skill_id: str
    level: CertificationLevel
    quality_score: int
    certification_date: datetime
    expiration_date: Optional[datetime]
    reason: str
    requirements_met: List[str]
    requirements_unmet: List[str]
```

**Mapping Status**: 🔴 Not Implemented

---

## 4. Evaluation Report Format

### 4.1 OpenSkill Report Structure

```json
{
  "skill_id": "skill-name",
  "skill_version": "1.0.0",
  "evaluation_id": "eval-abc123",
  "evaluation_date": "2026-05-02T08:34:00Z",
  "evaluator": {
    "agent_name": "support-agent",
    "agent_version": "1.0.0"
  },
  "dataset": {
    "dataset_id": "qa-dataset",
    "sample_count": 100
  },
  "metrics": {
    "quantitative": {
      "accuracy": 0.92,
      "f1_score": 0.88,
      "bleu_score": 0.85,
      "latency_ms": 245,
      "tokens_used": 1250,
      "cost_usd": 0.15
    },
    "qualitative": {
      "helpfulness": 4.5,
      "clarity": 4.3,
      "relevance": 4.7,
      "safety": 4.9,
      "completeness": 4.2
    },
    "boolean": {
      "contains_hallucination": false,
      "is_complete": true,
      "meets_requirements": true
    }
  },
  "quality_score": 85,
  "certification": {
    "level": "CERTIFIED",
    "date": "2026-05-02T08:34:00Z",
    "expiration": "2027-05-02T08:34:00Z"
  },
  "impact": {
    "baseline_metrics": {
      "accuracy": 0.78
    },
    "impact_metrics": {
      "accuracy": 0.92
    },
    "deltas": {
      "accuracy": 0.14
    },
    "effectiveness_score": 8.5
  },
  "recommendations": [
    "Improve clarity score by adding more examples",
    "Consider optimizing latency for real-time use cases"
  ]
}
```

### 4.2 DVA Implementation

```python
# From skill_evaluator.py - SkillEvaluationReporter
@dataclass
class SkillEvaluationReport:
    skill_id: str
    skill_version: str
    evaluation_id: str
    evaluation_date: datetime
    evaluator: Dict[str, str]
    dataset: Dict[str, Any]
    metrics: Dict[str, Any]
    quality_score: int
    certification: Dict[str, Any]
    impact: Dict[str, Any]
    recommendations: List[str]
    
    def to_openskill_format(self) -> Dict[str, Any]:
        """Convert to OpenSkill-compliant JSON."""
        pass
    
    def to_json(self) -> str:
        """Export as JSON."""
        pass
    
    def to_csv(self) -> str:
        """Export as CSV."""
        pass
```

**Mapping Status**: ✅ Mostly Complete (needs OpenSkill export)

---

## 5. Skill Source Tracking

### 5.1 Agent-Generated Skills

**Characteristics**:
- Created via `dva skill generate`
- AI-generated using Claude/Gemini/GPT-4
- Follows OpenSkill format by default
- Auto-validated on creation
- Includes generation metadata

**DVA Tracking**:
```python
@dataclass
class SkillMetadata:
    source: str = "agent-generated"
    generated_by: str  # Model name (claude-3-5-sonnet, gemini-2.5-flash, etc.)
    generation_date: datetime
    generation_config: Dict[str, Any]  # Model params, temperature, etc.
    generation_prompt: str  # The prompt used to generate
```

**Status**: ⚠️ Partial (need to track generation metadata)

---

### 5.2 User-Generated Skills

**Characteristics**:
- Installed via `dva skill install`
- From GitHub repositories or local sources
- May not follow OpenSkill format
- Manual validation required
- Includes installation metadata

**DVA Tracking**:
```python
@dataclass
class SkillMetadata:
    source: str = "user-generated"
    source_url: str  # GitHub URL or local path
    installation_date: datetime
    installed_by: str  # User name or email
    installation_method: str  # "github", "local", "registry"
```

**Status**: ⚠️ Partial (need to track installation metadata)

---

## 6. Compliance Checklist

### 6.1 Metadata Compliance

- [ ] Skill name (required)
- [ ] Skill description (required)
- [ ] Skill tags (recommended)
- [ ] Skill version (required for OpenSkill)
- [ ] Skill author (recommended)
- [ ] Skill license (recommended)
- [ ] Creation date (recommended)
- [ ] Update date (recommended)

**Status**: ⚠️ Partial (missing version, author, license)

---

### 6.2 Structure Compliance

- [x] Frontmatter with YAML
- [x] Instructions section
- [x] Available Tools section
- [x] Workflow section
- [x] Examples section (optional)
- [x] Related Skills section (optional)
- [x] Notes section (optional)

**Status**: ✅ Complete

---

### 6.3 Evaluation Compliance

- [x] Quantitative metrics (accuracy, F1, BLEU, latency, tokens, cost)
- [x] Qualitative metrics (helpfulness, clarity, relevance, safety, completeness)
- [x] Boolean metrics (hallucination, completeness, requirements)
- [x] Baseline evaluation
- [x] Impact evaluation
- [x] Delta calculation
- [ ] Quality scoring (0-100)
- [ ] Certification system

**Status**: ⚠️ Partial (missing quality scoring and certification)

---

### 6.4 Reporting Compliance

- [x] Structured JSON report
- [x] Metric summary
- [x] Impact analysis
- [ ] Certification status
- [ ] Recommendations
- [ ] OpenSkill format export

**Status**: ⚠️ Partial (missing certification and recommendations)

---

## 7. Implementation Roadmap

### Phase 1: Core Compliance
- [ ] Add version, author, license to skill metadata
- [ ] Implement quality scoring algorithm
- [ ] Create OpenSkill format validator
- [ ] Add OpenSkill export functionality

### Phase 5: Certification
- [ ] Implement certification system
- [ ] Add certification tracking
- [ ] Create certification reports

### Phase 4: Recommendations
- [ ] Implement recommendation engine
- [ ] Generate improvement suggestions
- [ ] Add best practices guidance

---

## 8. References

### OpenSkill Resources
- [OpenSkill GitHub Repository](https://github.com/anthropics/skills)
- [Claude Skill Creator Documentation](https://docs.anthropic.com/skills)
- [Skill Format Specification](https://github.com/anthropics/skills/blob/main/SKILL_FORMAT.md)

### DVA Implementation Files
- `agentic-cli/src/agentic_cli/evaluation/metrics.py` - Metric definitions
- `agentic-cli/src/agentic_cli/evaluation/runner.py` - Evaluation execution
- `agentic-cli/src/agentic_cli/evaluation/validator.py` - Skill validation
- `agentic-cli/src/agentic_cli/evaluation/skill_evaluator.py` - Skill evaluation
- `agentic-cli/src/agentic_cli/commands/eval.py` - CLI commands

---

**Document Status**: Ready for Implementation  
**Last Updated**: May 2, 2026  
**Next Review**: May 9, 2026
