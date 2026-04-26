# Agentic CLI Examples

This directory contains example scripts and workflows demonstrating the agentic-cli capabilities.

## Skill Evaluation Demo

### Overview

The `skill_evaluation_demo.py` script demonstrates the complete **skill evaluation workflow** using Vertex AI integration.

This is an end-to-end example showing:
1. **Dataset Creation** - Create evaluation datasets with test Q&A pairs
2. **Skill Validation** - Validate skill file structure and quality
3. **Impact Evaluation** - Measure how much a skill improves agent performance
4. **Result Interpretation** - Understand and act on evaluation results

### What It Shows

- Creating evaluation datasets programmatically
- Validating skill files (quality checks)
- Running async/parallel skill impact evaluations
- Using Vertex AI judges for response evaluation
- Interpreting effectiveness scores
- Saving and reporting results

### Running the Demo

```bash
# From the agentic-cli directory
python examples/skill_evaluation_demo.py
```

### Output

The script generates:
- **Console output** with progress updates and results
- **JSON report** saved to `examples/evaluations/`
- **Dataset files** saved to `examples/datasets/`

### Understanding the Workflow

#### Step 1: Create Dataset
```python
dataset_manager = DatasetManager(datasets_dir)
dataset = dataset_manager.create_dataset(
    dataset_id="customer-qa",
    name="Customer Support QA",
    description="Q&A pairs for testing customer support"
)

# Add test samples
dataset.add_sample(EvaluationSample(
    input="What is your return policy?",
    expected_output="We offer 30-day returns..."
))
```

#### Step 2: Validate Skill
```python
validator = SkillValidator(skill_file)
result = validator.validate()
# Returns: quality_score, passed flag, detailed checks
```

#### Step 3: Run Impact Evaluation
```python
evaluator = AsyncSkillEvaluator(
    agent_name="customer-support-bot",
    skill_name="customer-support",
    dataset=dataset,
    metrics=["accuracy", "helpfulness"],
    judge_type="anthropic"  # Vertex AI with fallback
)

results = await evaluator.evaluate(
    agent_fn=agent_with_skill,
    baseline_agent_fn=agent_without_skill
)
```

#### Step 4: Interpret Results
- **Baseline**: Agent performance without skill
- **With Skill**: Agent performance with skill enabled
- **Delta**: Improvement/degradation
- **Effectiveness**: 0-10 score indicating overall value

### Key Concepts

**Baseline vs With Skill:**
- Baseline measures agent on its own
- With Skill measures agent using the skill
- Difference shows skill's impact

**Effectiveness Score:**
- 8-10: Excellent (strong improvement)
- 6-8: Good (moderate improvement)
- 4-6: Fair (minor improvement or mixed)
- 0-4: Needs work (negative or minimal impact)

**Metrics Used:**
- **accuracy**: Exact match with expected output
- **bleu_score**: Text similarity (word overlap)
- **helpfulness**: LLM judge rating (1-5 scale)
- **latency_ms**: Response time
- **token_usage**: Tokens consumed

### Vertex AI Integration

The demo uses **Vertex AI Gemini** for qualitative evaluation (via VertexAIJudge).

For qualitative metrics (helpfulness, clarity, relevance, safety):
1. Agent response is sent to Vertex AI/Claude/GPT-4
2. Judge evaluates response on 1-5 scale
3. Scores are aggregated for final effectiveness rating

**Fallback Mechanism:**
- Primary: Vertex AI (Google Cloud)
- Fallback: Claude (Anthropic)
- Fallback: GPT-4 (OpenAI)

### Modifying the Demo

To adapt for your use case:

**Change Metrics:**
```python
config = SkillEvaluationConfig(
    ...
    metrics=["accuracy", "clarity", "relevance"],  # Your metrics
    ...
)
```

**Use Different Agents:**
```python
# Instead of mock agents, use your actual agents
agent_with_skill = my_custom_agent  # Your agent implementation
agent_without_skill = baseline_agent
```

**Change Judge:**
```python
evaluator = AsyncSkillEvaluator(
    ...
    judge_type="vertex-ai",  # or "anthropic" or "openai"
    ...
)
```

**Add More Samples:**
```python
for question, answer in my_qa_pairs:
    dataset.add_sample(EvaluationSample(
        input=question,
        expected_output=answer
    ))
```

### Output Files

After running, you'll find:

```
examples/
├── datasets/
│   └── customer-qa.json           # Evaluation dataset
├── evaluations/
│   └── customer-support_*.json    # Evaluation results
└── skills/
    └── SKILL.md                   # Example skill file
```

### Real-World Application

In production:
1. **Create datasets** from real customer Q&A or test cases
2. **Design skills** for specific use cases (customer support, coding, research)
3. **Evaluate periodically** to track skill effectiveness
4. **Iterate** based on results (improve low-scoring skills)
5. **Publish** validated skills with confidence metrics

### For More Information

- **Skill Validation**: See `docs/SKILL_VALIDATION_GUIDE.md`
- **Evaluation Framework**: See `docs/SKILL_EVALUATION_INTEGRATION.md`
- **Evaluation Plan**: See `docs/EVALUATION_FRAMEWORK_PLAN.md`

### Troubleshooting

**Q: Import errors when running the script?**
A: Make sure you're in the `agentic-cli` directory and have installed dev dependencies:
```bash
pip install -e ".[dev]"
```

**Q: How do I use my own agents?**
A: Replace `MockAgents.get_agent()` with your agent functions. They should be async functions taking `input_text` and returning `output_text`.

**Q: Can I use Vertex AI locally?**
A: Yes, but you need GCP credentials configured. Set up with:
```bash
gcloud auth application-default login
```

Then use `judge_type="vertex-ai"` in the evaluator.
