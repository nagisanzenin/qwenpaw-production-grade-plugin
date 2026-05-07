"""SpecialistACPAgent — minimal stdio ACP server for one role.

For each invocation by ``delegate_external_agent``, QwenPaw spawns this as a
fresh subprocess. The subprocess loads ``skills/<role>/SKILL.md`` and the 8
shared protocols, builds a single system prompt, then streams LLM output
back through the ACP wire protocol.

v0.2-alpha is intentionally text-only: the runner produces plans, analyses,
specs, audits, etc. as text. Tools (read_file/write_file/execute_shell) stay
on the orchestrator side. v0.3+ will add ACP tool-call routing so specialists
can request tool execution from the parent.

LLM provider is selected via environment variables, populated by the parent
QwenPaw process when it spawns the runner:

- ``PG_LLM_PROVIDER``  ``openai`` (default) | ``dashscope``
- ``PG_LLM_MODEL``     model id (default: gpt-4o-mini for openai,
                       qwen-max-latest for dashscope)
- ``PG_LLM_BASE_URL``  optional override for OpenAI-compatible endpoints
- ``OPENAI_API_KEY`` / ``DASHSCOPE_API_KEY``  the credential
- ``PG_LOG_FILE``      optional log path for runner-side diagnostics
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
import uuid
from pathlib import Path
from typing import AsyncIterator

# ACP SDK is shipped by QwenPaw as `agent-client-protocol>=0.9.0`.
try:
    from acp import Agent
    from acp import (
        AgentCapabilities,
        NewSessionResponse,
        PromptResponse,
    )
    from acp.runtime import run_agent
    from acp.updates import update_agent_message, text_block
except Exception as exc:  # noqa: BLE001
    sys.stderr.write(
        f"[pg-runner] failed to import acp SDK: {exc}\n"
        "Install with: pip install agent-client-protocol\n"
    )
    raise


PROTOCOL_FILES = (
    "ux-protocol.md",
    "input-validation.md",
    "tool-efficiency.md",
    "visual-identity.md",
    "freshness-protocol.md",
    "receipt-protocol.md",
    "boundary-safety.md",
    "conflict-resolution.md",
)


def _setup_logging() -> logging.Logger:
    log = logging.getLogger("pg-runner")
    log.setLevel(logging.DEBUG)
    log_file = os.environ.get("PG_LOG_FILE")
    if log_file:
        h: logging.Handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    log.addHandler(h)
    log.propagate = False
    return log


# ─── Specialist agent ───────────────────────────────────────────────────────


class SpecialistACPAgent(Agent):  # type: ignore[misc]
    """ACP Agent that wraps one role's SKILL.md as system prompt."""

    def __init__(self, *, role: str, copy: str, plugin_root: Path) -> None:
        super().__init__()
        self.role = role
        self.copy = copy
        self.plugin_root = plugin_root
        self.log = _setup_logging()
        self.system_prompt = self._build_system_prompt()
        self.log.info(
            "specialist=%s copy=%s plugin_root=%s system_prompt_chars=%d",
            role, copy, plugin_root, len(self.system_prompt),
        )

    # -- ACP lifecycle -------------------------------------------------------

    async def initialize(self, params):  # type: ignore[no-untyped-def]
        return AgentCapabilities(
            load_session=False,
            session_capabilities={"prompts": True, "tools": False},
        )

    async def new_session(self, params):  # type: ignore[no-untyped-def]
        sid = str(uuid.uuid4())
        self.log.info("new_session session_id=%s", sid)
        return NewSessionResponse(session_id=sid, config_options=[])

    async def prompt(self, params):  # type: ignore[no-untyped-def]
        user_text = self._extract_user_text(getattr(params, "prompt", None))
        self.log.info(
            "prompt session=%s len=%d preview=%r",
            getattr(params, "session_id", "?"), len(user_text), user_text[:120],
        )
        try:
            async for delta in self._stream_llm(user_text):
                if not delta:
                    continue
                await self._conn.session_update(  # type: ignore[attr-defined]
                    session_id=params.session_id,
                    update=update_agent_message(text_block(delta)),
                )
            return PromptResponse(stop_reason="end_turn")
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            self.log.error("prompt failed: %s\n%s", exc, tb)
            err = (
                f"[pg-runner role={self.role}] LLM call failed: {type(exc).__name__}: {exc}\n"
                "Check OPENAI_API_KEY / PG_LLM_PROVIDER / PG_LLM_MODEL.\n"
            )
            try:
                await self._conn.session_update(  # type: ignore[attr-defined]
                    session_id=params.session_id,
                    update=update_agent_message(text_block(err)),
                )
            except Exception:  # noqa: BLE001
                pass
            return PromptResponse(stop_reason="error")

    # -- Helpers -------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        skill_md = (self.plugin_root / "skills" / self.role / "SKILL.md").read_text(encoding="utf-8")
        protocols_dir = self.plugin_root / "protocols"
        protocol_chunks: list[str] = []
        for fname in PROTOCOL_FILES:
            p = protocols_dir / fname
            if p.is_file():
                protocol_chunks.append(f"## {fname}\n\n{p.read_text(encoding='utf-8')}")
        protocols_block = "\n\n".join(protocol_chunks) if protocol_chunks else "(no protocols loaded)"
        return (
            "# Production-Grade Specialist (ACP runner)\n\n"
            f"You are running as the **{self.role}** specialist in a fresh subprocess.\n"
            "You receive ONE prompt from the orchestrator describing the work for this turn.\n"
            "Produce a focused response that fulfills the role's methodology — analyses, plans,\n"
            "specs, reviews, audits, threat models, etc. — as plain text.\n\n"
            "v0.2-alpha note: you do NOT have tool access. If your methodology says to "
            "execute or write files, describe what to execute/write in clear terms; the "
            "orchestrator (parent) will perform the action and may dispatch back to you.\n\n"
            "## Shared Protocols\n\n"
            f"{protocols_block}\n\n"
            f"## Role Definition: {self.role}\n\n"
            f"{skill_md}\n"
        )

    @staticmethod
    def _extract_user_text(prompt) -> str:
        if not prompt:
            return ""
        # ACP prompt content is typically a list of typed content blocks.
        if isinstance(prompt, str):
            return prompt
        out_parts: list[str] = []
        for blk in prompt:
            t = getattr(blk, "text", None)
            if t is not None:
                out_parts.append(t)
                continue
            if isinstance(blk, dict):
                if "text" in blk:
                    out_parts.append(str(blk["text"]))
        return "".join(out_parts)

    async def _stream_llm(self, user_text: str) -> AsyncIterator[str]:
        provider = os.environ.get("PG_LLM_PROVIDER", "openai").lower()
        model = os.environ.get("PG_LLM_MODEL", _default_model(provider))
        base_url = os.environ.get("PG_LLM_BASE_URL") or _default_base_url(provider)
        api_key = _resolve_api_key(provider)

        try:
            from openai import AsyncOpenAI
        except Exception as exc:  # noqa: BLE001
            yield f"[pg-runner] missing openai SDK; pip install openai. ({exc})"
            return

        client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url \
            else AsyncOpenAI(api_key=api_key)

        self.log.info("llm provider=%s model=%s base_url=%s", provider, model, base_url or "(default)")
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_text or "(empty prompt)"},
            ],
            stream=True,
        )
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
            except Exception:  # noqa: BLE001
                delta = None
            if delta:
                yield delta


