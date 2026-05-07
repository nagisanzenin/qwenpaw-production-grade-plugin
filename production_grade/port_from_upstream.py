"""CLI to (re-)port skills + protocols from a local upstream copy of
``nagisanzenin/claude-code-production-grade-plugin`` into this plugin's
``skills/`` and ``protocols/`` directories.

Run once at port time, or whenever upstream changes::

    python -m production_grade.port_from_upstream

By default the upstream is resolved the same way as ``installer.py``:

1. ``$CLAUDE_PRODUCTION_GRADE_UPSTREAM``
2. ``~/Documents/Github/claude-code-production-grade-plugin/``
3. Sibling directory of this plugin
4. ``~/.claude/plugins/cache/nagisanzenin/production-grade/<version>/``

Override with ``--upstream /abs/path``.

Outputs:
- ``skills/<name>/SKILL.md`` — adapted via ``port_logic.adapt_skill``
- ``protocols/<name>.md``   — copied verbatim
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from production_grade.port_logic import adapt_skill

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DST = REPO_ROOT / "skills"
PROTOCOLS_DST = REPO_ROOT / "protocols"


def resolve_upstream(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env = os.environ.get("CLAUDE_PRODUCTION_GRADE_UPSTREAM")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        Path.home() / "Documents" / "Github" / "claude-code-production-grade-plugin",
        REPO_ROOT.parent / "claude-code-production-grade-plugin",
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
    raise FileNotFoundError(
        "Upstream not found. Set CLAUDE_PRODUCTION_GRADE_UPSTREAM=/abs/path "
        "or pass --upstream."
    )


def port_skill(src_md: Path, dst_md: Path) -> None:
    """Adapt one SKILL.md and write to dst.

    Note: ``adapt_skill`` embeds an absolute protocols dir into its
    rendered ``read_file`` instructions. At port time we don't yet know
    which workspace the skill will live in, so we use a placeholder
    that ``installer.py`` rewrites at install time.
    """
    placeholder = Path("${PG_PROTOCOLS}")
    adapted = adapt_skill(src_md.read_text(encoding="utf-8"), protocols_dir=placeholder)
    dst_md.parent.mkdir(parents=True, exist_ok=True)
    dst_md.write_text(adapted, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream", help="Absolute path to upstream plugin")
    p.add_argument("--clean", action="store_true",
                   help="Remove existing skills/ and protocols/ before porting")
    args = p.parse_args(argv)

    try:
        upstream = resolve_upstream(args.upstream)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"upstream = {upstream}")
    skills_src = upstream / "skills"
    protocols_src = skills_src / "_shared" / "protocols"

    if args.clean:
        if SKILLS_DST.exists():
            shutil.rmtree(SKILLS_DST)
        if PROTOCOLS_DST.exists():
            shutil.rmtree(PROTOCOLS_DST)
    SKILLS_DST.mkdir(exist_ok=True)
    PROTOCOLS_DST.mkdir(exist_ok=True)

    # Skills
    n_skills = 0
    for src_dir in sorted(skills_src.iterdir()):
        if not src_dir.is_dir() or src_dir.name.startswith("_"):
            continue
        src_md = src_dir / "SKILL.md"
        if not src_md.is_file():
            continue
        dst_md = SKILLS_DST / src_dir.name / "SKILL.md"
        port_skill(src_md, dst_md)
        n_skills += 1
        print(f"  ✓ skill: {src_dir.name}")

    # Protocols (verbatim)
    n_protocols = 0
    if protocols_src.is_dir():
        for src in sorted(protocols_src.iterdir()):
            if src.is_file() and src.suffix == ".md":
                shutil.copy2(src, PROTOCOLS_DST / src.name)
                n_protocols += 1
                print(f"  ✓ protocol: {src.name}")

    print(f"\nPorted {n_skills} skills + {n_protocols} protocols.")
    print(f"  skills/    → {SKILLS_DST}")
    print(f"  protocols/ → {PROTOCOLS_DST}")
    print("\nNext: commit, then `qwenpaw plugin install . --force`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
