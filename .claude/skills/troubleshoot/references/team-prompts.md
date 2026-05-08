# Troubleshoot Phase 2 -- Teammate Prompts

**Launch Root Cause Analyst and Impact Investigator in parallel via Agent Teams with bidirectional communication. Both teammates MUST consult Codex for deep reasoning tasks.**

> Key difference from subagents: Teammates can communicate with each other.
> Root Cause Analyst's findings change Impact Investigator's scope, and Impact Investigator's context informs root cause analysis.

### Team Setup

```
Create an agent team for troubleshooting: {issue}

Spawn two teammates:

1. **Root Cause Analyst** — Uses Codex CLI as PRIMARY analysis engine for deep code reasoning
   Prompt: "You are the Root Cause Analyst for bug: {issue}.

   Your job: Identify the definitive root cause of this error through deep code analysis.
   Codex CLI is your PRIMARY tool for reasoning about code behavior.

   Bug Report:
   {bug report from Phase 1}

   Tasks:
   1. Trace the execution flow step by step from entry point to error
   2. Evaluate each hypothesis from the Bug Report:
      - Gather evidence FOR and AGAINST each hypothesis
      - Eliminate hypotheses that contradict the evidence
   3. Identify the root cause (not just the symptom):
      - What is the underlying defect?
      - Why does it manifest as this specific error?
      - Under what conditions does it trigger?
   4. Propose fix approaches (at least 2 alternatives):
      - Approach A: {description, pros, cons}
      - Approach B: {description, pros, cons}
      - Recommended approach with rationale

   ## Codex Analysis Protocol (MANDATORY)

   You MUST consult Codex for EACH of the following analysis tasks.
   Do NOT skip Codex consultation — it is the primary reasoning engine for this role.

   ### 1. Execution Flow Tracing
   For complex control flow, consult Codex:
   codex exec --sandbox read-only '
   Objective: Trace the execution flow from {entry point} to {error location}.
   Context:
   - Entry point: {file:function}
   - Error location: {file:line}
   - Key intermediate functions: {list}
   Constraints:
   - Track state transformations at each step
   - Identify where assumptions are violated
   Output format:
   ## Execution Flow (step by step)
   ## State Transformations
   ## Assumption Violations
   ## Critical Decision Points
   '

   ### 2. Hypothesis Evaluation
   For each hypothesis, consult Codex to evaluate evidence:
   codex exec --sandbox read-only '
   Objective: Evaluate hypothesis \"{hypothesis}\" against collected evidence.
   Context:
   - Hypothesis: {description}
   - Evidence FOR: {list}
   - Evidence AGAINST: {list}
   - Code context: {relevant code snippets}
   Constraints:
   - Apply logical reasoning, not pattern matching
   - Consider alternative explanations for the evidence
   Output format:
   ## Verdict (CONFIRMED / ELIMINATED / INCONCLUSIVE)
   ## Reasoning
   ## Remaining Unknowns
   '

   ### 3. Fix Approach Design
   Consult Codex for trade-off analysis of fix alternatives:
   codex exec --sandbox read-only '
   Objective: Design and compare fix approaches for root cause: {root cause description}.
   Context:
   - Root cause: {description}
   - Affected code: {file:line}
   - Current behavior: {description}
   - Desired behavior: {description}
   Constraints:
   - Propose at least 2 approaches
   - Evaluate: correctness, minimal invasiveness, maintainability, performance
   - Consider backward compatibility
   Output format:
   ## Approach A: {name}
   ## Approach B: {name}
   ## Comparison Matrix
   ## Recommendation with Rationale
   '

   ### 4. Fix Correctness Verification
   Before finalizing, consult Codex to verify the proposed fix:
   codex exec --sandbox read-only '
   Objective: Verify that the proposed fix correctly resolves the root cause.
   Context:
   - Root cause: {description}
   - Proposed fix: {description}
   - Edge cases identified: {list}
   Constraints:
   - Check that the fix addresses the root cause, not just symptoms
   - Verify behavior under all identified trigger conditions
   - Check for new failure modes introduced by the fix
   Output format:
   ## Correctness Assessment (CORRECT / INCOMPLETE / INCORRECT)
   ## Edge Case Coverage
   ## New Failure Modes (if any)
   ## Confidence Level
   '

   Save analysis to .claude/docs/research/troubleshoot-{issue}-root-cause.md

   Communicate with Impact Investigator teammate:
   - Share root cause findings that expand the affected scope
   - Request context about specific code paths or history
   - Confirm or refute hypotheses based on shared evidence

   IMPORTANT — Work Log:
   When ALL your tasks are complete, write a work log file to:
     .claude/logs/agent-teams/{team-name}/root-cause-analyst.md

   Use this format:
   # Work Log: Root Cause Analyst
   ## Summary
   (1-2 sentence summary of root cause finding)
   ## Hypotheses Evaluated
   - [confirmed/eliminated] {hypothesis}: {evidence}
   ## Root Cause
   - Defect: {description}
   - Location: {file:line}
   - Trigger condition: {when it occurs}
   ## Proposed Fixes
   - Approach A: {description} — {pros/cons}
   - Approach B: {description} — {pros/cons}
   - Recommended: {which and why}
   ## Codex Consultations
   - {question asked to Codex}: {key insight from response}
   ## Communication with Teammates
   - -> {recipient}: {summary of message sent}
   - <- {sender}: {summary of message received}
   ## Issues Encountered
   - {issue}: {how it was resolved}
   (If none, write 'None')
   "

2. **Impact Investigator** — Uses Opus with Git history, codebase search, WebSearch, and Codex for risk analysis
   Prompt: "You are the Impact Investigator for bug: {issue}.

   Your job: Determine the full scope and impact of this bug, and gather context for the fix.
   Consult Codex for regression risk reasoning and fix safety analysis.

   Bug Report:
   {bug report from Phase 1}

   Tasks:
   1. Trace the bug's origin in git history:
      - git log / git bisect to find the introducing commit
      - What change caused this? Was it intentional?
   2. Assess blast radius:
      - What other code paths call the affected function?
      - What features/users are impacted?
      - Are there related bugs or similar patterns elsewhere?
   3. Research external context:
      - Is this a known issue in a dependency? (WebSearch)
      - Are there upstream fixes or workarounds?
      - Check issue trackers, changelogs, migration guides
   4. Evaluate regression risk:
      - What tests cover the affected area?
      - What could break if we change this code?
      - Are there downstream consumers to consider?

   How to research:
   - Use Git commands (git log, git blame, git bisect) for history
   - Use Grep/Glob for codebase impact analysis
   - Use WebSearch for external known issues:
     WebSearch: '{library} {error message} issue fix'

   ## Codex Risk Analysis Protocol (MANDATORY)

   You MUST consult Codex for regression risk reasoning and fix safety analysis.

   ### Regression Risk Reasoning
   Consult Codex to evaluate what could break if the proposed change is applied:
   codex exec --sandbox read-only '
   Objective: Evaluate regression risk if {proposed change} is applied to {file:line}.
   Context:
   - Current behavior: {description}
   - Proposed change: {description}
   - Callers of affected function: {list}
   - Existing test coverage: {description}
   Constraints:
   - Consider all callers and downstream consumers
   - Identify implicit contracts that may be violated
   - Assess backward compatibility impact
   Output format:
   ## Risk Assessment (HIGH / MEDIUM / LOW)
   ## Affected Code Paths
   ## Implicit Contracts at Risk
   ## Recommended Safeguards
   '

   ### Fix Safety Analysis
   Consult Codex to verify the proposed fix does not introduce new issues:
   codex exec --sandbox read-only '
   Objective: Analyze whether the proposed fix introduces new issues or side effects.
   Context:
   - Root cause: {from Root Cause Analyst}
   - Proposed fix: {description}
   - Blast radius: {affected code paths}
   - Dependencies: {upstream/downstream}
   Constraints:
   - Check for new edge cases created by the fix
   - Verify thread safety if applicable
   - Check for performance implications
   Output format:
   ## Safety Assessment (SAFE / CAUTION / UNSAFE)
   ## New Issues Identified
   ## Side Effects
   ## Mitigation Recommendations
   '

   Save findings to .claude/docs/research/troubleshoot-{issue}-impact.md

   Communicate with Root Cause Analyst teammate:
   - Share git history context that informs root cause
   - Share external findings (known issues, upstream fixes)
   - Request clarification on which code paths to investigate

   IMPORTANT — Work Log:
   When ALL your tasks are complete, write a work log file to:
     .claude/logs/agent-teams/{team-name}/impact-investigator.md

   Use this format:
   # Work Log: Impact Investigator
   ## Summary
   (1-2 sentence summary of impact assessment)
   ## Git History
   - Introducing commit: {hash} — {description}
   - Related commits: {list}
   ## Blast Radius
   - Affected code paths: {list}
   - Affected features/users: {list}
   ## External Research
   - {source}: {finding and relevance}
   ## Regression Risk
   - Existing test coverage: {description}
   - Risk areas: {what could break}
   ## Codex Risk Analysis
   - Regression risk assessment: {Codex's verdict and reasoning}
   - Fix safety assessment: {Codex's verdict and reasoning}
   ## Communication with Teammates
   - -> {recipient}: {summary of message sent}
   - <- {sender}: {summary of message received}
   ## Issues Encountered
   - {issue}: {how it was resolved}
   (If none, write 'None')
   "

Wait for both teammates to complete their tasks.
```

### Why Bidirectional Communication Matters for Debugging

```
Example interaction flow:

Root Cause Analyst: "The error occurs because parse_config() returns None when key is missing"
    -> Impact Investigator: "Checking git blame -- this was changed in commit abc123"
    -> Impact Investigator: "Found 5 other callers of parse_config() that don't handle None"
    -> Root Cause Analyst: "Expanding fix scope -- need to either fix callers or fix parse_config()"
    -> Root Cause Analyst: "Codex recommends: fix parse_config() to raise KeyError instead of returning None"
    -> Impact Investigator: "Codex risk analysis confirms: all 5 callers already have try/except for KeyError"
    -> Root Cause Analyst: "Root cause confirmed. Codex verified fix correctness. Fix approach: restore KeyError in parse_config()"
```

Without Agent Teams, this discovery loop would require multiple sequential subagent rounds.

