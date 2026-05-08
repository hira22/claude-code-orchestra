---
name: troubleshoot
description: Diagnose errors and bugs with structured root cause analysis and fix planning.
metadata:
  short-description: Codex-first error/bug diagnosis with Agent Teams (Diagnosis phase)
---

# Troubleshoot

**Codex-first error/bug diagnosis skill leveraging Codex deep reasoning, Opus 1M context, and Agent Teams.**

## Overview

This skill handles the diagnosis phases (Phase 1-3) with a **Codex-first approach**: Codex CLI is consulted proactively in every phase for pattern recognition, hypothesis evaluation, root cause reasoning, and fix validation. Fix implementation is done via `/team-implement`, and review via `/team-review`.

```
/troubleshoot <error description>   <- This skill (diagnosis & fix planning)
    | After approval
/team-implement                     <- Parallel fix implementation
    | After completion
/team-review                        <- Parallel review (regression check)
```

## Workflow

```
Phase 1: REPRODUCE & UNDERSTAND (Opus 1M context + Codex Initial Analysis + Claude Lead)
  Opus subagent analyzes the error context, Codex generates initial hypotheses,
  Claude gathers details from the user
    |
Phase 2: DIAGNOSE (Agent Teams -- Parallel, Codex-driven)
  Root Cause Analyst (Codex mandatory) <-> Impact Investigator (Opus + Codex) communicate bidirectionally
  Both teammates consult Codex for deep reasoning throughout analysis
    |
Phase 3: FIX PLAN & APPROVE (Codex Validation + Claude Lead + User)
  Integrate diagnosis results, validate fix plan with Codex, get user approval
```

---

## Phase 1: REPRODUCE & UNDERSTAND (Opus Subagent + Codex + Claude Lead)

**Reproduce the error and gather full context with Opus subagent's 1M context, then consult Codex for initial hypothesis generation, while Claude interacts with the user.**

> Main orchestrator context is precious. Large-scale error context analysis is delegated to Opus subagent (1M context).
> Codex is consulted early for pattern recognition and hypothesis generation.

### Step 1: Gather Error Details from User

Ask the user to provide:

1. **Error message / stack trace**: Full error output
2. **Reproduction steps**: How to trigger the error
3. **Expected vs actual behavior**: What should happen vs what happens
4. **Environment**: OS, Python version, dependency versions
5. **Recent changes**: What changed before the error appeared (if known)

### Step 2: Reproduce & Analyze with Opus Subagent

Use a general-purpose subagent (Opus) to reproduce and analyze:

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Investigate this error in the codebase:

    Error: {error message / stack trace}
    Reproduction: {steps from user}

    Tasks:
    1. Try to reproduce the error:
       - Run the failing command/test
       - Capture full error output with stack trace
    2. Analyze the error context:
       - Read all files mentioned in the stack trace
       - Trace the execution flow leading to the error
       - Identify the immediate cause (what line throws/fails)
    3. Gather surrounding context:
       - Check recent git history for related changes: git log --oneline -20
       - Look for related tests and whether they pass/fail
       - Check if similar patterns exist elsewhere in the codebase

    Use Bash, Glob, Grep, and Read tools to investigate thoroughly.

    Save analysis to .claude/docs/research/troubleshoot-{issue}-context.md
    Return concise summary (5-7 key findings).
```

### Step 2.5: Codex Initial Error Pattern Analysis

Consult Codex for initial hypothesis generation before creating the Bug Report:

```bash
codex exec --sandbox read-only "
Objective: Analyze this error and generate initial hypotheses for root cause.
Context:
- Error: {error message / stack trace}
- Failing location: {file:line from Opus subagent analysis}
- Execution flow: {call chain from Opus subagent analysis}
Constraints:
- Focus on root cause categories (state mutation, boundary, concurrency, dependency, type/contract)
- Rank hypotheses by likelihood
- Suggest specific code areas to investigate for each hypothesis
Output format:
## Error Pattern Recognition
## Hypotheses (ranked by likelihood)
## Investigation Plan (per hypothesis)
## Known Similar Patterns
"
```

Use Codex's analysis to strengthen the Initial Hypotheses section of the Bug Report.

### Step 3: Create Bug Report

Combine error details + codebase analysis + Codex initial hypotheses into a "Bug Report":

```markdown
## Bug Report: {issue}

### Error
- Message: {error message}
- Location: {file:line}
- Stack trace: {key frames}

### Reproduction
- Steps: {numbered list}
- Reproducibility: {always / intermittent / environment-specific}

### Immediate Context
- Failing code: {file:line and surrounding logic}
- Call chain: {caller -> ... -> failing function}
- Recent changes: {relevant git commits}

### Affected Area
- Files involved: {list}
- Related tests: {list with pass/fail status}