# ─── Provider helpers ───────────────────────────────────────────────────────


def _default_model(provider: str) -> str:
    return {
        "openai": "gpt-4o-mini",
        "dashscope": "qwen-max-latest",
        "together": "Qwen/Qwen2.5-72B-Instruct-Turbo",
    }.get(provider, "gpt-4o-mini")


def _default_base_url(provider: str) -> str | None:
    return {
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "together": "https://api.together.xyz/v1",
    }.get(provider)


def _resolve_api_key(provider: str) -> str:
    keys = {
        "openai": ("OPENAI_API_KEY",),
        "dashscope": ("DASHSCOPE_API_KEY", "OPENAI_API_KEY"),
        "together": ("TOGETHER_API_KEY", "OPENAI_API_KEY"),
    }.get(provider, ("OPENAI_API_KEY",))
    for name in keys:
        v = os.environ.get(name)
        if v:
            return v
    raise RuntimeError(
        f"No API key for provider={provider!r}. Set one of: {', '.join(keys)}"
    )


# ─── Entry helper used by __main__ ─────────────────────────────────────────


async def run_specialist(*, role: str, copy: str, plugin_root: Path) -> None:
    agent = SpecialistACPAgent(role=role, copy=copy, plugin_root=plugin_root)
    await run_agent(agent, use_unstable_protocol=True)
