---
name: add-feature
description: Add a feature to an existing codebase with scope analysis and design validation.
metadata:
  short-description: Codex-first feature addition with complexity-based implementation routing
---

# Add Feature

**Codex-first feature addition skill for existing codebases, with complexity-based implementation routing.**

## Overview

This skill adds a feature to an **existing** codebase. It is lighter-weight than `/start-feature` (which targets large features requiring research) but still Codex-centric: Codex CLI is consulted proactively in every phase for scope analysis, architecture design, implementation planning, and validation. Implementation is routed based on complexity.

```
/add-feature <feature description>   <- This skill (scope, design, implement)
    | SIMPLE (1-3 files, <50 LOC)
    Codex workspace-write direct implementation
    | MODERATE (3-5 files)
    Codex workspace-write + /team-review
    | COMPLEX (5+ files)
    /team-implement + /team-review
```

## When to Use

| Skill | Use When |
|-------|----------|
| **`/add-feature`** | Adding a feature to an existing codebase with established patterns |
| `/start-feature` | Starting a large new feature requiring external research and parallel design |
| `/troubleshoot` | Diagnosing and fixing bugs where root cause is unclear |
| `/team-implement` | Executing an already-approved implementation plan in parallel |

## Workflow

```
Phase 1: SCOPE (Opus 1M context + Codex Impact Analysis + Claude Lead)
  Opus subagent scans affected areas, Codex analyzes scope and impact,
  Claude clarifies requirements with the user
    |
Phase 2: DESIGN (Codex Architecture + Codex Plan + Codex Validation)
  Codex designs architecture, creates implementation plan, validates completeness
    |
Phase 3: IMPLEMENT (Complexity-routed)
  SIMPLE  -> Codex workspace-write
  MODERATE -> Codex workspace-write + /team-review
  COMPLEX  -> /team-implement + /team-review
```

---

## Phase 1: SCOPE (Opus Subagent + Codex + Claude Lead)

**Understand the feature's scope and impact on the existing codebase with Opus subagent's 1M context, then consult Codex for scope and impact analysis, while Claude clarifies requirements with the user.**

> Main orchestrator context is precious. Large-scale codebase scanning is delegated to Opus subagent (1M context).
> Codex is consulted early for scope analysis and impact assessment.

### Step 1: Gather Feature Requirements from User

Ask the user to provide:

1. **Feature description**: What should the feature do?
2. **Expected behavior**: How should it work from the user's perspective?
3. **Scope boundaries**: What to include / exclude?
4. **Technical preferences**: Specific libraries, patterns, or constraints?
5. **Success criteria**: How do you determine the feature is complete?

### Step 2: Scan Codebase with Opus Subagent

Use a general-purpose subagent (Opus) to scan the affected areas:

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Analyze this codebase to understand where a new feature should be added:

    Feature: {feature description}

    Tasks:
    1. Identify the areas of the codebase relevant to this feature:
       - Which modules/files will be affected?
       - What are the existing patterns in those areas?
       - What interfaces/contracts exist that the feature must conform to?
    2. Analyze existing conventions:
       - Code patterns (naming, structure, error handling)
       - Test patterns (test location, fixture usage, assertion style)
       - Import and dependency patterns
    3. Map dependencies:
       - What does the affected code depend on?
       - What depends on the affected code? (downstream consumers)
       - Are there shared utilities or base classes to leverage?

    Use Glob, Grep, and Read tools to investigate thoroughly.

    Save analysis to .claude/docs/research/add-feature-{feature}-codebase.md
    Return concise summary (5-7 key findings).
```

### Step 2.5: Codex Scope & Impact Analysis (MANDATORY)

Consult Codex for scope analysis and impact assessment:

```bash
codex exec --sandbox read-only "
Objective: Analyze the scope and impact of adding this feature to the existing codebase.
Context:
- Feature: {feature description}
- Affected modules: {from Opus subagent analysis}
- Existing patterns: {from Opus subagent analysis}
- Dependencies: {from Opus subagent analysis}
Constraints:
- Assess how many files need to change and estimate LOC
- Classify complexity: SIMPLE (1-3 files, <50 LOC), MODERATE (3-5 files), COMPLEX (5+ files)
- Identify integration points where the feature connects to existing code
- Flag risks: breaking changes, performance concerns, test coverage gaps
Output format:
## Scope Assessment
## Complexity Classification (SIMPLE / MODERATE / COMPLEX)
## Integration Points
## Affected Files (with change type: new / modify)
## Risks and Concerns
## Recommended Approach
"
```

Use Codex's complexity classification to determine the implementation route in Phase 3.

### Step 3: Create Feature Brief

Combine user requirements + codebase analysis + Codex scope assessment into a "Feature Brief":

```markdown
## Feature Brief: {feature}

### Current State
- Architecture: {existing architecture in affected area}
- Relevant files: {key files and modules}
- Patterns: {existing patterns to follow}

