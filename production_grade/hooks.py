"""v0.2 hooks — bridges the remaining capability gap to Claude Code parity.

Three pieces, installed at plugin startup:

P2 — Auto-receipt enforcement
    `post_acting` class hook on QwenPawAgent. When the orchestrator
    completes a `delegate_external_agent` call, this hook writes a stub
    receipt JSON into `Claude-Production-Grade-Suite/.orchestrator/receipts/`
    so the protocol's audit trail survives even when the model forgets.
    The orchestrator can then enrich the receipt with metrics/artifacts.

P3 — Runtime `!`<cmd>`` shell preprocessing
    Monkey-patches `qwenpaw.app.runner.runner.AgentRunner._maybe_inject_skill`
    to scan the rewritten user message after a slash-skill injection and
    expand `!`<cmd>`` patterns into their stdout (with timeout + cwd-aware
    execution). This restores the upstream Claude Code skill loader's
    cwd-sensitive protocol-loading behavior that the v0.1 port had to
    statify at port time.

P4 — SessionStart + UserPromptSubmit equivalents
    `pre_reply` class hook. Two responsibilities folded into one hook:
    - First time we see a session whose cwd contains
      `Claude-Production-Grade-Suite/`, prepend a recommendation pointing
      the model at /production-grade.
    - Every prompt: keyword/regex match against activation rules; if a
      production-grade pattern fires, prepend a routing hint.

All hooks wrap their bodies in try/except — a crash here must NEVER
break the user's chat turn. Failures log to stderr and the original
message/output flows through unchanged.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

log = logging.getLogger("production-grade.hooks")

# ─── Module state ───────────────────────────────────────────────────────────

_INSTALLED: dict[str, bool] = {
    "skill_loader_patch": False,
    "session_guard_hook": False,
    "auto_receipt_hook": False,
}

# Sessions for which we've already shown the project-detection prompt.
# Re-shown on a fresh QwenPaw process restart (intended).
_SEEN_SESSIONS: set[str] = set()

# Activation rules: prompt → recommended skill. Conservative — only fire
# on unambiguous build/audit/etc. signals.
_ACTIVATION_RULES = (
    (re.compile(r"\b(build|create)\s+(me\s+)?(a|an|the)\s+(saas|platform|service|api|app|system|product)\b", re.I),
     "production-grade",
     "Looks like a build request. Consider using /production-grade for the structured pipeline."),
    (re.compile(r"\b(production[\s-]?grade|production[\s-]?ready)\b", re.I),
     "production-grade", ""),
    (re.compile(r"\b(audit|harden|review)\b.*\b(security|owasp|threat\s*model)\b", re.I),
     "security-engineer",
     "Hint: /security-engineer for the structured audit, or /production-grade in MODE=Harden."),
    (re.compile(r"\b(write|add)\s+tests?\b|\btest\s+coverage\b", re.I),
     "qa-engineer",
     "Hint: /qa-engineer for the structured test pass."),
    (re.compile(r"\b(deploy|ci/cd|terraform|docker|kubernetes)\b", re.I),
     "devops",
     "Hint: /devops for the deployment scaffolding, or /production-grade in MODE=Ship."),
)


# ─── Public install entry ───────────────────────────────────────────────────


def install_hooks(plugin_root: Path) -> None:
    """Install P2/P3/P4 hooks. Idempotent and crash-tolerant."""
    _install_skill_loader_patch(plugin_root)
    _install_class_hooks(plugin_root)


# ─── P3 — Skill-loader monkey-patch ────────────────────────────────────────

_BACKTICK_BANG_RE = re.compile(r"!`([^`]+)`")


def _expand_backtick_bang_in_text(text: str, cwd: str | os.PathLike[str]) -> str:
    """Replace each ``!`<cmd>` `` token with the command's stdout.

    Timeout 10s per command, errors swallowed into a comment so the model
    sees the failure but the turn keeps moving.
    """

    def _sub(m: re.Match[str]) -> str:
        cmd = m.group(1)
        try:
            out = subprocess.run(
                cmd, shell=True,
                capture_output=True, text=True,
                timeout=10, cwd=str(cwd) or None,
            )
            return (out.stdout or out.stderr or "").rstrip("\n")
        except Exception as exc:  # noqa: BLE001
            return f"<!-- !`{cmd}` failed: {type(exc).__name__}: {exc} -->"

    return _BACKTICK_BANG_RE.sub(_sub, text)


def _install_skill_loader_patch(plugin_root: Path) -> None:
    if _INSTALLED["skill_loader_patch"]:
        return
    try:
        from qwenpaw.app.runner import runner as _r  # type: ignore[import]
    except Exception as exc:  # noqa: BLE001
        log.warning("skill-loader patch skipped (no qwenpaw runner): %s", exc)
        return

    AgentRunner = _r.AgentRunner
    if not hasattr(AgentRunner, "_maybe_inject_skill"):
        log.warning("skill-loader patch skipped (no _maybe_inject_skill on AgentRunner)")
        return
    if getattr(AgentRunner._maybe_inject_skill, "_pg_patched", False):
        _INSTALLED["skill_loader_patch"] = True
        return

    _orig = AgentRunner._maybe_inject_skill

    def _patched(query, msgs, skills):  # noqa: ANN001
        result = _orig(query, msgs, skills)
        # _orig returned None means "rewrite was applied to msgs[-1]".
        # We post-process by expanding any !`<cmd>` patterns the skill
        # body carries in.
        try:
            if result is None and msgs:
                last = msgs[-1]
                content = getattr(last, "content", None)
                if isinstance(content, list):
                    for blk in content:
                        text = None
                        # Msg uses dataclass-ish content blocks; tolerate dicts too.
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            text = blk.get("text")
                            if text and "!`" in text:
                                blk["text"] = _expand_backtick_bang_in_text(text, os.getcwd())
                        elif hasattr(blk, "text") and getattr(blk, "type", None) == "text":
                            text = blk.text
                            if text and "!`" in text:
                                try:
                                    blk.text = _expand_backtick_bang_in_text(text, os.getcwd())
                                except Exception:  # noqa: BLE001
                                    pass
        except Exception:  # noqa: BLE001
            log.warning("backtick-bang expansion crashed:\n%s", traceback.format_exc())
        return result

    _patched._pg_patched = True  # type: ignore[attr-defined]
    AgentRunner._maybe_inject_skill = staticmethod(_patched)
    _INSTALLED["skill_loader_patch"] = True
    log.info("[P3] skill loader patched: !`<cmd>` runtime expansion installed")
    print("[production-grade]   ✓ P3: !`<cmd>` runtime expansion installed", flush=True)


# ─── P2 + P4 — class hooks on QwenPawAgent ─────────────────────────────────


def _install_class_hooks(plugin_root: Path) -> None:
    try:
        from qwenpaw.agents.react_agent import QwenPawAgent  # type: ignore[import]
    except Exception as exc:  # noqa: BLE001
        log.warning("class-hook install skipped (no QwenPawAgent): %s", exc)
        return

    # P4 — pre_reply hook (session guard + activation rules)
    if not _INSTALLED["session_guard_hook"]:
        try:
            QwenPawAgent.register_class_hook(
                "pre_reply", "pg_session_guard_and_activation",
                _make_session_guard_hook(plugin_root),
            )
            _INSTALLED["session_guard_hook"] = True
            log.info("[P4] pre_reply class hook installed")
            print("[production-grade]   ✓ P4: session guard + activation rules", flush=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("[P4] register_class_hook failed: %s", exc)

    # P2 — post_acting hook (auto-receipt for delegate_external_agent)
    if not _INSTALLED["auto_receipt_hook"]:
        try:
            QwenPawAgent.register_class_hook(
                "post_acting", "pg_auto_receipt",
                _make_auto_receipt_hook(plugin_root),
            )
            _INSTALLED["auto_receipt_hook"] = True
            log.info("[P2] post_acting class hook installed")
            print("[production-grade]   ✓ P2: auto-receipt for delegate_external_agent", flush=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("[P2] register_class_hook failed: %s", exc)


# ─── P4 hook factory ────────────────────────────────────────────────────────


def _make_session_guard_hook(plugin_root: Path):
    """Return an async hook that handles SessionStart+UserPromptSubmit semantics."""

    async def hook(self, kwargs):  # noqa: ANN001, ARG001
        try:
            # Best-effort introspection — Msg shape varies across QwenPaw versions.
            msg = kwargs.get("msg")
            session_id = _session_id_for(self)
            user_text = _msg_to_text(msg)

            extra_lines: list[str] = []

            # SessionStart-equivalent: only on first prompt of the session.
            if session_id and session_id not in _SEEN_SESSIONS:
                _SEEN_SESSIONS.add(session_id)
                proj_msg = _maybe_project_detection_msg()
                if proj_msg:
                    extra_lines.append(proj_msg)

            # UserPromptSubmit-equivalent: every prompt.
            if user_text:
                lower = user_text.lower()
                seen = set()
                for pat, skill, hint in _ACTIVATION_RULES:
                    if pat.search(user_text):
                        if skill in seen:
                            continue
                        seen.add(skill)
                        if hint:
                            extra_lines.append(hint)

            if not extra_lines:
                return None  # no rewrite

            preamble = "\n\n[production-grade]\n" + "\n".join(f"  • {l}" for l in extra_lines)
            new_msg = _prepend_text_to_msg(msg, preamble)
            new_kwargs = dict(kwargs)
            new_kwargs["msg"] = new_msg
            return new_kwargs
        except Exception:  # noqa: BLE001
            log.warning("session_guard_hook crashed:\n%s", traceback.format_exc())
            return None

    return hook


def _maybe_project_detection_msg() -> str | None:
    suite_dir = Path.cwd() / "Claude-Production-Grade-Suite"
    if not suite_dir.is_dir():
        return None
    receipts = suite_dir / ".orchestrator" / "receipts"
    n_receipts = (
        sum(1 for _ in receipts.glob("*.json"))
        if receipts.is_dir() else 0
    )
    return (
        f"Production-Grade workspace detected at {suite_dir} "
        f"({n_receipts} prior receipt(s)). "
        f"Use /production-grade to continue the pipeline."
    )


# ─── P2 hook factory ────────────────────────────────────────────────────────


_RUNNER_NAME_RE = re.compile(r"^pgs-(?P<role>[a-z0-9_-]+?)-[a-z]$")


def _make_auto_receipt_hook(plugin_root: Path):
    """Return an async post_acting hook that writes a stub receipt
    when delegate_external_agent finishes."""

    async def hook(self, kwargs, output):  # noqa: ANN001, ARG001
        try:
            tool_call = kwargs.get("tool_call") or {}
            name = (
                getattr(tool_call, "name", None)
                or (tool_call.get("name") if isinstance(tool_call, dict) else None)
            )
            if name != "delegate_external_agent":
                return None

            tool_input = (
                getattr(tool_call, "input", None)
                or (tool_call.get("input") if isinstance(tool_call, dict) else None)
                or {}
            )
            action = tool_input.get("action")
            runner = tool_input.get("runner") or ""
            if action not in ("start", "message"):
                return None  # only record meaningful turns

            m = _RUNNER_NAME_RE.match(runner)
            if not m:
                return None
            role = m.group("role")

            project_root = _find_project_root()
            if not project_root:
                # No workspace yet — orchestrator hasn't bootstrapped it.
                return None

            receipts = project_root / "Claude-Production-Grade-Suite" / ".orchestrator" / "receipts"
            receipts.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            short = uuid4().hex[:6]
            path = receipts / f"{ts}-{role}-{short}.json"
            stub = {
                "task": f"auto-{ts}-{short}",
                "agent": role,
                "phase": "auto",
                "status": "in_progress",
                "artifacts": [],
                "metrics": {},
                "verification": "auto-stub from post_acting hook on delegate_external_agent; orchestrator should enrich",
                "delegate": {
                    "runner": runner,
                    "action": action,
                    "ts": ts,
                },
            }
            path.write_text(json.dumps(stub, indent=2), encoding="utf-8")
            log.debug("[P2] receipt stub written: %s", path)
        except Exception:  # noqa: BLE001
            log.warning("auto_receipt_hook crashed:\n%s", traceback.format_exc())
        return None

    return hook


# ─── Helpers ────────────────────────────────────────────────────────────────


def _session_id_for(agent) -> str:
    # QwenPaw agents carry the session id on a per-request context;
    # fall back to a class-default if not exposed.
    for attr in ("_request_session_id", "session_id", "_session_id"):
        if hasattr(agent, attr):
            v = getattr(agent, attr)
            if v:
                return str(v)
    ctx = getattr(agent, "_request_context", None)
    if isinstance(ctx, dict):
        return str(ctx.get("session_id") or "")
    return ""


def _msg_to_text(msg) -> str:
    if msg is None:
        return ""
    if isinstance(msg, list):
        return "\n".join(_msg_to_text(m) for m in msg)
    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for blk in content:
        if isinstance(blk, dict) and blk.get("type") == "text":
            parts.append(str(blk.get("text", "")))
        elif hasattr(blk, "text") and getattr(blk, "type", None) == "text":
            parts.append(blk.text or "")
    return "".join(parts)


def _prepend_text_to_msg(msg, preamble: str):
    """Return a Msg with `preamble` inserted at the start of its first text block."""
    if msg is None:
        return msg
    if isinstance(msg, list):
        if not msg:
            return msg
        new_first = _prepend_text_to_msg(msg[0], preamble)
        return [new_first] + list(msg[1:])
    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            new = dict(msg)
            new["content"] = preamble + "\n" + content
            return new
    if isinstance(content, list):
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "text":
                blk["text"] = preamble + "\n" + str(blk.get("text", ""))
                break
            if hasattr(blk, "text") and getattr(blk, "type", None) == "text":
                try:
                    blk.text = preamble + "\n" + (blk.text or "")
                except Exception:  # noqa: BLE001
                    pass
                break
    return msg


def _find_project_root(start: Path | None = None) -> Path | None:
    """Walk upward from start (default cwd) until a directory with
    `Claude-Production-Grade-Suite/` is found."""
    here = (start or Path.cwd()).resolve()
    for cand in (here, *here.parents):
        if (cand / "Claude-Production-Grade-Suite").is_dir():
            return cand
    return None
