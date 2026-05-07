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
import sys
import traceback
from pathlib import Path

from qwenpaw.plugins.api import PluginApi

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("production-grade")


class ProductionGradePlugin:
    """Entry class — required name ``plugin`` exported at module level below."""

    def register(self, api: PluginApi) -> None:
        api.register_startup_hook(
            hook_name="pg_install_skills",
            callback=self._on_startup,
            priority=100,
        )

    def _on_startup(self) -> None:
        # Make the sibling ``production_grade/`` package importable. The plugin
        # validator loads this file as a standalone module via importlib, so
        # the parent dir isn't on sys.path by default.
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        # Loud startup banner — users see this at every `qwenpaw app` start.
        # Lets them confirm the plugin loaded, what version, and from where.
        # If the printed path doesn't match the source they're iterating in,
        # they know they need to re-run `make install` to refresh the snapshot.
        try:
            version = self._read_plugin_version()
        except Exception:  # noqa: BLE001
            version = "(unknown)"
        print(
            f"[production-grade] v{version} starting "
            f"(plugin root: {ROOT})",
            flush=True,
        )
        self._maybe_warn_stale_snapshot()

        try:
            from production_grade.installer import install_skills_to_all_workspaces

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

        # v0.2: register specialist ACP runners so the orchestrator can
        # delegate to fresh subprocesses per role (real multi-agent +
        # parallelism). Runs after skills install so SKILL.md files exist.
        try:
            from production_grade.acp_install import register_specialist_runners

            n_runners = register_specialist_runners(plugin_root=ROOT)
            print(
                f"[production-grade] specialist runners registered in {n_runners} workspace(s)",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("ACP runner install failed: %s\n%s", exc, traceback.format_exc())
            print(
                f"[production-grade] WARN ACP runner install skipped: {exc}",
                flush=True,
            )

        # v0.2: install P2 (auto-receipt) + P3 (skill-loader patch) +
        # P4 (session guard + activation rules) hooks.
        try:
            from production_grade.hooks import install_hooks

            install_hooks(plugin_root=ROOT)
        except Exception as exc:  # noqa: BLE001
            log.error("hook install failed: %s\n%s", exc, traceback.format_exc())
            print(
                f"[production-grade] WARN hook install skipped: {exc}",
                flush=True,
            )


    # ─── Diagnostics helpers ────────────────────────────────────────────────

    def _read_plugin_version(self) -> str:
        """Pull version from this plugin's plugin.json without a JSON dep."""
        import json
        meta = ROOT / "plugin.json"
        if meta.is_file():
            return json.loads(meta.read_text(encoding="utf-8")).get("version", "?")
        return "?"

    def _maybe_warn_stale_snapshot(self) -> None:
        """Detect the "I edited source but qwenpaw runs the snapshot" trap.

        When ``make install`` runs, we drop a ``.dev_source`` file pointing at
        the source repo. At startup, if any ``.py`` in source is newer than
        any in this snapshot, print a loud warning so users know to re-run
        ``make install``. End-users who installed via ``qwenpaw plugin install
        <git-url>`` won't have ``.dev_source`` and won't see this warning —
        intentional: only matters during plugin development.
        """
        marker = ROOT / ".dev_source"
        if not marker.is_file():
            return  # not a dev install
        try:
            source_path = Path(marker.read_text(encoding="utf-8").strip())
            if not source_path.is_dir():
                return
            snapshot_mtime = max(
                p.stat().st_mtime
                for p in ROOT.rglob("*.py")
                if p.is_file()
            )
            source_latest = max(
                (p.stat().st_mtime for p in source_path.rglob("*.py") if p.is_file()),
                default=0,
            )
            if source_latest > snapshot_mtime + 5:  # 5s grace for clock drift
                drift = int(source_latest - snapshot_mtime)
                print(
                    f"[production-grade] ⚠  source repo at {source_path}\n"
                    f"[production-grade]    has changes {drift}s newer than this snapshot.\n"
                    f"[production-grade]    Run `make install` (in source) to refresh.\n"
                    f"[production-grade]    Otherwise QwenPaw runs stale plugin code.",
                    flush=True,
                )
        except Exception as exc:  # noqa: BLE001 — never crash on diagnostic
            log.debug("stale-snapshot check failed: %s", exc)


# Required: a module-level `plugin` instance.
plugin = ProductionGradePlugin()
