"""Direct unit tests for .claude/hooks/lib/cli_logger.py.

The log path is redirected to a tmp file via $CLAUDE_CLI_LOG_FILE so tests
stay isolated and never touch the developer's session log.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time

import pytest


@pytest.fixture
def cli_logger(lib_module_path, tmp_path, monkeypatch):
    log_file = tmp_path / "cli-tools.jsonl"
    monkeypatch.setenv("CLAUDE_CLI_LOG_FILE", str(log_file))
    if "lib.cli_logger" in sys.modules:
        mod = importlib.reload(sys.modules["lib.cli_logger"])
    else:
        mod = importlib.import_module("lib.cli_logger")
    return mod, log_file


def _bash(command: str, stdout: str = "", exit_code: int = 0) -> dict:
    return {
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "exit_code": exit_code},
    }


def test_codex_command_extraction_picks_longest_quoted_segment(cli_logger):
    mod, log_file = cli_logger
    cmd = (
        'codex exec --config model_reasoning_effort="high" '
        '"This is the actual prompt that is much longer"'
    )
    prompt = mod.extract_codex_prompt(cmd)
    assert prompt == "This is the actual prompt that is much longer"


def test_agy_command_extraction(cli_logger):
    mod, _ = cli_logger
    assert mod.extract_agy_prompt('agy -p "summarize this"') == "summarize this"
    assert (
        mod.extract_agy_prompt("agy -p 'transcribe @audio.mp3'")
        == "transcribe @audio.mp3"
    )
    assert mod.extract_agy_prompt("agy --version") is None


def test_agy_command_extraction_supports_long_flag_aliases(cli_logger):
    """``--print`` / ``--prompt`` are documented long forms of ``-p``.

    Regression: only ``-p`` was matched, so long-form invocations were
    classified as agy but dropped by ``check()`` for lack of a prompt.
    """
    mod, _ = cli_logger
    assert mod.extract_agy_prompt('agy --print "summarize this"') == "summarize this"
    assert (
        mod.extract_agy_prompt("agy --prompt 'transcribe @audio.mp3'")
        == "transcribe @audio.mp3"
    )
    assert mod.extract_agy_prompt('agy --print="describe @img.png"') == (
        "describe @img.png"
    )
    assert mod.extract_agy_prompt("agy --prompt='read @doc.pdf'") == "read @doc.pdf"


def test_check_writes_agy_entry_with_long_flag(cli_logger):
    """End-to-end: ``agy --print "..."`` is logged, not silently dropped."""
    mod, log_file = cli_logger
    payload = _bash(
        'agy --print "describe @img.png"',
        stdout="A cat.",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["prompt"] == "describe @img.png"


def test_extract_model_flag(cli_logger):
    mod, _ = cli_logger
    assert mod.extract_model("codex --model gpt-5 'foo'") == "gpt-5"
    assert mod.extract_model("codex 'foo'") is None


def test_extract_model_supports_equals_form(cli_logger):
    """agy accepts ``--model=NAME`` in addition to space-separated form."""
    mod, _ = cli_logger
    assert mod.extract_model("agy --model=gemini-3.1-pro -p 'x'") == "gemini-3.1-pro"


def test_extract_model_supports_quoted_display_names(cli_logger):
    """agy models like ``Gemini 3.5 Flash`` contain spaces; must not truncate."""
    mod, _ = cli_logger
    assert (
        mod.extract_model('agy --model="Gemini 3.5 Flash" -p "x"') == "Gemini 3.5 Flash"
    )
    assert (
        mod.extract_model('agy --model "Gemini 3.5 Flash" -p "x"') == "Gemini 3.5 Flash"
    )
    assert (
        mod.extract_model("agy --model='Gemini 3.5 Flash' -p 'x'") == "Gemini 3.5 Flash"
    )
    assert (
        mod.extract_model("agy --model 'Gemini 3.5 Flash' -p 'x'") == "Gemini 3.5 Flash"
    )


def test_detect_tool_classifies_by_binary_not_prompt_body(cli_logger):
    """``agy -p "... codex ..."`` must be classified as agy, not codex.

    Regression: prior substring-based detection routed such commands into
    the codex branch, which then failed to extract a prompt and dropped
    the log entry entirely.
    """
    mod, _ = cli_logger
    assert (
        mod.detect_tool('agy -p "analyze this codex error screenshot @err.png"')
        == "agy"
    )
    assert mod.detect_tool('codex exec "explain agy usage"') == "codex"
    assert mod.detect_tool("ls -la") is None
    # Env-var prefix should not fool the classifier.
    assert mod.detect_tool('FOO=bar agy -p "hi"') == "agy"


def test_check_logs_agy_when_prompt_mentions_codex(cli_logger):
    """End-to-end: an agy call whose prompt mentions ``codex`` is logged as agy."""
    mod, log_file = cli_logger
    payload = _bash(
        'agy -p "analyze this codex error screenshot @err.png"',
        stdout="Error is a KeyError on line 42.",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["prompt"] == "analyze this codex error screenshot @err.png"


def test_check_writes_agy_entry_with_quoted_model_display_name(cli_logger):
    """``--model="Gemini 3.5 Flash"`` is recorded verbatim, quotes stripped."""
    mod, log_file = cli_logger
    payload = _bash(
        'agy --model="Gemini 3.5 Flash" -p "describe @img.png"',
        stdout="A cat.",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["model"] == "Gemini 3.5 Flash"


def _make_brain_run(
    brain_dir,
    name: str,
    prompt: str,
    artifact: str = "",
    response: str = "",
    transcript_mtime: float | None = None,
    dir_mtime: float | None = None,
    flat_transcript: bool = False,
) -> None:
    """Create a brain run dir mirroring the real Antigravity CLI layout.

    Real runs store the transcript at ``.system_generated/logs/transcript.jsonl``
    (JSONL entries with source/type/content; the user prompt appears inside a
    ``<USER_REQUEST>`` wrapper and the final answer in the last MODEL
    PLANNER_RESPONSE). ``flat_transcript=True`` reproduces the legacy layout
    with ``transcript.jsonl`` at the run root.
    """
    run_dir = brain_dir / name
    entries = [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "content": f"<USER_REQUEST>\n{prompt}\n</USER_REQUEST>",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "content": response,
        },
    ]
    if flat_transcript:
        run_dir.mkdir(parents=True)
        transcript = run_dir / "transcript.jsonl"
    else:
        logs_dir = run_dir / ".system_generated" / "logs"
        logs_dir.mkdir(parents=True)
        transcript = logs_dir / "transcript.jsonl"
    transcript.write_text(
        "".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8"
    )
    if artifact:
        (run_dir / "result.md").write_text(artifact, encoding="utf-8")
    if transcript_mtime is not None:
        os.utime(transcript, (transcript_mtime, transcript_mtime))
    if dir_mtime is not None:
        os.utime(run_dir, (dir_mtime, dir_mtime))


@pytest.fixture
def brain_dir(cli_logger, tmp_path, monkeypatch):
    path = tmp_path / "brain"
    path.mkdir()
    monkeypatch.setenv("CLAUDE_AGY_BRAIN_DIR", str(path))
    return path


def test_recover_agy_output_reads_matching_run(cli_logger, brain_dir):
    """Transcript is found at the real nested path, artifact returned."""
    mod, _ = cli_logger
    _make_brain_run(
        brain_dir, "run-a", "describe @img.png", artifact="A cat on a chair."
    )
    assert mod.recover_agy_output("describe @img.png") == "A cat on a chair."


def test_recover_agy_output_skips_parallel_run_with_other_prompt(cli_logger, brain_dir):
    """A newer run from a parallel agy call must not be attributed to this one."""
    mod, _ = cli_logger
    now = time.time()
    _make_brain_run(
        brain_dir,
        "run-mine",
        "describe @img.png",
        artifact="A cat on a chair.",
        transcript_mtime=now - 10,
    )
    _make_brain_run(
        brain_dir,
        "run-other",
        "extract @invoice.pdf",
        artifact="Invoice total: 42.",
        transcript_mtime=now,
    )
    assert mod.recover_agy_output("describe @img.png") == "A cat on a chair."


def test_recover_agy_output_returns_none_without_match(cli_logger, brain_dir):
    mod, _ = cli_logger
    _make_brain_run(
        brain_dir, "run-other", "extract @invoice.pdf", artifact="Invoice total: 42."
    )
    assert mod.recover_agy_output("describe @img.png") is None


def test_recover_agy_output_ignores_stale_run_with_same_prompt(cli_logger, brain_dir):
    """An old run matching the prompt must not be attributed to this call.

    Repeated prompts (e.g. `agy -p "describe @img.png"` run again days later)
    would otherwise resurface a previous run's artifacts as this call's output.
    """
    mod, _ = cli_logger
    stale = time.time() - mod.MAX_BRAIN_RUN_AGE_SECONDS - 60
    _make_brain_run(
        brain_dir,
        "run-old",
        "describe @img.png",
        artifact="A cat on a chair.",
        transcript_mtime=stale,
        dir_mtime=stale,
    )
    assert mod.recover_agy_output("describe @img.png") is None


def test_recover_agy_output_survives_long_runs(cli_logger, brain_dir):
    """Long jobs: run dir mtime reflects the START of the run, so a video
    analysis can leave the dir mtime far older than the age cutoff. Recency
    must be judged on the transcript, which is written until agy exits."""
    mod, _ = cli_logger
    now = time.time()
    _make_brain_run(
        brain_dir,
        "run-long",
        "summarize @video.mp4",
        artifact="Key moments: ...",
        transcript_mtime=now,
        dir_mtime=now - mod.MAX_BRAIN_RUN_AGE_SECONDS - 600,
    )
    assert mod.recover_agy_output("summarize @video.mp4") == "Key moments: ..."


def test_recover_agy_output_falls_back_to_planner_response(cli_logger, brain_dir):
    """Short extractions often leave no *.md artifact; the answer then only
    exists as the final MODEL PLANNER_RESPONSE inside the transcript."""
    mod, _ = cli_logger
    _make_brain_run(brain_dir, "run-a", "what is the secret word", response="BANANA")
    assert mod.recover_agy_output("what is the secret word") == "BANANA"


def test_recover_agy_output_prefers_artifact_over_planner_response(
    cli_logger, brain_dir
):
    mod, _ = cli_logger
    _make_brain_run(
        brain_dir,
        "run-a",
        "describe @img.png",
        artifact="Full report.",
        response="Short summary.",
    )
    assert mod.recover_agy_output("describe @img.png") == "Full report."


def test_recover_agy_output_returns_none_when_run_has_no_content(cli_logger, brain_dir):
    """A matched run with neither artifacts nor planner text (e.g. quota
    exhaustion) is unrecoverable — not an excuse to scan other runs."""
    mod, _ = cli_logger
    _make_brain_run(brain_dir, "run-dead", "describe @img.png")
    assert mod.recover_agy_output("describe @img.png") is None


def test_recover_agy_output_matches_prompt_with_json_escaped_chars(
    cli_logger, brain_dir
):
    """Prompts with quotes/backslashes are JSON-escaped inside the raw
    transcript file; matching must compare against the decoded content, not
    the raw JSONL text, or the call's own run is skipped as unrelated."""
    mod, _ = cli_logger
    prompt = 'describe "the cat" and C:\\photos @img.png'
    _make_brain_run(brain_dir, "run-a", prompt, artifact="A cat on a chair.")
    assert mod.recover_agy_output(prompt) == "A cat on a chair."


