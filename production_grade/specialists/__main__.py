"""ACP specialist runner — entry point.

Spawned as a subprocess by QwenPaw via ``delegate_external_agent``.
Loads the named role's SKILL.md + 8 shared protocols from this plugin's
bundled ``skills/`` and ``protocols/``, builds a system prompt, and
streams LLM output back through the ACP protocol.

Designed to be small and testable on its own.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow direct module run (`python -m production_grade.specialists --role ...`).
if __name__ == "__main__":
    # Re-exec via the runner's main() below.
    pass

from production_grade.specialists.runner import SpecialistACPAgent, run_specialist


def _resolve_plugin_root(arg: str | None) -> Path:
    candidates = []
    if arg:
        candidates.append(Path(arg).expanduser())
    env = os.environ.get("PG_ROOT")
    if env:
        candidates.append(Path(env).expanduser())
    # Fall back: walk up from this file (production_grade/specialists/__main__.py)
    here = Path(__file__).resolve().parent.parent.parent
    candidates.append(here)
    for c in candidates:
        if c.is_dir() and (c / "skills").is_dir() and (c / "protocols").is_dir():
            return c.resolve()
    raise SystemExit(
        "Could not locate plugin root with skills/ and protocols/. "
        "Pass --plugin-root or set PG_ROOT."
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--role", required=True, help="Specialist role (e.g. polymath, software-engineer)")
    p.add_argument("--plugin-root", default=None, help="Path to qwenpaw-production-grade-plugin repo")
    p.add_argument("--copy", default="a", help="Copy suffix (a/b/c/...) for parallel parity")
    p.add_argument("--smoke", action="store_true",
                   help="Print system prompt size and exit (no ACP run)")
    args = p.parse_args()

    plugin_root = _resolve_plugin_root(args.plugin_root)
    skill_md = plugin_root / "skills" / args.role / "SKILL.md"
    if not skill_md.is_file():
        raise SystemExit(f"No SKILL.md for role={args.role!r} at {skill_md}")

    if args.smoke:
        agent = SpecialistACPAgent(role=args.role, copy=args.copy, plugin_root=plugin_root)
        sp = agent.system_prompt
        print(f"role: {args.role}")
        print(f"copy: {args.copy}")
        print(f"plugin_root: {plugin_root}")
        print(f"system_prompt: {len(sp)} chars  ({len(sp.splitlines())} lines)")
        print(f"first 80 chars: {sp[:80].replace(chr(10), ' ')!r}")
        return 0

    # Real ACP run.
    try:
        asyncio.run(run_specialist(role=args.role, copy=args.copy, plugin_root=plugin_root))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
