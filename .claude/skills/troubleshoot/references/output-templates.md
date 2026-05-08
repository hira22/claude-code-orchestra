# Troubleshoot Phase 3 -- Output Templates

## Step 3: Update CLAUDE.md

Add bug context to CLAUDE.md for cross-session persistence:

```markdown
---

## Current Bug Fix: {issue}

### Context
- Error: {1-2 sentence summary}
- Root cause: {description}
- Affected files: {list}

### Fix Approach
- {Recommended approach from Root Cause Analyst}

### Codex Validation
- Validation result: {PASS / NEEDS_REVISION}
- Additional test cases: {from Codex validation}

### Regression Risks
- {Key risks from Impact Investigator}
- {Codex risk assessment summary}

### Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}
```


## Step 4: Present to User

Present the diagnosis and fix plan to the user:

```markdown
## Diagnosis Report: {issue}

### Error Reproduction
{Reproduction result -- confirmed / partially confirmed / could not reproduce}

### Root Cause (Root Cause Analyst + Codex)
- **Defect**: {description of the underlying defect}
- **Location**: `{file}:{line}`
- **Trigger**: {conditions under which the error occurs}
- **Evidence**: {key evidence supporting this conclusion}
- **Codex confidence**: {Codex's assessment of root cause certainty}

### Impact Assessment (Impact Investigator + Codex)
- **Blast radius**: {affected code paths and features}
- **Introducing commit**: {hash and description, if identified}
- **External context**: {known issues, upstream fixes if any}
- **Regression risk**: {what could break during fix}
- **Codex risk assessment**: {Codex's regression risk verdict}

### Fix Plan ({N} tasks) -- Codex Validated: {PASS / NEEDS_REVISION}
1. Write failing test to reproduce the bug
2. {Fix task -- the core fix}
3. {Additional fix tasks from blast radius}
4. {Additional test cases recommended by Codex}
5. Run full test suite for regression check

### Alternative Approaches Considered
- **Approach A**: {description} -- {why chosen / not chosen}
- **Approach B**: {description} -- {why chosen / not chosen}

### Next Steps
1. Shall we proceed with this fix plan?
2. After approval, start fix implementation with `/team-implement`
3. After implementation, run regression review with `/team-review`

---
Shall we proceed with this fix plan?
```


## Output Files

| File | Author | Purpose |
|------|--------|---------|
| `.claude/docs/research/troubleshoot-{issue}-context.md` | Opus Subagent | Initial error context analysis |
| `.claude/docs/research/troubleshoot-{issue}-root-cause.md` | Root Cause Analyst | Root cause analysis (Codex-driven) |
| `.claude/docs/research/troubleshoot-{issue}-impact.md` | Impact Investigator | Impact assessment (with Codex risk analysis) |
| `CLAUDE.md` (updated) | Lead | Cross-session bug fix context |
| Task list (internal) | Lead | Fix implementation tracking |

---
