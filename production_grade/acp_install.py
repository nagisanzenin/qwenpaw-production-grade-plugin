"""Register production-grade specialist ACP runners in QwenPaw agent configs.

Writes ``ACPAgentConfig`` entries into ``<workspace>/agent.json`` under
``acp.agents`` so the parent QwenPaw agent can call::

    delegate_external_agent(action="start", runner="pgs-<role>-<copy>", ...)

and QwenPaw spawns ``python -m production_grade.specialists --role <role>``
as a fresh subprocess for that specialist.

Multiple suffixed copies per role are registered (``-a``, ``-b``, ``-c``)
to work around QwenPaw's per-(session,runner) re-entrancy constraint —
this enables real Wave A/B/C parallelism for roles where production-grade
calls multiple instances concurrently.

LLM provider config is read from ``PG_LLM_*`` env vars in the plugin
process at install time and passed through to each runner subprocess.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("production-grade.acp_install")

# Number of suffixed copies per role. Heavy parallel roles get more copies;
# serial roles get just one.
COPIES_PER_ROLE: dict[str, int] = {
    "polymath":           1,
    "product-manager":    1,
    "solution-architect": 1,
    "software-engineer":  3,
    "frontend-engineer":  3,
    "qa-engineer":        3,
    "security-engineer":  2,
    "code-reviewer":      2,
    "devops":             2,
    "sre":                1,
    "technical-writer":   1,
    "data-scientist":     1,
    "skill-maker":        1,
    # NOTE: production-grade itself is the orchestrator — it runs in the
    # parent QwenPaw context, not as a specialist runner.
}

RUNNER_PREFIX = "pgs"  # production-grade specialist


# ─── Public API ─────────────────────────────────────────────────────────────


def register_specialist_runners(plugin_root: Path) -> int:
    """Register one ACP runner per (role, copy) into every QwenPaw workspace.

    Returns the number of workspaces updated. Idempotent — re-running
    overwrites existing pgs-* entries with current config but leaves
    user-added runners alone.
    """
    try:
        from qwenpaw.config.config import (  # type: ignore[import]
            load_agent_config, save_agent_config, ACPAgentConfig, ACPConfig,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("qwenpaw config module not importable: %s — skipping runner install", exc)
        return 0

    ws_root = _workspaces_root()
    if not ws_root.is_dir():
        log.info("no workspaces at %s; skipping ACP runner install", ws_root)
        return 0

    base_env = _runner_env(plugin_root)
    cmd = sys.executable
    common_args = ["-m", "production_grade.specialists"]

    written = 0
    for ws in sorted(ws_root.iterdir()):
        if not ws.is_dir():
            continue
        agent_id = ws.name
        try:
            cfg = load_agent_config(agent_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("load_agent_config(%s) failed: %s", agent_id, exc)
            continue
        cfg.acp = cfg.acp or ACPConfig()
        existing = getattr(cfg.acp, "agents", None) or {}
        # Some QwenPaw versions store .agents as a dict on the model.
        if not hasattr(cfg.acp, "agents"):
            log.warning("ACPConfig has no .agents attr on agent_id=%s — skipping", agent_id)
            continue

        n_role_copies = 0
        for role, n_copies in COPIES_PER_ROLE.items():
            for i in range(n_copies):
                suffix = chr(ord("a") + i)
                key = f"{RUNNER_PREFIX}-{role}-{suffix}"
                runner_args = list(common_args) + [
                    "--role", role,
                    "--copy", suffix,
                    "--plugin-root", str(plugin_root),
                ]
                cfg.acp.agents[key] = ACPAgentConfig(
                    enabled=True,
                    command=cmd,
                    args=runner_args,
                    env={**base_env},
                    trusted=True,
                    tool_parse_mode="update_detail",
                    stdio_buffer_limit_bytes=50 * 1024 * 1024,
                )
                n_role_copies += 1

        try:
            save_agent_config(agent_id, cfg)
        except Exception as exc:  # noqa: BLE001
            log.warning("save_agent_config(%s) failed: %s", agent_id, exc)
            continue
        log.info("workspace %s: registered %d specialist runners", agent_id, n_role_copies)
        print(
            f"[production-grade]   ✓ {agent_id}: registered {n_role_copies} ACP runners",
            flush=True,
        )
        written += 1

    return written


# ─── Helpers ────────────────────────────────────────────────────────────────


def _runner_env(plugin_root: Path) -> dict[str, str]:
    """Env vars passed to every spawned runner subprocess.

    We pass through PG_LLM_* (provider config) and the LLM API keys.
    Skipped: workspace-specific values that should come from the parent.
    """
    pass_through = (
        "PG_LLM_PROVIDER",
        "PG_LLM_MODEL",
        "PG_LLM_BASE_URL",
        "PG_LOG_FILE",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_BASE_URL",
        "TOGETHER_API_KEY",
        "ANTHROPIC_API_KEY",
        "TAVILY_API_KEY",
    )
    env: dict[str, str] = {"PG_ROOT": str(plugin_root)}
    for name in pass_through:
        v = os.environ.get(name)
        if v:
            env[name] = v
    return env


def _workspaces_root() -> Path:
    try:
        from qwenpaw.constant import WORKING_DIR  # type: ignore[import]

        return Path(WORKING_DIR).expanduser() / "workspaces"
    except Exception:  # noqa: BLE001
        return Path.home() / ".qwenpaw" / "workspaces"
