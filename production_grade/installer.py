"""Install production-grade skills + protocols into QwenPaw agent workspaces.

The plugin does not bundle the skill bodies. Instead, it reads them from the
user's own upstream copy of ``nagisanzenin/claude-code-production-grade-plugin``
(MIT licensed) at install time and writes adapted versions into each QwenPaw
agent workspace.

Upstream resolution order:

1. ``CLAUDE_PRODUCTION_GRADE_UPSTREAM`` environment variable (absolute path)
2. ``~/Documents/Github/claude-code-production-grade-plugin/`` (default)
3. ``~/.claude/plugins/cache/nagisanzenin/production-grade/<version>/``
4. Sibling directory ``../claude-code-production-grade-plugin/``

The first path that contains a ``skills/`` directory wins.

Each agent workspace gets:

- ``skills/<name>/SKILL.md``  — adapted skill body
- ``production-grade-protocols/<name>.md`` — verbatim protocol files

Adaptation rules (see ``adapt_skill`` in port_logic.py):

- Strip Claude-Code-specific frontmatter fields.
- Translate tool names (Read → read_file, etc.).
- Replace ``!`<cmd>` `` blocks with explicit ``read_file`` instructions
  pointing at ``${PG_PROTOCOLS}`` (set by this installer).
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from production_grade.port_logic import adapt_skill

log = logging.getLogger("production-grade.installer")


# ─── Public API ─────────────────────────────────────────────────────────────


def install_skills_to_all_workspaces(plugin_root: Path) -> int:
    """Find an upstream copy, then install adapted skills + protocols into every
    QwenPaw agent workspace.

    Returns the number of workspaces written to. Raises ``FileNotFoundError`` if
    no upstream copy is found and no skills are bundled in the plugin itself.
    """
    upstream = _resolve_upstream(plugin_root)
    if upstream is None:
        raise FileNotFoundError(
            "No upstream production-grade plugin found. Set "
            "CLAUDE_PRODUCTION_GRADE_UPSTREAM=/abs/path or clone "
            "https://github.com/nagisanzenin/claude-code-production-grade-plugin "
            "to ~/Documents/Github/claude-code-production-grade-plugin/."
        )
    log.info("upstream resolved to %s", upstream)
    print(f"[production-grade] upstream → {upstream}", flush=True)

    skills_src = upstream / "skills"
    protocols_src = skills_src / "_shared" / "protocols"
    if not skills_src.is_dir():
        raise FileNotFoundError(f"upstream missing skills/ dir: {skills_src}")

    ws_root = _resolve_workspaces_root()
    if not ws_root.exists():
        log.warning("no QwenPaw workspaces found at %s; nothing to install", ws_root)
        print(
            f"[production-grade] no workspaces at {ws_root}; run "
            f"`qwenpaw init --defaults` first",
            flush=True,
        )
        return 0

    n = 0
    for agent_dir in sorted(ws_root.iterdir()):
        if not agent_dir.is_dir():
            continue
        _install_into_workspace(
            workspace=agent_dir,
            skills_src=skills_src,
            protocols_src=protocols_src,
        )
        n += 1
    return n


# ─── Workspace install ──────────────────────────────────────────────────────


def _install_into_workspace(
    *,
    workspace: Path,
    skills_src: Path,
    protocols_src: Path,
) -> None:
    """Write adapted skills + protocols into one agent workspace."""
    dst_skills = workspace / "skills"
    dst_protocols = workspace / "production-grade-protocols"
    dst_skills.mkdir(exist_ok=True)
    dst_protocols.mkdir(exist_ok=True)

    # Protocols: verbatim copy (these are short, simple text rules).
    if protocols_src.is_dir():
        for src in protocols_src.iterdir():
            if src.is_file() and src.suffix == ".md":
                shutil.copy2(src, dst_protocols / src.name)

    # Skills: adapt each SKILL.md before writing.
    n_skills = 0
    for src_dir in skills_src.iterdir():
        if not src_dir.is_dir() or src_dir.name.startswith("_"):
            continue  # skip _shared/, _archive/, etc.
        src_md = src_dir / "SKILL.md"
        if not src_md.is_file():
            continue
        dst_dir = dst_skills / src_dir.name
        dst_dir.mkdir(exist_ok=True)
        adapted = adapt_skill(
            src_md.read_text(encoding="utf-8"),
            protocols_dir=dst_protocols,
        )
        (dst_dir / "SKILL.md").write_text(adapted, encoding="utf-8")
        n_skills += 1

    log.info("workspace %s: installed %d skills", workspace.name, n_skills)
    print(
        f"[production-grade]   ✓ {workspace.name}: {n_skills} skills",
        flush=True,
    )


# ─── Path resolution ────────────────────────────────────────────────────────


def _resolve_upstream(plugin_root: Path) -> Path | None:
    candidates: list[Path] = []
    env = os.environ.get("CLAUDE_PRODUCTION_GRADE_UPSTREAM")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        Path.home() / "Documents" / "Github" / "claude-code-production-grade-plugin",
        plugin_root.parent / "claude-code-production-grade-plugin",
    ])
    # Walk plugin cache too (latest version wins).
    cache = (
        Path.home() / ".claude" / "plugins" / "cache"
        / "nagisanzenin" / "production-grade"
    )
    if cache.is_dir():
        versions = sorted(
            (p for p in cache.iterdir() if p.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        )
        candidates.extend(versions)

    for c in candidates:
        if c.is_dir() and (c / "skills").is_dir():
            return c.resolve()
    return None


def _resolve_workspaces_root() -> Path:
    """Locate ``~/.qwenpaw/workspaces/`` via QwenPaw's own constant module
    when available; fall back to the documented default.
    """
    try:
        from qwenpaw.constant import WORKING_DIR  # type: ignore[import]

        return Path(WORKING_DIR).expanduser() / "workspaces"
    except Exception:  # noqa: BLE001
        return Path.home() / ".qwenpaw" / "workspaces"
