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

    Each runner's env is resolved per-workspace from QwenPaw's active model:
    the provider's decrypted ``api_key`` becomes ``OPENAI_API_KEY``, the
    ``base_url`` becomes ``OPENAI_BASE_URL``, and the model id becomes
    ``PG_LLM_MODEL``. Falls back to shell env vars if the QwenPaw provider
    cannot be resolved.
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
        if not hasattr(cfg.acp, "agents"):
            log.warning("ACPConfig has no .agents attr on agent_id=%s — skipping", agent_id)
            continue

        # Per-workspace runner env (decrypted API key, base_url, model).
        ws_env = _runner_env(plugin_root, agent_id=agent_id, agent_cfg=cfg)

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
                    env={**ws_env},
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

        masked = ", ".join(f"{k}=***" if "KEY" in k else f"{k}={v}"
                           for k, v in ws_env.items() if k.startswith(("OPENAI_", "PG_LLM_")))
        log.info("workspace %s: registered %d specialist runners; env: %s",
                 agent_id, n_role_copies, masked)
        print(
            f"[production-grade]   ✓ {agent_id}: registered {n_role_copies} ACP runners",
            flush=True,
        )
        if masked:
            print(f"[production-grade]     env passthrough: {masked}", flush=True)
        written += 1

    return written


# ─── Helpers ────────────────────────────────────────────────────────────────


def _runner_env(plugin_root: Path, *, agent_id: str, agent_cfg) -> dict[str, str]:
    """Build the env dict passed to each spawned runner subprocess.

    Order of precedence (later overrides earlier):
    1. Resolve the agent's active model → provider config; decrypt
       ``api_key`` via QwenPaw's secret_store; populate
       ``OPENAI_API_KEY`` / ``OPENAI_BASE_URL`` / ``PG_LLM_MODEL``.
    2. Pass-through any matching shell env vars only when the provider
       config didn't already supply them — useful for ``TAVILY_API_KEY``
       or for users who do prefer to set keys in their shell.
    """
    env: dict[str, str] = {"PG_ROOT": str(plugin_root)}

    # 1. Resolve from active provider via QwenPaw's secret store.
    try:
        active = getattr(agent_cfg, "active_model", None)
        provider_id = _attr_or_key(active, "provider_id")
        model = _attr_or_key(active, "model")
        if provider_id:
            provider_cfg = _read_provider_config(provider_id)
            if provider_cfg:
                api_key = _decrypt_if_encrypted(provider_cfg.get("api_key", ""))
                base_url = provider_cfg.get("base_url", "")
                if api_key:
                    env["OPENAI_API_KEY"] = api_key
                if base_url:
                    # Strip trailing /chat/completions if present — the
                    # OpenAI SDK appends it itself when building the URL.
                    env["OPENAI_BASE_URL"] = base_url.rstrip("/").removesuffix("/chat/completions")
                if model:
                    env["PG_LLM_MODEL"] = model
                env.setdefault("PG_LLM_PROVIDER", "openai")
                log.info("workspace %s: resolved provider=%s model=%s base_url=%s",
                         agent_id, provider_id, model, base_url or "(default)")
            else:
                log.warning("workspace %s: provider_id=%s has no config file under "
                            "~/.qwenpaw.secret/providers/", agent_id, provider_id)
        else:
            log.warning("workspace %s: no active_model configured", agent_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("workspace %s: provider resolution failed: %s", agent_id, exc)

    # 2. Shell fallback — only fills in what (1) didn't set.
    pass_through = (
        "PG_LLM_PROVIDER", "PG_LLM_MODEL", "PG_LLM_BASE_URL", "PG_LOG_FILE",
        "OPENAI_API_KEY", "OPENAI_BASE_URL",
        "DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL",
        "TOGETHER_API_KEY", "ANTHROPIC_API_KEY",
        "TAVILY_API_KEY",
    )
    for name in pass_through:
        v = os.environ.get(name)
        if v:
            env.setdefault(name, v)

    return env


def _attr_or_key(obj, name: str):
    if obj is None:
        return None
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name)
    return None


def _read_provider_config(provider_id: str) -> dict | None:
    """Read ``~/.qwenpaw.secret/providers/<layer>/<id>.json``.

    Layers checked in order: custom (user) → plugin → builtin.
    """
    import json
    secret_root = Path.home() / ".qwenpaw.secret" / "providers"
    for layer in ("custom", "plugin", "builtin"):
        f = secret_root / layer / f"{provider_id}.json"
        if f.is_file():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                log.warning("provider config %s unreadable: %s", f, exc)
    return None


def _decrypt_if_encrypted(value: str) -> str:
    if not value:
        return ""
    if not str(value).startswith("ENC:"):
        return str(value)
    try:
        from qwenpaw.security.secret_store import decrypt  # type: ignore[import]

        return decrypt(value)
    except Exception as exc:  # noqa: BLE001
        log.warning("decrypt failed (api_key will be empty): %s", exc)
        return ""


def _workspaces_root() -> Path:
    try:
        from qwenpaw.constant import WORKING_DIR  # type: ignore[import]

        return Path(WORKING_DIR).expanduser() / "workspaces"
    except Exception:  # noqa: BLE001
        return Path.home() / ".qwenpaw" / "workspaces"
