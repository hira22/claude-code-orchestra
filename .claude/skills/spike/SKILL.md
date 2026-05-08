---
name: spike
description: Time-boxed feasibility investigation producing a go/no-go decision document.
metadata:
  short-description: Codex-first time-boxed technical investigation with Agent Teams (Decision phase)
---

# Spike

**Codex-first time-boxed technical investigation skill leveraging Codex deep reasoning, Opus 1M context, and Agent Teams.**

## Overview

This skill handles time-boxed feasibility studies and technical investigations. It produces a **decision document** (go/no-go recommendation), NOT an implementation plan. After a GO decision, the user proceeds to `/add-feature` or `/start-feature` for actual implementation.

```
/spike <question or hypothesis>    <- This skill (investigation & decision)
    | After GO decision
/add-feature or /start-feature      <- Implementation planning
    | After approval
/team-implement                    <- Parallel implementation
```

### When to Use

| Situation | Example |
|-----------|---------|
| **Technology feasibility** | "Can we use WebSocket for real-time sync?" |
| **Library evaluation** | "Is DuckDB suitable for our analytics pipeline?" |
| **Architecture question** | "Should we use event sourcing for the order system?" |
| **Performance hypothesis** | "Can we serve 10k concurrent requests with this stack?" |
| **Migration risk** | "What would it take to migrate from REST to gRPC?" |
| **Integration question** | "Can we integrate with the Stripe Connect API for our use case?" |

### When NOT to Use

| Situation | Use Instead |
|-----------|-------------|
| Bug diagnosis | `/troubleshoot` |
| Known feature to implement | `/add-feature` or `/start-feature` |
| Simple library lookup | Direct research (Opus subagent) |
| Code review | `/team-review` |

### Investigation Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **RESEARCH-ONLY** | No code written. Pure analysis from docs, examples, and Codex reasoning. | Library evaluation, architecture questions, migration risk |
| **PROTOTYPE** | Small throwaway code to validate a specific technical question. Code is NOT production-quality. | Performance hypothesis, API integration feasibility, compatibility testing |

## Workflow

```
Phase 1: FRAME (Claude Lead + Codex Question Decomposition)
  Claude clarifies the spike question with the user, Codex decomposes into
  sub-questions and defines success criteria
    |
Phase 2: INVESTIGATE (Agent Teams -- Parallel, Codex-driven)
  Researcher (Opus) <-> Feasibility Analyst (Codex) communicate bidirectionally
  Optional: Codex prototype (workspace-write) for hands-on validation
    |
Phase 3: SYNTHESIZE (Codex Evaluation + Claude Lead + User)
  Codex evaluates all evidence against success criteria,
  produces go/no-go recommendation, Claude presents to user
```

---

## Phase 1: FRAME (Claude Lead + Codex Question Decomposition)

**Clarify the spike question with the user, then consult Codex to decompose it into a structured investigation plan.**

> A well-framed question is half the answer. Phase 1 ensures we investigate the right thing within the right constraints.

### Step 1: Gather Spike Parameters from User

Ask the user to provide:

1. **Question / Hypothesis**: What are we trying to find out? (e.g., "Can we use SQLite for multi-tenant data isolation?")
2. **Time budget**: How long should this investigation take? (e.g., 30 min, 1 hour, 2 hours)
3. **Investigation mode**: RESEARCH-ONLY or PROTOTYPE?
4. **Success criteria**: What evidence would make this a GO? (e.g., "Library supports X, performance meets Y threshold")
5. **Context**: Why is this question important now? What decision depends on it?

### Step 2: Codex Question Decomposition (MANDATORY)

Consult Codex to decompose the spike question into a structured investigation plan:

```bash
codex exec --sandbox read-only "
Objective: Decompose this spike question into a structured investigation plan.
Context:
- Spike question: {question/hypothesis from user}
- Investigation mode: {RESEARCH-ONLY or PROTOTYPE}
- Time budget: {time budget}
- Success criteria: {user's success criteria}
- Project context: {why this matters, what decision depends on it}
Constraints:
- Break the question into 3-5 concrete sub-questions that can be independently investigated
- For each sub-question, specify what evidence would confirm or deny it
- Identify the critical path (which sub-question is most decisive)
- Suggest the investigation approach for each sub-question
- Keep the plan achievable within the time budget
Output format:
## Question Decomposition
## Sub-questions (ranked by decisiveness)
## Evidence Needed (per sub-question)
## Investigation Approach
## Critical Path (which finding would short-circuit the spike)
## Risk of Inconclusive Result
"
```

### Step 3: Create Spike Brief

Combine user parameters + Codex decomposition into a "Spike Brief":

