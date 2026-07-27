# Multimodal Use Cases — agy (Antigravity CLI)

> For research, codebase analysis, and documentation lookup, use a general-purpose subagent (Opus) instead.
> agy is specialized for multimodal file processing only.

## Video Analysis

```bash
# Tutorial video analysis
agy -p "Analyze this tutorial video:
- Summarize the main concepts taught
- List step-by-step instructions
- Note any important warnings or tips
- Identify timestamps for key sections
@tutorial.mp4"

# Code review video
agy -p "Extract code patterns and best practices demonstrated in this video @code-review.mp4"
```

## Audio Analysis

```bash
# Meeting recording
agy -p "Transcribe and summarize this technical discussion:
- Key decisions made
- Action items
- Open questions
- Technical terms mentioned
@meeting.mp3"

# Podcast/talk analysis
agy -p "Extract technical insights from this talk about {topic} @conference-talk.mp3"
```

## PDF Analysis

```bash
# API documentation
agy -p "Extract from this API documentation:
- All available endpoints
- Request/response schemas
- Authentication requirements
- Rate limiting rules
@api-spec.pdf"

# Technical specification
agy -p "Summarize this technical specification:
- Core requirements
- Constraints
- Interface definitions
- Edge cases to handle
@spec.pdf"

# Research paper
agy -p "Analyze this paper and explain:
- Problem being solved
- Proposed approach
- Key algorithms
- How to apply this in practice
@paper.pdf"
```

## Image / Diagram Analysis

```bash
# Architecture diagram
agy -p "Analyze this architecture diagram:
- Components and their responsibilities
- Data flow between components
- External dependencies
@architecture.png"

# Chart analysis
agy -p "Extract data and trends from this chart:
- Key metrics
- Trends over time
- Notable anomalies
@dashboard.png"
```

## When NOT to Use agy

| Task | Reason | Use Instead |
|------|--------|-------------|
| Research / investigation | Opus has 1M context + WebSearch | general-purpose subagent |
| Codebase analysis | Opus has 1M context + Read/Grep | general-purpose subagent |
| Design decisions | Requires deep reasoning | Codex |
| Code implementation | Codex has better code abilities | Codex |
| Debugging | Requires logical analysis | Codex |
| Simple file edits | Overkill | Claude Code directly |
| Running tests | Execution task | Claude Code directly |

## Output Handling

### Piping to Files

Do not trust a bare stdout redirect. In non-TTY contexts (e.g. Claude Code's
Bash tool), `agy -p` can exit 0 with **empty stdout** even after a successful
extraction whose result was written only to the brain directory
(google-antigravity/antigravity-cli#408). A bare `agy -p ... > file` can then
produce an empty file while still consuming quota.

```bash
START=$(date +%s)
agy -p "Extract all API schemas. Answer concisely in plain text. @api-spec.pdf" > docs/api-schemas.md

if [ ! -s docs/api-schemas.md ]; then
  # stdout was empty — recover the result from the brain dir instead of
  # accepting the empty file. Follow the "Non-TTY Output Fallback" procedure
  # in .claude/agents/multimodal-explore.md: find runs under
  # ~/.gemini/antigravity-cli/brain/<uuid>/ whose
  # .system_generated/logs/transcript.jsonl was modified after $START and
  # contains your prompt text, then use that run's root *.md artifacts —
  # or, if none exist, the last PLANNER_RESPONSE in the transcript.
  echo "agy returned empty stdout; recover output from the brain dir" >&2
fi
```

## Rate Limits

`agy` has weekly usage quotas that may be tighter than the gemini-cli free tier.
Plan accordingly for large extraction tasks; batch multi-file work and prefer
concise, focused prompts.