def test_recover_agy_output_reads_legacy_flat_transcript(cli_logger, brain_dir):
    """Older CLI builds wrote transcript.jsonl at the run root."""
    mod, _ = cli_logger
    _make_brain_run(
        brain_dir,
        "run-a",
        "describe @img.png",
        artifact="A cat on a chair.",
        flat_transcript=True,
    )
    assert mod.recover_agy_output("describe @img.png") == "A cat on a chair."


def test_recover_agy_output_returns_none_when_brain_dir_missing(
    cli_logger, tmp_path, monkeypatch
):
    mod, _ = cli_logger
    monkeypatch.setenv("CLAUDE_AGY_BRAIN_DIR", str(tmp_path / "no-such-dir"))
    assert mod.recover_agy_output("describe @img.png") is None


def test_check_recovers_empty_stdout_agy_from_brain(cli_logger, brain_dir):
    """Non-TTY agy run (exit 0, empty stdout) is logged with the brain output."""
    mod, log_file = cli_logger
    _make_brain_run(
        brain_dir, "run-a", "describe @img.png", artifact="A cat on a chair."
    )
    result = mod.check(_bash('agy -p "describe @img.png"', stdout="", exit_code=0))
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["success"] is True
    assert entry["response"] == "A cat on a chair."
    assert entry["recovered_from_brain"] is True
    assert "stdout_empty" not in entry


