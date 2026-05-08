---
name: design-tracker
description: Track design decisions in DESIGN.md. Triggers on architecture talk, "record this", "update design", or explicit /design-tracker.
---

# Design Tracker Skill

## Purpose

This skill manages the project's design documentation (`.claude/docs/DESIGN.md`). It automatically tracks:
- Architecture decisions
- Implementation plans
- Library choices and their rationale
- TODO items and open questions

## When to Activate

- User discusses architecture or design patterns
- User makes implementation decisions (e.g., "let's use ReAct pattern")
- User says "record this", "add to design", "document this", "update design"
- User asks "what's our current design?" or "what have we decided?"
- Important technical decisions are made during conversation
- User explicitly invokes via `/design-tracker [optional content]`

## Workflow

### Recording Decisions

1. Read existing `.claude/docs/DESIGN.md`
2. Extract the decision/information from conversation
3. Update the appropriate section
4. Add entry to Changelog with today's date

If `$ARGUMENTS` is provided (explicit invocation), focus on recording that specific content.

### Sections to Update

| Conversation Topic | Target Section |
|-------------------|----------------|
| Overall goals, purpose | Overview |
| System structure, components | Architecture |
| Patterns (ReAct, etc.) | Implementation Plan > Patterns |
| Library choices | Implementation Plan > Libraries |
| Why we chose X over Y | Implementation Plan > Key Decisions |
| Things to implement later | TODO |
| Unresolved questions | Open Questions |

### Update Format

When updating, append to the appropriate section using:

```markdown
### Key Decisions

#### {Decision Title} ({Date})

**Context**: {Why this decision was needed}
**Decision**: {What was decided}
**Rationale**: {Why this option was chosen}
```

### Changelog Entry

Always add to the Changelog section:

```markdown
## Changelog

### {Date}
- {Brief description of what was recorded}
```

## Output Format

When recording, confirm in Japanese:
- What was recorded
- Which section was updated
- Brief summary of the change

## Language Rules

- **Thinking/Reasoning**: English
- **Code examples**: English
- **Document content**: English (technical terms) + Japanese (descriptions OK)
- **User communication**: Japanese

## Migration Note

The standalone `update-design` skill has been merged into this one. Both
auto-trigger (architecture/decision keywords) and explicit invocation
(`/design-tracker [content]`) flow through this single skill.
