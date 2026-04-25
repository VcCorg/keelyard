# Skill Generator + Agent Evaluation Integration

## Overview

**The Problem**: Skill generator creates domain skills, but there's **NO WAY to measure if they actually help agents**.

**The Solution**: Integrate skill evaluation into the evaluation framework to validate and measure skill effectiveness.

---

## Three-Level Evaluation Strategy

### Level 1: Skill Quality Validation 
**After skill generation, before publishing**

```bash
agent eval validate-skill backend-dev-skill.md
```

Validates:
- ✅ YAML structure (front-matter, metadata)
- ✅ Required sections (Instructions, Tools, Workflow)
- ✅ Markdown formatting
- ✅ Tool reference validity
- ✅ No broken links

Produces: **Quality Score (0-100)**

---

### Level 2: Agent Performance Impact
**Measure if skill actually improves agent performance**

```bash
agent eval measure-skill-impact \
  --agent customer-support \
  --skill backend-dev-skill \
  --dataset qa-dataset
```

Compares:
- Agent WITHOUT skill (baseline)
- Agent WITH skill (test)
- Calculates deltas for each metric

Output:
```
Without Skill: 78% accuracy, 3.2/5 helpfulness, 2.5s latency
With Skill:    86% accuracy (+8%), 4.1/5 (+0.9), 2.8s (-0.3s)
Impact Score: 8.5/10 ✅ EFFECTIVE
```

---

### Level 3: Multi-Skill Interactions
**Evaluate how multiple skills work together (synergy)**

```bash
agent eval skill-combination \
  --agent my-agent \
  --skills skill1,skill2,skill3 \
  --measure synergy
```

Detects:
- Individual skill contributions
- Synergy bonuses (or penalties)
- Optimal skill combinations

---

## Implementation Roadmap: 8 Weeks

| Phase | Week | Feature | Command |
|-------|------|---------|---------|
| **A** | 1-2 | Quality Validation | `agent eval validate-skill` |
| **B** | 3-4 | Impact Measurement | `agent eval measure-skill-impact` |
| **C** | 5 | Skill Registry | `agent skill-registry` |
| **D** | 6 | Recommendations | `agent eval skill-recommend` |
| **E** | 7 | Integration | Code onboarding integration |
| **F** | 8 | Reports | HTML/JSON skill reports |

---

## New Evaluation Commands

### 1. Validate Skill
```bash
agent eval validate-skill <skill-path>
  --check structure        # YAML, sections
  --check completeness     # All required fields
  --check clarity          # Readability score
  --output json            # JSON report
```

### 2. Measure Skill Impact
```bash
agent eval measure-skill-impact
  --agent <agent-name>
  --skill <skill-name>
  --dataset <dataset-name>
  --baseline-agent <agent-without-skill>
  --metrics accuracy,helpfulness,latency
```

### 3. Test Skill Combinations
```bash
agent eval skill-combination
  --agent <agent-name>
  --skills skill1,skill2,skill3
  --dataset <dataset-name>
  --measure synergy
```

### 4. View Skill Info
```bash
agent eval skill-info <skill-name>
  # Shows:
  # - Quality score
  # - Impact metrics
  # - Effectiveness rating
  # - Usage statistics
  # - Version history
```

### 5. Recommend Skills
```bash
agent eval skill-recommend
  --agent <agent-name>
  --top 5
  --predict-improvement
  # Shows top 5 skills with predicted impact
```

---

## Data Model: Skill with Evaluation

### Extended Skill YAML
```yaml
---
name: developer-skill
description: Developer persona context
role: dev
domain: backend
created: 2026-04-25T14:30:00Z

# NEW: Evaluation Metrics
evaluation:
  quality_score: 92/100
  completeness: 0.95
  clarity: 4.2/5
  structure_valid: true
  last_validated: 2026-04-25T14:35:00Z
  
impact_metrics:
  tested_on_agents: 12
  average_improvement: 0.14  # 14%
  accuracy_delta: +0.12
  latency_delta: -0.05s
  helpfulness_delta: +0.8
  cost_delta: +0.002
  
effectiveness_rating: 4.7/5
adoption_count: 45
user_sentiment: 4.6/5
status: "verified"
---

# Skill content...
```

---

## Integration Points

### With Code Onboarding
```bash
agent code onboard <repo-url> --auto-skills
  → Generate skills
  → [NEW] Validate each skill (quality score)
  → [NEW] Measure initial effectiveness
  → Publish with quality badges

Output:
✅ backend-dev-skill (Quality: 92/100, Impact: +12%)
✅ backend-qa-skill (Quality: 88/100, Impact: +8%)
✅ backend-sm-skill (Quality: 85/100, Impact: +5%)
```