def test_check_flags_unrecoverable_empty_stdout_agy(cli_logger, brain_dir):
    """exit 0 + empty stdout + no attributable run → flagged, not silently failed."""
    mod, log_file = cli_logger
    result = mod.check(_bash('agy -p "describe @img.png"', stdout="", exit_code=0))
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["success"] is False
    assert entry["response"] == ""
    assert entry["stdout_empty"] is True
    assert "recovered_from_brain" not in entry


def test_truncate_text_preserves_short(cli_logger):
    mod, _ = cli_logger
    assert mod.truncate_text("hello", max_length=10) == "hello"


def test_truncate_text_truncates_long(cli_logger):
    mod, _ = cli_logger
    text = "x" * 3000
    truncated = mod.truncate_text(text, max_length=2000)
    assert truncated.startswith("x" * 2000)
    assert "truncated" in truncated
    assert "3000 total" in truncated


def test_check_writes_codex_entry(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('codex exec "Hello world"', stdout="Hi there", exit_code=0)
    result = mod.check(payload)
    assert result is not None
    assert "[LOG]" in result["additionalContext"]
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tool"] == "codex"
    assert entry["prompt"] == "Hello world"
    assert entry["response"] == "Hi there"
    assert entry["success"] is True
    assert entry["exit_code"] == 0


def test_check_writes_agy_entry(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('agy -p "describe @img.png"', stdout="A cat", exit_code=0)
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["prompt"] == "describe @img.png"
    # Model label defaults to the tool name; --model overrides record the flag.
    assert entry["model"] == "agy"


def test_check_writes_agy_entry_with_model_flag(cli_logger):
    mod, log_file = cli_logger
    payload = _bash(
        "agy --model gemini-3.1-pro -p 'read @doc.pdf'",
        stdout="Doc content",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["model"] == "gemini-3.1-pro"


def test_check_appends_multiple_entries(cli_logger):
    mod, log_file = cli_logger
    mod.check(_bash('codex exec "first"', stdout="a"))
    mod.check(_bash('codex exec "second"', stdout="b"))
    mod.check(_bash('codex exec "third"', stdout="c"))
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    prompts = [json.loads(line)["prompt"] for line in lines]
    assert prompts == ["first", "second", "third"]


def test_non_codex_agy_command_skipped(cli_logger):
    mod, log_file = cli_logger
    assert mod.check(_bash("ls -la", stdout="a\nb")) is None
    assert not log_file.exists() or log_file.read_text() == ""


def test_codex_without_quoted_prompt_skipped(cli_logger):
    mod, log_file = cli_logger
    assert mod.check(_bash("codex --version", stdout="0.1")) is None
    assert not log_file.exists() or log_file.read_text() == ""


def test_failure_marked_success_false(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('codex exec "boom"', stdout="", exit_code=1)
    mod.check(payload)
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["success"] is False
    assert entry["exit_code"] == 1