### Initial Hypotheses (informed by Codex analysis)
1. {Hypothesis A}: {brief reasoning} -- Codex confidence: {high/medium/low}
2. {Hypothesis B}: {brief reasoning} -- Codex confidence: {high/medium/low}
3. {Hypothesis C}: {brief reasoning} -- Codex confidence: {high/medium/low}

### Codex Pattern Recognition
- Error pattern: {Codex's classification of the error type}
- Known similar patterns: {any patterns Codex identified}
- Recommended investigation priority: {Codex's suggested order}
```

This bug report is passed to Phase 2 teammates as shared context.

---

## Phase 2: DIAGNOSE (Agent Teams — Parallel)

**Launch Root Cause Analyst and Impact Investigator in parallel via Agent Teams with bidirectional communication. Both teammates MUST consult Codex for deep reasoning tasks.**

Root Cause Analyst (Codex-driven) traces execution flow, evaluates hypotheses, designs fix approaches, and verifies correctness. Impact Investigator (Opus + Codex) traces git history, assesses blast radius, researches external context, and evaluates regression risk. The two teammates communicate bidirectionally -- findings from one inform the other's analysis scope.

See `references/team-prompts.md` for the full Phase 2 teammate prompts and the bidirectional-communication example.

---
## Phase 3: FIX PLAN & APPROVE (Codex Validation + Claude Lead)

**Integrate Agent Teams diagnosis results, validate the fix plan with Codex, and request user approval.**

### Step 1: Synthesize Diagnosis

Read outputs from Phase 2:
- `.claude/docs/research/troubleshoot-{issue}-root-cause.md` -- Root cause analysis
- `.claude/docs/research/troubleshoot-{issue}-impact.md` -- Impact assessment

### Step 1.5: Codex Fix Plan Validation

Before presenting to the user, validate the fix plan with Codex:

```bash
codex exec --sandbox read-only "
Objective: Validate this fix plan for completeness and correctness.
Context:
- Root cause: {from Root Cause Analyst}
- Proposed fix: {recommended approach}
- Blast radius: {from Impact Investigator}
- Fix tasks: {task list}
Constraints:
- Check for missing edge cases
- Verify the fix addresses the root cause (not just symptoms)
- Identify potential new issues the fix could introduce
- Suggest additional test cases if needed
Output format:
## Validation Result (PASS / NEEDS_REVISION)
## Missing Coverage
## Potential New Issues
## Additional Test Cases Recommended
## Revised Task List (if needed)
"
```

If Codex returns NEEDS_REVISION, update the fix plan before presenting to user.

### Step 2: Create Fix Plan

Create task list using TodoWrite:

```python
{
    "content": "Fix {specific task}",
    "activeForm": "Fixing {specific task}",
    "status": "pending"
}
```

Task breakdown should follow `references/debug-patterns.md`.

Typical fix task structure:
1. **Write failing test** -- Reproduce the bug as a test case
2. **Apply fix** -- Implement the root cause fix
3. **Verify fix** -- Confirm the failing test now passes
4. **Check regressions** -- Run full test suite
5. **Fix collateral damage** -- Address blast radius items (if any)

### Step 3: Update CLAUDE.md

Add bug context to CLAUDE.md for cross-session persistence using the structured template covering error summary, root cause, fix approach, Codex validation, and regression risks.

See `references/output-templates.md` for the full CLAUDE.md update template.

### Step 4: Present to User

Present the diagnosis and fix plan covering reproduction result, root cause, impact assessment, fix plan, alternative approaches, and next steps.

See `references/output-templates.md` for the full diagnosis report template and output files table.

---

## Tips

- **Codex-first**: Every phase consults Codex. This is intentional -- Codex excels at deep code reasoning and pattern recognition that complements Opus's broad context analysis
- **Codex for hypothesis testing**: When hypotheses conflict, ask Codex to evaluate evidence for each. Codex is better at logical reasoning about code behavior than pattern matching
- **Phase 1**: Opus subagent (1M context) reproduces the error and gathers full context, then Codex generates initial hypotheses, while Claude collects details from the user
- **Phase 2**: Agent Teams bidirectional communication allows Root Cause Analyst (Codex-driven) and Impact Investigator (Opus + Codex) to converge on the true root cause
- **Phase 3**: Codex validates the fix plan before presenting to user. After approval, proceed to implementation with `/team-implement`
- **Competing Hypotheses**: If Phase 2 yields inconclusive results, consider spawning additional teammates with adversarial hypotheses (see `/team-review` competing hypotheses pattern)
- **Quick bugs**: For obvious single-file bugs, skip this skill and fix directly -- use this skill for non-trivial bugs where root cause is unclear
- **Ctrl+T**: Toggle task list display
- **Shift+Up/Down**: Navigate between teammates (when using Agent Teams)