```markdown
## Spike Brief: {topic}

### Question
{The core question or hypothesis in one sentence}

### Parameters
- Time budget: {duration}
- Investigation mode: {RESEARCH-ONLY / PROTOTYPE}
- Started: {timestamp}
- Deadline: {timestamp}

### Success Criteria
- GO if: {conditions that make this a GO}
- NO-GO if: {conditions that make this a NO-GO}
- INCONCLUSIVE if: {what would leave us uncertain}

### Sub-questions (from Codex decomposition)
1. {Sub-question A}: Evidence needed: {description}
2. {Sub-question B}: Evidence needed: {description}
3. {Sub-question C}: Evidence needed: {description}

### Critical Path
{Which sub-question is most decisive -- investigate this first}

### Investigation Plan
- Researcher (Opus): {what to research externally}
- Feasibility Analyst (Codex): {what to analyze technically}
- Prototype (if applicable): {what to build and test}
```

This brief is passed to Phase 2 teammates as shared context.

---

## Phase 2: INVESTIGATE (Agent Teams -- Parallel)

**Launch Researcher and Feasibility Analyst in parallel via Agent Teams with bidirectional communication. Feasibility Analyst MUST consult Codex for all technical analysis.**

Researcher (Opus 1M context) gathers external evidence via WebSearch/WebFetch while Feasibility Analyst (Codex-driven) evaluates technical feasibility, architecture compatibility, and risks. The two teammates communicate bidirectionally -- Researcher's external findings change Analyst's scope, and Analyst's technical questions trigger new research.

See `references/team-prompts.md` for the full Phase 2 teammate prompts and the bidirectional-communication example.

---
## Phase 3: SYNTHESIZE (Codex Evaluation + Claude Lead)

**Integrate Agent Teams investigation results, have Codex evaluate evidence against success criteria, and produce a go/no-go recommendation.**

### Step 1: Gather Investigation Results

Read outputs from Phase 2:
- `.claude/docs/research/spike-{topic}-research.md` -- Researcher findings
- `.claude/docs/research/spike-{topic}-feasibility.md` -- Feasibility analysis (Codex-driven)
- `.claude/spikes/{topic}/` -- Prototype code and results (if PROTOTYPE mode)

### Step 2: Codex Final Evaluation (MANDATORY)

Consult Codex to synthesize all findings into a go/no-go recommendation:

```bash
codex exec --sandbox read-only "
Objective: Synthesize spike investigation findings and produce a go/no-go recommendation.
Context:
- Spike question: {original question}
- Success criteria: {from Spike Brief}
- Researcher findings: {summary of key findings}
- Feasibility assessment: {summary of Codex feasibility analysis per sub-question}
- Risks identified: {summary of risks}
- Prototype result (if any): {VALIDATED / INVALIDATED / INCONCLUSIVE}
Constraints:
- Evaluate each success criterion against the collected evidence
- Be explicit about confidence level (HIGH / MEDIUM / LOW)
- If GO, specify key constraints and risks to carry forward
- If NO-GO, explain the decisive blocker and suggest alternatives
- If INCONCLUSIVE, specify what additional investigation is needed
Output format:
## Evidence Summary (per success criterion)
## Verdict: GO / NO-GO / INCONCLUSIVE
## Confidence Level: HIGH / MEDIUM / LOW
## Decisive Factor
## If GO: Constraints and Risks to Carry Forward
## If GO: Recommended Next Skill (/add-feature or /start-feature)
## If NO-GO: Decisive Blocker and Alternatives
## If INCONCLUSIVE: What Additional Investigation Is Needed
"
```

### Step 3: Save Research Report

Save the complete spike report to `.claude/docs/research/spike-{topic}.md` using the structured template covering verdict, evidence, sub-question findings, risks, and recommendations.

See `references/report-template.md` for the full report template.

### Step 4: Present to User

Present the spike result to the user covering verdict, evidence summary, feasibility assessment, risks, and next steps.

See `references/report-template.md` for the full presentation template and output files table.

---

## Tips

- **Codex-first**: Every phase consults Codex. This is intentional -- Codex excels at structured reasoning about feasibility and trade-offs that complements Opus's broad research capabilities
- **Time budget discipline**: Respect the time budget. If investigation is taking too long, Codex can evaluate with partial evidence and mark the verdict as INCONCLUSIVE
- **Phase 1 is critical**: A well-decomposed question makes Phase 2 much more efficient. Invest time in framing the right sub-questions with Codex
- **Phase 2**: Agent Teams bidirectional communication allows Researcher (Opus) and Feasibility Analyst (Codex-driven) to converge on evidence-based assessment
- **Phase 3**: Codex synthesizes all findings into a decision. After a GO decision, proceed to `/add-feature` or `/start-feature` -- do NOT start implementation within the spike
- **PROTOTYPE mode**: Prototype code is throwaway. It lives in `.claude/spikes/` and is NOT production code. Its only purpose is to generate evidence for the decision
- **Short-circuit**: If Phase 2 discovers a hard blocker early, short-circuit to Phase 3 immediately. No need to complete all sub-questions if the answer is already clear
- **Inconclusive is OK**: Not every spike produces a clear answer. An INCONCLUSIVE result with documented unknowns is more valuable than a false GO
- **Reuse research**: Spike reports in `.claude/docs/research/` persist across sessions. Reference prior spikes before starting new ones on similar topics
- **Ctrl+T**: Toggle task list display
- **Shift+Up/Down**: Navigate between teammates (when using Agent Teams)
