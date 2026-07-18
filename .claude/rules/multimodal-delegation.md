# Multimodal Delegation Rule

**Antigravity CLI (`agy`) is specialized for multimodal file processing (PDF, video, audio, image).**

> Opus/Sonnet now support 1M context. Research and codebase analysis are handled by Opus subagents (general-purpose).
> `agy` is used exclusively for multimodal content extraction that Claude cannot process directly.

## Role: Multimodal File Processing

- Extract content from PDF, video, audio, and image files
- Detailed analysis of charts and diagrams
- Video summarization and timestamp extraction
- Audio transcription and summarization

## When to Use agy

| Situation | Examples |
|------|------|
| **PDF content extraction** | "Extract API specs from this PDF" |
| **Video analysis** | "Summarize this tutorial video" |
| **Audio transcription** | "Transcribe this meeting recording" |
| **Diagram/chart analysis** | "Analyze this architecture diagram" |

## When NOT to Use agy

- **Research and investigation** → Opus subagent (general-purpose) with WebSearch/WebFetch
- **Codebase analysis** → Opus subagent (general-purpose) with Read/Grep/Glob
- **Planning, design, architecture** → Codex CLI
- **Debugging, error analysis** → Codex CLI
- **Code implementation** → Claude / subagent
- **Simple file reading** → Claude's Read tool
- **Simple screenshot inspection** → Claude's Read tool

## Supported File Extensions (Multimodal)

| Category | Extensions |
|----------|--------|
| PDF | `.pdf` |
| Video | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` |
| Audio | `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg` |
| Image (detailed analysis) | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg` |

## How to Use

### Multimodal File Reading

```bash
# PDF -- Extract structure and content
agy -p "Extract: {what information to extract}. Answer concisely in plain text. @/path/to/file.pdf"

# Video -- Summarize, key points, timestamps
agy -p "Summarize: key concepts, decisions, timestamps. Answer concisely in plain text. @/path/to/video.mp4"

# Audio -- Transcription and summarization
agy -p "Transcribe and summarize: decisions, action items. Answer concisely in plain text. @/path/to/audio.mp3"

# Image -- Detailed analysis of charts and diagrams
agy -p "Analyze this diagram: components, relationships, data flow. Answer concisely in plain text. @/path/to/diagram.png"
```

## Important: Constrain agy Output

`agy` is agent-like and may return conversational summaries plus unrequested
"Recommended Changes / Open Questions" sections. Detailed artifacts are also
saved to `~/.gemini/antigravity-cli/brain/<uuid>/*.md`.

- Append **"Answer concisely in plain text"** (or equivalent) to every prompt.
- If detailed artifacts matter, remember to also collect the `brain/<uuid>/`
  outputs for the run.

## Context Management

| Situation | Recommended Method |
|------|----------|
| Short extraction or answer (~30 lines) | Direct call OK |
| Detailed analysis report | Via multimodal-explore subagent |

### Subagent Pattern (For large output)

```
Task tool parameters:
- subagent_type: "multimodal-explore"
- run_in_background: true (for parallel work)
- prompt: |
    {task description}

    agy -p "{prompt}. Answer concisely in plain text. @/path/to/file"

    Return CONCISE summary (key findings + extracted content).
```

### Direct Call (Short extractions)

```bash
agy -p "Extract: {specific content}. Answer concisely in plain text. @/path/to/file"
```

## Auto-Trigger (Activates automatically without user instruction)

- PDF/video/audio files are referenced within a task
- User provides a file path with a multimodal-supported extension

## Prerequisites

- Install: `curl -fsSL https://antigravity.google/cli/install.sh | bash`
- Auth: initial `agy` run opens browser Google Sign-In (account-based).
  Standalone API-key auth is not supported yet, so headless/CI use is not
  supported; authenticate interactively once per machine.
- Optional: `agy plugin import gemini` migrates settings/plugins from a previous
  gemini-cli install (`agy` reads `~/.gemini/antigravity-cli/` at runtime).

## Language Protocol

1. Ask `agy` in **English**
2. Receive response in **English**
3. Execute based on findings
4. Report to user in **English**
