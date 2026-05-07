"""Install production-grade skills + protocols into QwenPaw agent workspaces.

The installer prefers **bundled** content if this plugin's ``skills/`` and
``protocols/`` dirs are populated (run ``python -m
production_grade.port_from_upstream`` once to populate). If the bundled dirs
are missing or empty, it falls back to **live-porting** from your local copy
of ``nagisanzenin/claude-code-production-grade-plugin`` (MIT) at install time.

Upstream resolution order (live-port fallback only):

1. ``CLAUDE_PRODUCTION_GRADE_UPSTREAM`` env var (absolute path)
2. ``~/Documents/Github/claude-code-production-grade-plugin/`` (default)
3. Sibling directory next to this plugin
4. ``~/.claude/plugins/cache/nagisanzenin/production-grade/<version>/``

Each agent workspace gets:

- ``skills/<name>/SKILL.md``                   — adapted skill body
- ``production-grade-protocols/<name>.md``     — verbatim protocol files

Adapted skills written to a workspace have their ``${PG_PROTOCOLS}``
placeholder replaced with the workspace's absolute protocols dir, so the
model can ``read_file`` protocols without environment variables.
"""
from __future__ import annotations

import logging
import os
import shutil
import traceback
from pathlib import Path

from production_grade.port_logic import adapt_skill

log = logging.getLogger("production-grade.installer")

# ─── Public API ─────────────────────────────────────────────────────────────


def install_skills_to_all_workspaces(plugin_root: Path) -> int:
    """Install skills + protocols into every QwenPaw agent workspace.

    Returns the number of workspaces written to. Bundled-first; falls back to
    live-porting from upstream when bundled dirs are empty.
    """
    bundle = _find_bundle(plugin_root)
    if bundle is not None:
        skills_src, protocols_src = bundle
        bundled = True
        print(
            f"[production-grade] using bundled skills+protocols from "
            f"{plugin_root}",
            flush=True,
        )
    else:
        upstream = _resolve_upstream(plugin_root)
        if upstream is None:
            raise FileNotFoundError(
                "No bundled skills/ in this plugin and no upstream "
                "production-grade plugin found. Either run "
                "`python -m production_grade.port_from_upstream` to "
                "populate skills/ and protocols/, or set "
                "CLAUDE_PRODUCTION_GRADE_UPSTREAM=/abs/path."
            )
        log.info("upstream resolved to %s", upstream)
        skills_src = upstream / "skills"
        protocols_src = skills_src / "_shared" / "protocols"
        bundled = False
        print(
            f"[production-grade] live-porting from upstream at {upstream}",
            flush=True,
        )

    if not skills_src.is_dir():
        raise FileNotFoundError(f"skills source dir missing: {skills_src}")

    ws_root = _resolve_workspaces_root()
    if not ws_root.exists():
        log.warning("no QwenPaw workspaces found at %s", ws_root)
        print(
            f"[production-grade] no workspaces at {ws_root}; "
            f"run `qwenpaw init --defaults` first",
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
            bundled=bundled,
        )
        n += 1
    return n


# ─── Workspace install ──────────────────────────────────────────────────────


def _install_into_workspace(
    *,
    workspace: Path,
    skills_src: Path,
    protocols_src: Path,
    bundled: bool,
) -> None:
    dst_skills = workspace / "skills"
    dst_protocols = workspace / "production-grade-protocols"
    dst_skills.mkdir(exist_ok=True)
    dst_protocols.mkdir(exist_ok=True)

    # Protocols: verbatim copy.
    if protocols_src.is_dir():
        for src in protocols_src.iterdir():
            if src.is_file() and src.suffix == ".md":
                shutil.copy2(src, dst_protocols / src.name)

    # Skills:
    #   - bundled: adaptation already applied at port time; only the
    #     ${PG_PROTOCOLS} placeholder needs to be substituted to the
    #     workspace's absolute protocols path.
    #   - live: read upstream SKILL.md and adapt fully on the fly.
    n_skills = 0
    for src_dir in skills_src.iterdir():
        if not src_dir.is_dir() or src_dir.name.startswith("_"):
            continue  # skip _shared/, _archive/, etc.
        src_md = src_dir / "SKILL.md"
        if not src_md.is_file():
            continue
        dst_dir = dst_skills / src_dir.name
        dst_dir.mkdir(exist_ok=True)
        text = src_md.read_text(encoding="utf-8")
        if bundled:
            text = text.replace("${PG_PROTOCOLS}", str(dst_protocols))
        else:
            text = adapt_skill(text, protocols_dir=dst_protocols)
        (dst_dir / "SKILL.md").write_text(text, encoding="utf-8")
        n_skills += 1

    log.info("workspace %s: installed %d skills", workspace.name, n_skills)
    print(
        f"[production-grade]   ✓ {workspace.name}: {n_skills} skills",
        flush=True,
    )


# ─── Bundle / upstream resolution ──────────────────────────────────────────


def _find_bundle(plugin_root: Path) -> tuple[Path, Path] | None:
    """Return ``(skills_dir, protocols_dir)`` if the plugin has bundled
    content, else ``None``."""
    skills = plugin_root / "skills"
    protocols = plugin_root / "protocols"
    has_skills = skills.is_dir() and any(
        (p / "SKILL.md").is_file()
        for p in skills.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if has_skills:
        return skills, protocols if protocols.is_dir() else skills / "_protocols_missing"
    return None


def _resolve_upstream(plugin_root: Path) -> Path | None:
    candidates: list[Path] = []
    env = os.environ.get("CLAUDE_PRODUCTION_GRADE_UPSTREAM")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        Path.home() / "Documents" / "Github" / "claude-code-production-grade-plugin",
        plugin_root.parent / "claude-code-production-grade-plugin",
    ])
    cache = (
        Path.home() / ".claude" / "plugins" / "cache"
        / "nagisanzenin" / "production-grade"
    )
    if cache.is_dir():
        for v in sorted(
            (p for p in cache.iterdir() if p.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        ):
            candidates.append(v)

    for c in candidates:
        if c.is_dir() and (c / "skills").is_dir():
            return c.resolve()
    return None


def _resolve_workspaces_root() -> Path:
    try:
        from qwenpaw.constant import WORKING_DIR  # type: ignore[import]

        return Path(WORKING_DIR).expanduser() / "workspaces"
    except Exception:  # noqa: BLE001
        return Path.home() / ".qwenpaw" / "workspaces"
