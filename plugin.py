"""QwenPaw plugin entry — Production-Grade port (v0.1).

Backend hook: on app startup, copies skills/* and protocols/* into every
QwenPaw agent workspace under ``~/.qwenpaw/workspaces/<id>/skills/`` and
``~/.qwenpaw/workspaces/<id>/production-grade-protocols/``.

v0.1 is intentionally minimal:
- No custom ACP runners (single-agent walk through the pipeline).
- No custom MCP server.
- No frontend tool renderers.
- No monkey-patches.

See ``08_full_parity_architecture.md`` in this repo for the v1.0+ plan.
"""
from __future__ import annotations

import logging
import traceback
from pathlib import Path

from qwenpaw.plugins.api import PluginApi

from production_grade.installer import install_skills_to_all_workspaces

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("production-grade")


class ProductionGradePlugin:
    """Entry class — required name ``plugin`` exported at module level below."""

    async def register(self, api: PluginApi) -> None:
        api.register_startup_hook(
            "pg_install_skills",
            self._on_startup,
            priority=100,
        )

    async def _on_startup(self) -> None:
        try:
            n = install_skills_to_all_workspaces(plugin_root=ROOT)
            print(
                f"[production-grade] installed into {n} workspace(s)",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 — never crash QwenPaw on plugin startup
            log.error("install failed: %s\n%s", exc, traceback.format_exc())
            print(
                f"[production-grade] WARN install skipped: {exc}",
                flush=True,
            )


# Required: a module-level `plugin` instance.
plugin = ProductionGradePlugin()
