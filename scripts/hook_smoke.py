"""End-to-end smoke for the v0.2 hooks attached against the user's QwenPaw.

Run from the plugin repo root::

    make hook-smoke
    # or:
    python3 scripts/hook_smoke.py

Exits 0 on success, non-zero on any check failure. Safe to run repeatedly.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def main() -> int:
    from production_grade.hooks import (
        _expand_backtick_bang_in_text, _ACTIVATION_RULES, install_hooks, _INSTALLED,
    )

    print("=" * 60)
    print("backtick-bang expansion (P3)")
    print("=" * 60)
    sample = "header\n!`echo hello` middle !`echo world` end\n"
    out = _expand_backtick_bang_in_text(sample, "/tmp")
    print(f"  in : {sample!r}")
    print(f"  out: {out!r}")
    assert "hello" in out and "world" in out and "!`" not in out, out
    print("  ok")

    print()
    print("=" * 60)
    print("activation rules (P4)")
    print("=" * 60)
    samples = [
        ("build me a saas", "production-grade"),
        ("review for security audit using owasp threat model", "security-engineer"),
        ("write tests for the auth flow", "qa-engineer"),
        ("deploy to terraform on aws", "devops"),
        ("production-grade everything", "production-grade"),
        ("what time is it?", None),
    ]
    fails = 0
    for text, expected in samples:
        fired = [s for pat, s, _ in _ACTIVATION_RULES if pat.search(text)]
        ok = (expected in fired) if expected else (not fired)
        flag = "✓" if ok else "✗"
        print(f"  {flag}  {text!r:60s} → {fired or '[]'}")
        if not ok:
            fails += 1
    if fails:
        print(f"  {fails} activation rule mismatches")
        return 1

    print()
    print("=" * 60)
    print("install_hooks() — P2 + P3 + P4 attach")
    print("=" * 60)
    install_hooks(plugin_root=REPO)
    print(f"  state: {_INSTALLED}")
    if not all(_INSTALLED.values()):
        print(f"  one or more hooks did not install: {_INSTALLED}")
        return 1

    try:
        from qwenpaw.agents.react_agent import QwenPawAgent
        from qwenpaw.app.runner.runner import AgentRunner
    except Exception as exc:  # noqa: BLE001
        print(f"  qwenpaw not importable in this venv: {exc}")
        return 1
    pre_reply = QwenPawAgent._class_pre_reply_hooks
    post_acting = QwenPawAgent._class_post_acting_hooks
    skill_patched = bool(getattr(AgentRunner._maybe_inject_skill, "_pg_patched", False))
    print(f"  pre_reply hooks:    {sorted(pre_reply.keys())}")
    print(f"  post_acting hooks:  {sorted(post_acting.keys())}")
    print(f"  skill loader patched: {skill_patched}")
    if "pg_session_guard_and_activation" not in pre_reply: return 1
    if "pg_auto_receipt" not in post_acting: return 1
    if not skill_patched: return 1

    # Idempotency
    print()
    print("Re-installing to test idempotency...")
    install_hooks(plugin_root=REPO)
    if sorted(QwenPawAgent._class_pre_reply_hooks.keys()) != sorted(pre_reply.keys()):
        print("  duplicate registration on re-install")
        return 1
    print("  ok (no duplicates)")

    print()
    print("=" * 60)
    print("ALL CHECKS PASS")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
