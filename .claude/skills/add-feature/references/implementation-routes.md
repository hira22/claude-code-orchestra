# Add Feature -- Implementation Routes & Templates

## Phase 2 Step 5: Present to User

Present the design and plan for approval:

```markdown
## Feature Plan: {feature}

### Scope Analysis (Opus + Codex)
{Key findings from Phase 1 -- 3-5 bullet points}

### Complexity
- Classification: {SIMPLE / MODERATE / COMPLEX}
- Implementation route: {Codex direct / Codex + review / team-implement}

### Architecture Design (Codex)
{Architecture overview}
{Key design decisions with rationale}

### Implementation Plan ({N} steps) -- Codex Validated: {PASS}
1. {Step 1}: {description}
2. {Step 2}: {description}
...

### File Changes Summary
| File | Change Type | Description |
|------|------------|-------------|
| {file} | {new/modify} | {what changes} |

### Test Plan
- {Test 1}: {what it verifies}
- {Test 2}: {what it verifies}

### Risks and Mitigations
- {Risk}: {mitigation}

### Next Steps
1. Shall we proceed with this plan?
2. Implementation will use: {route based on complexity}

---
Shall we proceed with this plan?
```


## Phase 3: IMPLEMENT (Complexity-Routed)

**Route implementation based on complexity classification from Phase 1.**

### Route A: SIMPLE (1-3 files, <50 LOC) -- Codex Direct

For simple features, Codex implements directly:

```bash
codex exec --sandbox workspace-write "
Objective: Implement this feature following the approved plan.
Context:
- Feature Brief: {feature brief}
- Architecture Design: {from Phase 2}
- Implementation Plan: {from Phase 2}
- Existing conventions: {from Phase 1 codebase scan}
Constraints:
- Follow the implementation plan steps exactly
- Follow existing codebase conventions (naming, structure, patterns)
- Write tests for all new functionality
- Keep changes minimal and focused
Relevant files:
- {list of files to create/modify}
Acceptance checks:
- All new tests pass
- Existing tests still pass
- Code follows existing conventions
Output format:
## Changes Made
## Tests Written
## Validation Results
## Remaining Risks
"
```

After Codex implementation, verify:

```bash
# Run tests
uv run pytest -v

# Run linter
uv run ruff check .

# Run formatter check
uv run ruff format --check .
```

### Route B: MODERATE (3-5 files) -- Codex + Review

For moderate features, Codex implements, then `/team-review` validates:

1. **Implement with Codex** (same as Route A, but with more files)
2. **Run basic verification** (tests, linting)
3. **Invoke `/team-review`** for parallel review (security, quality, test coverage)

```
After Codex implementation:
/team-review   <- Parallel review from multiple perspectives
```

### Route C: COMPLEX (5+ files) -- Team Implement + Review

For complex features, delegate to `/team-implement` for parallel implementation:

```
/team-implement   <- Parallel implementation with Agent Teams
    | After completion
/team-review      <- Parallel review
```

Pass the Feature Brief, Architecture Design, and Implementation Plan from Phase 2 as input to `/team-implement`.


### Post-Implementation: Update CLAUDE.md

After implementation is complete, add feature context to CLAUDE.md for cross-session persistence:

```markdown
---

## Current Feature: {feature}

### Context
- Goal: {1-2 sentences}
- Key files: {list of new/modified files}
- Complexity: {SIMPLE / MODERATE / COMPLEX}

### Architecture
- {Key architecture decisions from Codex}

### Codex Validation
- Design validation: {PASS / NEEDS_REVISION}
- Additional test cases: {from Codex validation}

### Integration Points
- {Integration point}: {description}

### Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}
```


## Output Files

| File | Author | Purpose |
|------|--------|---------|
| `.claude/docs/research/add-feature-{feature}-codebase.md` | Opus Subagent | Codebase scan for affected areas |
| `.claude/docs/DESIGN.md` (updated) | Lead (Codex-informed) | Architecture decisions for the feature |
| `CLAUDE.md` (updated) | Lead | Cross-session feature context |
| Implementation files | Codex / Agent Teams | The feature itself |
| Test files | Codex / Agent Teams | Tests for the feature |

---
