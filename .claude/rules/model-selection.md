# Model Selection Rule

Select the model tier (Opus / Sonnet) by **cognitive complexity**, not task size.
Aliases resolve to the latest version (`opus` → Opus 4.8, `sonnet` → Sonnet 4.6 on the Anthropic API).

## Default Tier per Agent

Each agent declares a frontmatter `model:` default. The orchestrator can override it
per-call via the `model` parameter on the Task/Agent tool.

| Agent | Default | Rationale |
|-------|---------|-----------|
| `general-purpose` | `opus` | Handles design, analysis, and complex implementation |
| `gemini-explore` | `sonnet` | Gemini CLI wrapper; Claude only gathers context and formats output |
| `codex-debugger` | `sonnet` | Codex CLI wrapper; deep reasoning happens in Codex (GPT-5.4) |

## When to Use Opus

- Design decisions, architecture, trade-off analysis
- Ambiguous or under-specified requirements needing interpretation
- Cross-cutting reasoning across multiple modules
- Deep code analysis or complex refactoring
- Tasks where correctness is critical and mistakes are costly

## When to Downgrade to Sonnet (per-call override)

- Well-specified, mechanical tasks (rename, format, boilerplate generation)
- Single-file edits with clear instructions
- Grep / search and summarize
- Template or scaffold expansion
- Collecting information without judgment (listing files, reading configs)

## Important Distinction

The **Delegation Trigger** (CLAUDE.md §4) decides **whether** to delegate.
The **model tier** decides **which model** runs the delegated task.
These are independent axes:

- A 15-line mechanical edit triggers delegation (> 10 LOC) but runs on **Sonnet**.
- A short but ambiguous design question may not trigger delegation, yet if delegated, runs on **Opus**.

## Orchestrator Pattern

```
Task tool:
  subagent_type: "general-purpose"
  model: "sonnet"              # Override for mechanical tasks
  prompt: "Rename all X to Y in the following files..."
```

When the `model` parameter is omitted, the agent's frontmatter default applies.
