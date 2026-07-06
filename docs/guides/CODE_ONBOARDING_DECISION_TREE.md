# Code Onboarding Decision Tree - Quick Reference

**Date**: May 6, 2026  
**Purpose**: Quick decision guide for which command to use

---

## Decision Tree

```
What do you want to do?
│
├─ Build domain knowledge base?
│  └─ YES → Use: keel kg onboard
│           Purpose: Extract business requirements from Confluence
│           Output: Domain knowledge in KG
│           Timeline: 5-10 minutes
│           Example: keel kg onboard --domain cwow-facility --confluence-space CWOV
│
├─ Map code to business requirements?
│  └─ YES → Use: keel code onboard --kg
│           Purpose: Analyze code + map to business context
│           Output: kg-context.md (code + business)
│           Timeline: 5-10 minutes
│           Example: keel code onboard --path ./facility-service --kg
│
├─ Need better code structure analysis?
│  └─ YES → Use: keel code onboard --kg --graphify
│           Purpose: Analyze code structure + map to business
│           Output: kg-context.md with Graphify analysis
│           Timeline: 5-10 minutes
│           Example: keel code onboard --path ./facility-service --kg --graphify
│
└─ Need structured entity queries?
   └─ YES → Use: keel code onboard --kg --extract-entities
            Purpose: Full entity extraction and relationship building
            Output: Structured entities in KG
            Timeline: 10-15 minutes
            Example: keel code onboard --path ./facility-service --kg --extract-entities
```

---

## Your Goal: Map Code Context to Business Requirements

```
Your Goal
    ↓
Map code context to business requirements
    ↓
Which command?
    ↓
keel code onboard --kg ✅
    ↓
Why?
├─ Analyzes code structure (Graphify)
├─ Queries KG for business requirements
├─ Builds hybrid context (code + business)
├─ Generates domain-aware skills
└─ No unnecessary entity extraction
    ↓
Result: Code context MAPPED to business requirements ✅
```

---

## Command Comparison Matrix

| Feature | `kg onboard` | `code onboard --kg` | `code onboard --kg --graphify` | `code onboard --kg --extract-entities` |
|---------|-------------|-------------------|-------------------------------|--------------------------------------|
| **Input** | Confluence | Code | Code | Code |
| **Analyzes Code** | ❌ | ✅ | ✅ | ✅ |
| **Analyzes Business** | ✅ | ✅ | ✅ | ✅ |
| **Code Structure** | ❌ | Basic | Advanced | Advanced |
| **Maps Code to Business** | ❌ | ✅ | ✅ | ✅ |
| **Entity Extraction** | ❌ | ❌ | ❌ | ✅ |
| **Timeline** | 5-10 min | 5-10 min | 5-10 min | 10-15 min |
| **For Your Goal** | Setup | ✅ YES | ✅ Better | ❌ Overkill |

---

## Workflow for Your Goal

### Step 1: One-Time Setup
```bash
# Onboard domain knowledge from Confluence
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Result: Domain knowledge in KG
# - SLAs: Response time < 100ms, Availability > 99.9%
# - Integration: FHIR API, OAuth 2.0
# - Security: HIPAA compliance, AES-256 encryption
# - Performance: 10K concurrent users, DB latency < 50ms
```

### Step 2: For Each Codebase
```bash
# Map code to business requirements
keel code onboard --path ./facility-service --kg

# Result: kg-context.md with code + business requirements
# - Code structure (Graphify)
# - Business requirements (from KG)
# - Repository overview (GitIngest)
```

### Step 3: (Optional) Better Code Structure
```bash
# Add Graphify analysis for better code understanding
keel code onboard --path ./facility-service --kg --graphify

# Result: kg-context.md with detailed code structure analysis
# - Code relationships
# - Code communities/modules
# - Architectural insights
```

---

## Entity Extraction: Do You Need It?

### You DON'T need it if:
- ✅ Your goal is to map code context to business requirements
- ✅ You just need the information in kg-context.md
- ✅ You want fast execution (5-10 minutes)
- ✅ You don't need programmatic entity queries

### You DO need it if:
- ❌ You need to query SLAs programmatically
- ❌ You need to query integration specs programmatically
- ❌ You need to build entity relationship graphs
- ❌ You need structured entity analysis

---

## Quick Answer to Your Questions

### Q1: How is `code onboard --kg` different from `kg onboard`?

| Aspect | `kg onboard` | `code onboard --kg` |
|--------|-------------|-------------------|
| Input | Confluence documents | Code repository |
| Purpose | Build knowledge base | Map code to business |
| Analyzes | Business requirements | Code + business |
| Output | Business rules in KG | kg-context.md |

**Answer**: Different inputs and purposes. `kg onboard` builds the knowledge base, `code onboard --kg` maps code to it.

---

### Q2: Do we really need full entity extraction?

**Answer**: NO, not for your goal.

- Your goal: Map code context to business requirements
- Entity extraction is overkill
- Light mode (default) is sufficient
- Use `--extract-entities` only if you need structured entity queries

---

### Q3: Does `code onboard --kg` help with your goal?

**Answer**: YES, it's exactly what you need.

```
Code Repository
    ↓
code onboard --kg
    ├─ Analyze code structure (Graphify)
    ├─ Query KG for business requirements
    └─ Build hybrid context (code + business)
    ↓
Result: Code context MAPPED to business requirements ✅
```

---

## Recommended Commands for Your Goal

### Minimal Setup (Just the essentials)
```bash
# Step 1: Onboard domain knowledge (one-time)
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Step 2: Map code to business requirements (per codebase)
keel code onboard --path ./facility-service --kg
```

### Enhanced Setup (Better code understanding)
```bash
# Step 1: Onboard domain knowledge (one-time)
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Step 2: Map code to business requirements with Graphify (per codebase)
keel code onboard --path ./facility-service --kg --graphify
```

### Full Setup (If you need entity queries later)
```bash
# Step 1: Onboard domain knowledge (one-time)
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Step 2: Map code to business requirements with full extraction (per codebase)
keel code onboard --path ./facility-service --kg --extract-entities
```

---

## Summary

| Question | Answer | Command |
|----------|--------|---------|
| **Build domain knowledge?** | Use kg onboard | `keel kg onboard` |
| **Map code to business?** | Use code onboard --kg | `keel code onboard --kg` |
| **Need entity extraction?** | NO (for your goal) | Don't use `--extract-entities` |
| **Want better code analysis?** | Use --graphify | `keel code onboard --kg --graphify` |

**Your recommended workflow**:
```bash
# One-time
keel kg onboard --domain cwow-facility --confluence-space CWOV --release-aware

# Per codebase
keel code onboard --path ./facility-service --kg
```

**Result**: Code context mapped to business requirements ✅
