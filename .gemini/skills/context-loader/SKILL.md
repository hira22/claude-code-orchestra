---
name: context-loader
description: Reference sheet listing which .claude/ files the caller (multimodal-explore agent) should inject into agy prompts. Auto-loading of this skill by agy is NOT relied upon; the Claude-side agent performs the injection.
---

# Context Loader Skill for the Multimodal CLI

## Purpose

Enumerate the project-context surface that the `multimodal-explore` agent
must fold into every `agy` call. `agy`'s auto-loading of project-level
`.gemini/` context is undocumented, so this file is a **checklist for the
caller**, not a runtime hook.

## When to Activate

This skill is not self-triggering inside `agy`. The `multimodal-explore` agent
consults it before invoking `agy -p ...` and injects the relevant items via
prompt preamble or `agy --add-dir`.

## Workflow

### Step 1: Load Coding Rules

Read relevant files from `.claude/rules/`:

```
.claude/rules/
├── coding-principles.md   # Simplicity, single responsibility, early return
├── dev-environment.md     # uv, ruff, ty, pytest requirements
├── language.md            # Think in English, respond in Japanese
├── security.md            # Secrets, validation, SQLi/XSS prevention
└── testing.md             # TDD, AAA pattern, 80% coverage
```

### Step 2: Load Design Documentation

Read `.claude/docs/DESIGN.md` for:
- Architecture decisions
- Implementation patterns
- Library choices and constraints

### Step 3: Check Library Documentation

If the task involves specific libraries, read relevant files from:
```
.claude/docs/libraries/
```

### Step 4: Execute Research Task

With the loaded context, execute the requested research/analysis following:
- Project coding principles
- Existing design decisions
- Library constraints

## Key Rules to Remember

1. **Simplicity first** - Recommend readable solutions over complex
2. **Type hints required** - Suggest typed code
3. **Use uv** - Reference uv for package management
4. **Security** - Highlight security considerations

## Language Protocol

- **Thinking/Reasoning**: English
- **Code examples**: English (variables, functions, comments)
- **Output**: Structured markdown, suitable for documentation

## Output Guidelines

When providing research results:
- Structure with clear headings
- Include code examples when relevant
- Cite sources from web search
- Note constraints relevant to this project
- Save comprehensive findings to `.claude/docs/research/`
