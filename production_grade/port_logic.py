"""Port a single SKILL.md from the Claude Code form to the QwenPaw form.

The transformation is mechanical and reversible-ish:

1. Strip Claude-Code-specific YAML frontmatter fields that have no QwenPaw
   equivalent (``allowed-tools``, ``model``, ``disable-model-invocation``,
   ``argument-hint``, ``arguments``, ``paths``, ``hooks``).

2. Translate tool name references in prose:
   ``Read`` → ``read_file``, ``Write`` → ``write_file``,
   ``Edit`` → ``edit_file``, ``Glob`` → ``glob_search``,
   ``Grep`` → ``grep_search``, ``Bash`` → ``execute_shell_command``,
   ``WebSearch`` → ``tavily_search``, ``WebFetch`` → ``tavily_search``,
   ``AskUserQuestion`` → "structured options + plain-text reply"
   (note this is a UX downgrade in v0.1).

3. Replace inline shell preprocessing blocks ``!`<cmd>` `` (which Claude
   Code expands at skill load time) with explicit instructions to read
   the corresponding protocol file via ``read_file``. The protocol files
   live next to the skill in ``${PG_PROTOCOLS}`` (set by the installer).

4. Append a v0.1 footer noting which Claude Code primitives are not
   available on QwenPaw yet (so the model adapts its expectations).
"""
from __future__ import annotations

import re
from pathlib import Path

# ─── Frontmatter handling ───────────────────────────────────────────────────

# Fields with no QwenPaw equivalent in the skill spec.
_FRONTMATTER_DROP = {
    "allowed-tools",
    "model",
    "disable-model-invocation",
    "user-invocable",
    "argument-hint",
    "arguments",
    "paths",
    "hooks",
    "context",
    "agent",
    "shell",
    "effort",
    "when_to_use",  # merged into description
}

_FM_FENCE = "---"


# ─── Tool name translation ──────────────────────────────────────────────────

# Word-boundary anchored replacements applied to skill body prose.
_TOOL_TRANSLATIONS: list[tuple[re.Pattern[str], str]] = [
    # Tool calls written as Claude Code syntax: `Read(path)` → `read_file(path)`.
    (re.compile(r"\bRead\(", re.UNICODE), "read_file("),
    (re.compile(r"\bWrite\(", re.UNICODE), "write_file("),
    (re.compile(r"\bEdit\(", re.UNICODE), "edit_file("),
    (re.compile(r"\bGlob\(", re.UNICODE), "glob_search("),
    (re.compile(r"\bGrep\(", re.UNICODE), "grep_search("),
    (re.compile(r"\bBash\(", re.UNICODE), "execute_shell_command("),
    (re.compile(r"\bWebSearch\(", re.UNICODE), "tavily_search("),
    (re.compile(r"\bWebFetch\(", re.UNICODE), "tavily_search("),
    # Function-call form of higher-level Claude Code primitives that don't have
    # a 1:1 QwenPaw v0.1 equivalent. Annotate inline so the model reads the
    # methodology + the v0.1 hint together.
    (re.compile(r"\bAgent\(", re.UNICODE),
     "<!-- v0.1: do this work yourself; no subagent spawn --> Agent("),
    (re.compile(r"\bTask\(", re.UNICODE),
     "<!-- v0.1: do this work yourself; no subagent spawn --> Task("),
    (re.compile(r"\bSkill\(", re.UNICODE),
     "<!-- v0.1: read the sub-skill SKILL.md inline --> Skill("),
    (re.compile(r"\bAskUserQuestion\(", re.UNICODE),
     "<!-- v0.1: render numbered options as plain Markdown; parse reply --> AskUserQuestion("),
    (re.compile(r"\bTaskCreate\(", re.UNICODE),
     "<!-- v0.1: emit a status line in chat --> TaskCreate("),
    (re.compile(r"\bTaskUpdate\(", re.UNICODE),
     "<!-- v0.1: emit a status line in chat --> TaskUpdate("),
    (re.compile(r"\bTaskList\(", re.UNICODE),
     "<!-- v0.1: emit a status line in chat --> TaskList("),
    (re.compile(r"\bTeamCreate\(", re.UNICODE),
     "<!-- v0.1: no-op --> TeamCreate("),
    (re.compile(r"\bTeamDelete\(", re.UNICODE),
     "<!-- v0.1: no-op --> TeamDelete("),
    (re.compile(r"\bSendMessage\(", re.UNICODE),
     "<!-- v0.1: no-op --> SendMessage("),
    # Backtick-quoted tool names.
    (re.compile(r"`Read`", re.UNICODE), "`read_file`"),
    (re.compile(r"`Write`", re.UNICODE), "`write_file`"),
    (re.compile(r"`Edit`", re.UNICODE), "`edit_file`"),
    (re.compile(r"`Glob`", re.UNICODE), "`glob_search`"),
    (re.compile(r"`Grep`", re.UNICODE), "`grep_search`"),
    (re.compile(r"`Bash`", re.UNICODE), "`execute_shell_command`"),
    (re.compile(r"`WebSearch`", re.UNICODE), "`tavily_search`"),
    (re.compile(r"`WebFetch`", re.UNICODE), "`tavily_search`"),
    (re.compile(r"`Skill`", re.UNICODE), "`(in-skill phase routing)`"),
    (re.compile(r"`Agent`", re.UNICODE), "`(deferred to v0.2 — single-agent flow)`"),
    (re.compile(r"`Task`", re.UNICODE), "`(deferred to v0.2 — single-agent flow)`"),
    (re.compile(r"`AskUserQuestion`", re.UNICODE),
     "`(plain-text option list — type the option name)`"),
    (re.compile(r"`TaskCreate`", re.UNICODE), "`(write a status line, then continue)`"),
    (re.compile(r"`TaskUpdate`", re.UNICODE), "`(write a status line, then continue)`"),
    (re.compile(r"`TaskList`", re.UNICODE), "`(write a status line, then continue)`"),
    (re.compile(r"`TeamCreate`", re.UNICODE), "`(no-op in v0.1)`"),
    (re.compile(r"`TeamDelete`", re.UNICODE), "`(no-op in v0.1)`"),
    (re.compile(r"`SendMessage`", re.UNICODE), "`(no-op in v0.1)`"),
]