### Feature Goal
{User's desired outcome in 1-2 sentences}

### Scope
- Include: {list}
- Exclude: {list}

### Complexity Classification (from Codex)
- Classification: {SIMPLE / MODERATE / COMPLEX}
- Estimated files: {count}
- Estimated LOC: {range}
- Implementation route: {Codex direct / Codex + review / team-implement}

### Integration Points
- {Integration point 1}: {how the feature connects}
- {Integration point 2}: {how the feature connects}

### Risks
- {Risk 1}: {mitigation}
- {Risk 2}: {mitigation}

### Success Criteria
- {measurable criteria}
```

This brief is passed to Phase 2 for design.

---

## Phase 2: DESIGN (Codex Architecture + Codex Plan + Codex Validation)

**Codex designs the architecture, creates an implementation plan, and validates completeness. All three consultations are MANDATORY.**

> Unlike /start-feature which uses Agent Teams (Researcher + Architect) for greenfield design,
> /add-feature uses Codex directly because the patterns and conventions are already established.

### Step 1: Codex Architecture Design (MANDATORY)

Consult Codex to design how the feature fits into the existing codebase:

```bash
codex exec --sandbox read-only "
Objective: Design the architecture for adding this feature to the existing codebase.
Context:
- Feature Brief: {feature brief from Phase 1}
- Existing patterns: {conventions from codebase scan}
- Integration points: {from Codex scope analysis}
Constraints:
- Follow existing codebase conventions exactly (naming, structure, patterns)
- Minimize changes to existing code (prefer extension over modification)
- Maintain backward compatibility
- Design for testability
Output format:
## Architecture Design
## Module Structure (new files and modifications)
## Interface Design (function signatures, class APIs)
## Data Flow
## Error Handling Strategy
## Test Strategy
"
```

### Step 2: Codex Implementation Plan (MANDATORY)

Consult Codex to create a step-by-step implementation plan:

```bash
codex exec --sandbox read-only "
Objective: Create a step-by-step implementation plan for this feature.
Context:
- Feature Brief: {feature brief from Phase 1}
- Architecture Design: {from Step 1}
- Complexity: {SIMPLE / MODERATE / COMPLEX}
Constraints:
- Order steps by dependency (what must be built first)
- Each step should be independently testable
- Include test writing as explicit steps (TDD where possible)
- Keep individual steps small and focused
Output format:
## Implementation Steps (ordered by dependency)
## File Changes (per step: file path, change type, description)
## Test Plan (per step: what to test)
## Dependencies Between Steps
## Estimated Effort per Step
"
```

### Step 3: Codex Validation (MANDATORY)

Consult Codex to validate the plan for completeness and correctness:

```bash
codex exec --sandbox read-only "
Objective: Validate this implementation plan for completeness, correctness, and risk.
Context:
- Feature Brief: {feature brief}
- Architecture Design: {from Step 1}
- Implementation Plan: {from Step 2}
- Existing codebase patterns: {from Phase 1}
Constraints:
- Check for missing edge cases or error handling
- Verify the plan maintains backward compatibility
- Ensure test coverage is adequate
- Identify potential integration issues
- Check that the plan follows existing conventions
Output format:
## Validation Result (PASS / NEEDS_REVISION)
## Missing Coverage
## Backward Compatibility Check
## Convention Compliance
## Integration Risks
## Additional Test Cases Recommended
## Revised Steps (if NEEDS_REVISION)
"
```

If Codex returns NEEDS_REVISION, update the plan and re-validate before proceeding.

### Step 4: Update DESIGN.md

Update `.claude/docs/DESIGN.md` with the feature's architecture decisions:

```markdown
## Feature: {feature}

### Architecture
- {Key architecture decisions from Codex}

### Integration Points
- {How the feature connects to existing code}

### Design Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}
```

### Step 5: Present to User

Present the design and plan for user approval, covering scope analysis, complexity classification, architecture design, implementation steps, file changes, test plan, risks, and next steps.

See `references/implementation-routes.md` for the full presentation template.

---

## Phase 3: IMPLEMENT (Complexity-Routed)

**Route implementation based on complexity classification from Phase 1.**

| Route | Complexity | Approach |
|-------|-----------|----------|
| **A: SIMPLE** | 1-3 files, <50 LOC | Codex `workspace-write` direct implementation, then verify with tests + linter |
| **B: MODERATE** | 3-5 files | Codex `workspace-write` implementation, then `/team-review` for validation |
| **C: COMPLEX** | 5+ files | `/team-implement` for parallel implementation, then `/team-review` |

After implementation, update CLAUDE.md with feature context for cross-session persistence.

See `references/implementation-routes.md` for the full route details, Codex prompts, post-implementation CLAUDE.md template, and output files table.

---

## Tips

- **Codex-first**: Every phase consults Codex. This is intentional -- Codex excels at understanding how new code fits into existing patterns and identifying integration risks
- **Codex for scope**: Phase 1 Codex consultation classifies complexity early, so the right implementation route is chosen from the start
- **Codex for validation**: Phase 2 validation catches missing edge cases and convention violations before implementation begins
- **Lighter than /start-feature**: This skill skips the Agent Teams research phase because the codebase conventions are already established -- Codex reasons about them directly
- **Complexity routing**: Do not over-engineer simple features. 1-3 file changes should use Codex direct implementation, not Agent Teams
- **Existing patterns**: The most important input to Codex is the existing codebase patterns from the Opus subagent scan. Always include them in every Codex prompt
- **Phase 1**: Opus subagent (1M context) scans affected areas, then Codex classifies scope and complexity, while Claude collects requirements from the user
- **Phase 2**: Three mandatory Codex consultations (architecture, plan, validation) ensure the design is sound before any code is written
- **Phase 3**: After implementation, always run tests (`uv run pytest`) and linting (`uv run ruff check .`) regardless of complexity route
- **Quick features**: For truly trivial changes (single function, <10 LOC), skip this skill and edit directly -- use this skill when the feature touches multiple parts of the codebase
- **Ctrl+T**: Toggle task list display
