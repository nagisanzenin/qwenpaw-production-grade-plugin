# Changelog

All notable changes to the QwenPaw port of `production-grade`. Format follows [Keep a Changelog](https://keepachangelog.com); this project follows [Semantic Versioning](https://semver.org).

## [v0.1.1] — 2026-05-07

Unbreaks the v0.1.0 release and addresses every install-flow issue surfaced during the first end-to-end user run.

### Fixed
- **Plugin install validator failure** (`No module named 'production_grade'`). Made `register()` and the startup callback synchronous and lazy-imported `production_grade.installer` inside the callback after pushing the plugin root onto `sys.path`. The validator loads `plugin.py` standalone and our top-level package import was failing during validation.
- **Skills never appeared in QwenPaw UI Skills tab.** Installer now updates each workspace's `skill.json` manifest (schema `workspace-skill-manifest.v1`) so all 14 skills register as `enabled` and `source: customized`. Without this the SKILL.md files were on disk but invisible to QwenPaw's UI.

### Added
- `Makefile` with `install / verify / port / port-clean / upstream-pull / update / uninstall / clean / help` targets.
- `scripts/verify.sh` post-install sanity check covering `qwenpaw` on PATH, plugin registration, bundled artifact counts, per-workspace install status, and skill-manifest registration.
- `TROUBLESHOOTING.md` enumerating every install/runtime failure mode hit during the v0.1.0 user run, each with a one-line fix.
- `CHANGELOG.md` (this file).

### Changed
- README rewritten action-first: 3-minute install at the top, success criteria immediately after, deferred features at the bottom.
- INSTALL.md collapsed to a single canonical bundled-install path with explicit verify/sanity-check steps; the bundled-vs-live decision moved to a "for maintainers" section.
- Design + research docs moved into `plans/` so the top-level only contains user-facing files and runnable code.
- `plugin.json.version` bumped to `0.1.1`.

### Deferred
Same as v0.1.0 — see [`plans/08_full_parity_architecture.md`](./plans/08_full_parity_architecture.md):
- Custom ACP runners (no fresh-context per specialist).
- Custom MCP server (`pg__dispatch_specialist`, `pg__ask_user_question`, etc.).
- Frontend tool renderers.
- SessionStart project detection.
- UserPromptSubmit activation rules.

## [v0.1.0] — 2026-05-07

Initial bundled release. **Known broken:** install fails with `No module named 'production_grade'` due to async/sync mismatch in `plugin.py`. Use v0.1.1 instead.

### Added
- `plugin.json` + `plugin.py` backend entry registering a startup hook.
- `production_grade/installer.py` that ports skills + protocols into each QwenPaw agent workspace.
- `production_grade/port_logic.py` adaptation rules: frontmatter strip, tool-name translation (`Read`→`read_file`, `WebSearch`→`tavily_search`, …), `` !`<cmd>` `` → explicit `read_file` instructions, v0.1 footer.
- `production_grade/port_from_upstream.py` CLI to (re)populate this repo's `skills/` and `protocols/` from a local upstream copy of `nagisanzenin/claude-code-production-grade-plugin` (MIT).
- Bundled `skills/` (14 SKILL.md files) and `protocols/` (8 protocol files).
- `pyproject.toml`, `LICENSE` (MIT), `.gitignore`.
- Plan docs: `05_compatibility_matrix.md`, `06_migration_plan.md`, `07_gotchas_and_risks.md`, `08_full_parity_architecture.md`, `PHASE_0_RUNBOOK.md`.
- Research notes: `research_notes/01..07`.

[v0.1.1]: https://github.com/nagisanzenin/qwenpaw-production-grade-plugin/releases/tag/v0.1.1
[v0.1.0]: https://github.com/nagisanzenin/qwenpaw-production-grade-plugin/releases/tag/v0.1.0