# ─── Inline shell-preprocessing blocks ──────────────────────────────────────

# Production-grade SKILL.md bodies start with blocks like
#   !`cat Claude-Production-Grade-Suite/.protocols/ux-protocol.md 2>/dev/null || true`
# Claude Code preprocesses these at skill load. QwenPaw does not.
#
# Transform target — replace the block with an explicit instruction to read
# the protocol via ``read_file`` from the per-workspace protocols dir.
_BACKTICK_BANG_RE = re.compile(r"!`([^`]+)`", re.UNICODE)
_PROTOCOL_PATH_RE = re.compile(
    r"(?:Claude-Production-Grade-Suite/\.protocols|\.protocols|protocols)/"
    r"(?P<name>[a-z0-9_\-]+)\.md",
    re.UNICODE,
)


def _replace_backtick_bang(body: str, protocols_dir: Path) -> str:
    """Replace ``!`cat .../<name>.md` `` patterns with read_file instructions."""

    def sub(m: re.Match[str]) -> str:
        cmd = m.group(1)
        prot = _PROTOCOL_PATH_RE.search(cmd)
        if prot:
            name = prot.group("name")
            return (
                f"<!-- protocol injection (was: !`{cmd}`) -->\n"
                f"Read protocol: `{protocols_dir / name}.md` "
                f"(use the `read_file` tool before continuing)."
            )
        # Generic fallback: keep the command but flag it for the model.
        return (
            f"<!-- inline shell (was: !`{cmd}`) -->\n"
            f"Run shell command before continuing: ``{cmd}``\n"
            f"(use the `execute_shell_command` tool)."
        )

    return _BACKTICK_BANG_RE.sub(sub, body)


# ─── Top-level adapter ──────────────────────────────────────────────────────


_V01_FOOTER = """

<!-- production-grade v0.1 port adaptation notes -->
> This skill body has been adapted for QwenPaw. Differences vs the upstream
> Claude Code plugin to be aware of:
>
> - **No `AskUserQuestion` tool.** When this skill says to surface a decision,
>   render numbered options as plain Markdown and ask the user to type the
>   option name. Parse free-text replies leniently.
> - **No `Skill` tool.** Phase transitions happen in-line: read the next
>   sub-skill body via `read_file` from the workspace `skills/` dir.
> - **No subagent spawn.** v0.1 is a single-agent flow. If the methodology
>   says "delegate to specialist X", invoke X by reading its `SKILL.md` from
>   `skills/<name>/SKILL.md` and following its instructions yourself.
> - **No `TaskCreate`/`TaskList`.** Track progress by writing receipts to
>   `Claude-Production-Grade-Suite/.orchestrator/receipts/<task>-<role>.json`
>   and emitting a one-line status update in chat after each phase.
> - **`WebSearch` is `tavily_search`.** Requires `TAVILY_API_KEY`. If unset,
>   skip the Freshness Protocol and note it.
"""


def adapt_skill(source: str, *, protocols_dir: Path) -> str:
    """Transform an upstream SKILL.md into a QwenPaw-compatible SKILL.md.

    ``source`` is the full file content, including YAML frontmatter.
    ``protocols_dir`` is the absolute path to the workspace protocols dir,
    embedded into the body so the model can read protocols by absolute path.
    """
    fm, body = _split_frontmatter(source)
    fm = _filter_frontmatter(fm)
    body = _replace_backtick_bang(body, protocols_dir)
    for pattern, repl in _TOOL_TRANSLATIONS:
        body = pattern.sub(repl, body)
    body = body.rstrip() + _V01_FOOTER
    return _join_frontmatter(fm, body)


# ─── Frontmatter helpers ────────────────────────────────────────────────────


def _split_frontmatter(text: str) -> tuple[list[str], str]:
    """Return (frontmatter_lines, body). frontmatter excludes the fences."""
    lines = text.splitlines(keepends=False)
    if len(lines) < 2 or lines[0].strip() != _FM_FENCE:
        return [], text
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FM_FENCE:
            end = i
            break
    if end is None:
        return [], text
    fm = lines[1:end]
    body = "\n".join(lines[end + 1:])
    return fm, body


def _filter_frontmatter(fm: list[str]) -> list[str]:
    """Drop top-level frontmatter keys we know don't translate."""
    out: list[str] = []
    drop_block = False
    for line in fm:
        # YAML key detection: only at column 0 (top-level keys).
        m = re.match(r"^([A-Za-z][A-Za-z0-9_\-]*)\s*:", line)
        if m:
            key = m.group(1)
            if key in _FRONTMATTER_DROP:
                drop_block = True
                continue
            drop_block = False
            out.append(line)
        elif drop_block:
            # Continuation line of a dropped block (indented or list item).
            if line.startswith((" ", "\t", "-")):
                continue
            drop_block = False
            out.append(line)
        else:
            out.append(line)
    return out


def _join_frontmatter(fm: list[str], body: str) -> str:
    if not fm:
        return body
    fm_text = "\n".join(fm)
    return f"{_FM_FENCE}\n{fm_text}\n{_FM_FENCE}\n{body}"
