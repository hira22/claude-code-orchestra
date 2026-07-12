---
name: multimodal-system
description: Antigravity CLI (agy) for content extraction from PDF/video/audio/image files. Use only when an actual file is present; research/codebase analysis → general-purpose subagent.
metadata:
  short-description: Antigravity CLI (agy) — multimodal file processing (PDF/video/audio/image)
---

# Multimodal System — Multimodal File Processing

**Antigravity CLI (`agy`) is specialized for multimodal file processing (PDF, video, audio, image).**

> **Detailed rules**: `.claude/rules/multimodal-delegation.md`
> **Research/codebase analysis**: Use general-purpose subagent (Opus) instead — Opus now supports 1M context.

## Multimodal File Processing

Extract content from PDF, video, audio, and image files.

```bash
# PDF
agy -p "Extract: {what to extract}. Answer concisely in plain text. @/path/to/file.pdf"

# Video
agy -p "Summarize: key concepts, timestamps. Answer concisely in plain text. @/path/to/video.mp4"

# Audio
agy -p "Transcribe and summarize: decisions, action items. Answer concisely in plain text. @/path/to/audio.mp3"

# Image (diagrams, charts)
agy -p "Analyze: components, relationships, data flow. Answer concisely in plain text. @/path/to/diagram.png"
```

| Target | Extensions |
|--------|------------|
| PDF | `.pdf` |
| Video | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` |
| Audio | `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg` |
| Images (advanced analysis) | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg` |

> Simple screenshot inspection can be done directly with Claude's Read tool.

## Constrain agy Output

`agy` is agent-like and may return conversational summaries plus unrequested
"Recommended Changes / Open Questions" sections. Detailed artifacts are saved
to `~/.gemini/antigravity-cli/brain/<uuid>/*.md`.

Always append **"Answer concisely in plain text"** (or equivalent) to constrain
the response to what was asked.

## Auto-Trigger

When multimodal files appear in a task, automatically pass them to `agy` without waiting for user instructions.

## When NOT to Use agy

| Task | Correct Owner |
|------|---------------|
| Research and investigation | **general-purpose subagent** (Opus) |
| Codebase analysis | **general-purpose subagent** (Opus) |
| Design and planning | **Codex** |
| Debugging | **Codex** |
| Code implementation | **Claude / Subagents** |

## How to Use

### Subagent Pattern (for large outputs)

```
Task tool parameters:
- subagent_type: "multimodal-explore"
- prompt: |
    {task description}

    agy -p "{prompt}. Answer concisely in plain text. @/path/to/file"

    Return CONCISE summary (5-7 bullet points).
```

### Direct Call (for short extractions)

```bash
agy -p "{what to extract}. Answer concisely in plain text. @/path/to/file"
```

## Language Protocol

1. Ask `agy` in **English**
2. Receive response in **English**
3. Report to user in **the user's language**