### With Agent Creation
```bash
agent project create my-agent --suggest-skills
  → Show available skills
  → [NEW] Display effectiveness scores
  → [NEW] Predict improvement per skill
  → Allow selection with confidence metrics

Output:
Top Skills for this agent:
1. backend-dev-skill (92/100) → Expected +12% accuracy
2. backend-qa-skill (88/100) → Expected +8% quality
3. backend-sm-skill (85/100) → Expected +5% clarity
```

### With Agent Evaluation
```bash
agent eval run my-agent --dataset dataset-1
  → [Existing] Run agent tests
  → [NEW] Measure with all skills enabled
  → [NEW] Measure with skills disabled
  → [NEW] Calculate skill contribution
  → Show breakdown of which skills helped most

Output:
Overall: 84% accuracy
├─ Backend-dev-skill contribution: +8%
├─ Backend-qa-skill contribution: +5%
└─ Backend-sm-skill contribution: +3%
```

---

## Complete End-to-End Workflow

```bash
# 1. Onboard repository with auto-skill generation
$ agent code onboard https://github.com/myteam/backend --auto-skills

✅ Analyzed backend repo (Python, FastAPI)
✅ Generated skills:
   - backend-dev-skill (Quality: 92/100)
   - backend-qa-skill (Quality: 88/100)
   - backend-sm-skill (Quality: 85/100)

# 2. Create agent with suggested skills
$ agent project create my-agent \
  --use-case rag \
  --domain backend \
  --auto-select-skills

✅ Created agent with:
   - RAG template
   - backend-dev-skill (predicted +12% improvement)
   - backend-qa-skill (predicted +8% improvement)

# 3. Prepare evaluation dataset
$ agent eval create-dataset backend-qa \
  --input-file qa-samples.csv

✅ Created dataset: 50 Q&A pairs

# 4. Run evaluation with skill impact measurement
$ agent eval run my-agent \
  --dataset backend-qa \
  --measure-skill-impact

Result without skills: 72% accuracy, 3.4/5 helpfulness
Result with skills:    84% accuracy (+12%), 4.2/5 (+0.8)
Skill Effectiveness:   9.2/10 ⭐⭐⭐⭐⭐

# 5. View in skill registry
$ agent skill-registry search backend --sort-by effectiveness

🥇 backend-dev-skill (v1.0)
   Effectiveness: 9.2/10
   Used by: 45 agents
   Avg improvement: +12%
   User rating: 4.8/5

# 6. Share evaluated skill
$ agent skill-publish backend-dev-skill \
  --include-evaluation-metrics

✅ Published backend-dev-skill with:
   - Quality score: 92/100 ✅
   - Impact metrics: +12% accuracy
   - Effectiveness: 9.2/10 ⭐
   - Status: Verified & Recommended
```

---

## Key Benefits

1. **Data-Driven Skills** - Stop guessing if skills work, measure it
2. **Skill Marketplace** - Build confidence with verified quality scores
3. **Agent Optimization** - Choose skills proven to improve performance
4. **Quality Assurance** - Catch poor skills before sharing
5. **ROI Tracking** - Know the exact value of each skill
6. **Continuous Improvement** - Iterate skills based on real metrics

---

## Success Metrics

- ✅ Validate 100% of generated skills in < 10 seconds
- ✅ Measure skill impact on 100-sample dataset in < 5 minutes
- ✅ Support skill version history with regression tracking
- ✅ Enable skill marketplace with verified badges
- ✅ Increase skill adoption by 3x with quality metrics
- ✅ < 5% false positive rate on "effective" claims

---

## Questions Answered

**Q: What if a skill doesn't help?**
A: Skills are marked with effectiveness scores (1-5 ⭐). Low-scoring skills can be improved and re-evaluated.

**Q: How do we handle skill versioning?**
A: Each skill version gets its own quality & impact scores, enabling users to compare versions and revert if needed.

**Q: Can skills hurt agent performance?**
A: Yes—we detect negative impact and flag skills with scores < 5/10 as "needs improvement".

**Q: How long to evaluate a skill?**
A: Quality validation: < 10 seconds. Impact measurement: < 5 minutes (for 100-sample dataset).

**Q: Do all skills need evaluation?**
A: No, but recommended. Users can skip evaluation, but skills without scores won't appear in marketplace.

