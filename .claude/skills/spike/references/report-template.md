# Spike Phase 3 -- Report & Presentation Templates

## Step 3: Save Research Report

Save the complete spike report to `.claude/docs/research/spike-{topic}.md`:

```markdown
# Spike Report: {topic}

## Question
{The original spike question}

## Verdict: {GO / NO-GO / INCONCLUSIVE}
**Confidence**: {HIGH / MEDIUM / LOW}
**Decisive factor**: {one-sentence summary of why}

## Investigation Parameters
- Time budget: {duration}
- Mode: {RESEARCH-ONLY / PROTOTYPE}
- Date: {date}

## Success Criteria Evaluation
| Criterion | Evidence | Met? |
|-----------|----------|------|
| {criterion 1} | {evidence summary} | {YES / NO / PARTIAL} |
| {criterion 2} | {evidence summary} | {YES / NO / PARTIAL} |

## Sub-question Findings
### {Sub-question 1}
- Finding: {description}
- Evidence: {sources and data}
- Assessment: {FEASIBLE / NOT_FEASIBLE / UNKNOWN}

### {Sub-question 2}
- Finding: {description}
- Evidence: {sources and data}
- Assessment: {FEASIBLE / NOT_FEASIBLE / UNKNOWN}

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {risk 1} | {H/M/L} | {H/M/L} | {strategy} |

## Prototype Results (if applicable)
- Tested: {what was tested}
- Result: {VALIDATED / INVALIDATED / INCONCLUSIVE}
- Evidence: {observations}

## Architecture Compatibility
- Assessment: {COMPATIBLE / REQUIRES_CHANGES / INCOMPATIBLE}
- Required changes: {list, if any}

## Alternatives Considered
| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| {alt 1} | {pros} | {cons} | {recommendation} |

## Recommendation
{GO / NO-GO / INCONCLUSIVE with detailed reasoning}

### If GO
- Next step: {/add-feature or /start-feature}
- Key constraints to carry forward: {list}
- Risks to monitor: {list}

### If NO-GO
- Decisive blocker: {description}
- Suggested alternatives: {list}

### If INCONCLUSIVE
- Missing evidence: {what we still need}
- Suggested follow-up: {description}
```


## Step 4: Present to User

Present the spike result to the user:

```markdown
## Spike Result: {topic}

### Verdict: {GO / NO-GO / INCONCLUSIVE}
**Confidence**: {HIGH / MEDIUM / LOW}

### Question
{The original spike question}

### Evidence Summary
{3-5 bullet points of key findings from Researcher}

### Feasibility Assessment (Codex)
{3-5 bullet points of key analysis from Feasibility Analyst}

### Risks
{Top 2-3 risks with likelihood and impact}

### Prototype Result (if applicable)
{What was tested and what the result was}

### Success Criteria Check
| Criterion | Met? | Evidence |
|-----------|------|----------|
| {criterion} | {YES/NO/PARTIAL} | {brief evidence} |

### Codex Evaluation
{Codex's synthesized reasoning for the verdict}
{Confidence level and decisive factor}

### Next Steps
**If GO:**
1. Proceed with `/add-feature` or `/start-feature` for implementation
2. Key constraints to carry forward: {list}
3. Risks to monitor during implementation: {list}

**If NO-GO:**
1. Decisive blocker: {description}
2. Alternatives to consider: {list}

**If INCONCLUSIVE:**
1. Missing evidence: {what we still need}
2. Consider a follow-up spike with narrower scope

---
Full report saved to: `.claude/docs/research/spike-{topic}.md`

Shall we proceed with the recommended next step?
```

---

## Output Files

| File | Author | Purpose |
|------|--------|---------|
| `.claude/docs/research/spike-{topic}-research.md` | Researcher | External research findings |
| `.claude/docs/research/spike-{topic}-feasibility.md` | Feasibility Analyst | Technical feasibility analysis (Codex-driven) |
| `.claude/docs/research/spike-{topic}.md` | Lead | Final spike report (decision document) |
| `.claude/spikes/{topic}/` | Feasibility Analyst | Prototype code (PROTOTYPE mode only) |

