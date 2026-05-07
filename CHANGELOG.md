# Changelog

All notable changes to the QwenPaw port of `production-grade`. Format follows [Keep a Changelog](https://keepachangelog.com); this project follows [Semantic Versioning](https://semver.org).

## [v0.2.0-alpha] — 2026-05-07 (UNRELEASED, on `main`)

The capability-first v0.2 release in progress. Closes the multi-agent and
parallelism gaps documented in `plans/AUDIT_v0.1.1.md`. **Untagged.**
Test on `main` first; tag `v0.2.0` once user-verified end-to-end.

### Added — multi-agent infrastructure

- **`production_grade/specialists/runner.py`** — minimal stdio ACP server.
  Each specialist runs in a fresh subprocess with its role's SKILL.md +
  the 8 shared protocols loaded as system prompt. No tool access in
  v0.2-alpha — runner produces text (plans, specs, audits, reviews);
  orchestrator implements via its own tools.
- **`production_grade/specialists/__main__.py`** — CLI entry. Run any
  specialist standalone for testing: `python -m production_grade.specialists --role polymath --smoke`.
- **`production_grade/acp_install.py`** — registers `pgs-<role>-{a,b,c}`
  runners in each workspace's `agent.json` so QwenPaw's
  `delegate_external_agent` tool can spawn them. Suffixed copies
  (3 for parallel-heavy roles, 2 for moderate, 1 for serial) work
  around QwenPaw's per-`(session, runner)` re-entrancy constraint and
  enable Wave A/B/C concurrent dispatch.
- **`production_grade/v02_dispatch_preamble.md`** — injected into the
  orchestrator's SKILL.md at install time. Tells the orchestrator how
  to dispatch via `delegate_external_agent` instead of doing all work
  itself, and lists the available runner names.

### Added — operator support

- `make runner-smoke` — load polymath runner and print system-prompt
  size; verifies bundled skills+protocols and the `acp` SDK install.
- `make runner-list` — list `pgs-*` runners registered in the default
  agent.
- `make dispatch-help` — print example `delegate_external_agent` call
  for testing in chat.
- `scripts/verify.sh` extended: checks count of `pgs-*` ACP runners
  registered per workspace; warns if no LLM API key is set in env
  (without one, runners fail at dispatch time).

### Required env vars (passed through to spawned runners)

For the runners to actually call out to an LLM, at least one of:

- `OPENAI_API_KEY` (default provider)
- `DASHSCOPE_API_KEY` (set `PG_LLM_PROVIDER=dashscope`)
- `TOGETHER_API_KEY` (set `PG_LLM_PROVIDER=together`)

Optional: `PG_LLM_MODEL`, `PG_LLM_BASE_URL`, `PG_LOG_FILE`.

Set them in the shell that runs `qwenpaw app`, or in the QwenPaw
secrets store. The plugin's startup hook reads them at install time and
embeds the values in each runner's launch config.

### Known limitations of v0.2-alpha

- Runners are text-only. If a specialist's methodology says "now run
  pytest" or "write file X", the orchestrator (you, the parent) must
  perform the action. v0.3+ will route tool calls through ACP.
- Parallelism is opportunistic — the orchestrator must explicitly fire
  multiple delegations concurrently. The skill body's preamble
  encourages this for Wave A/B/C phases but doesn't enforce it.
- LLM credential is shared across runners — a different model per
  specialist is not yet supported. v0.3+ will allow per-role overrides.

### Added — v0.2 capability hooks (P2 + P3 + P4)

`production_grade/hooks.py` ships three pieces, all installed by the
plugin's startup hook and verified end-to-end in `/tmp/pg_hook_test.py`
against the user's actual QwenPaw install:

- **P2 — auto-receipt enforcement** (`post_acting` class hook on
  `QwenPawAgent`). When the orchestrator finishes a
  `delegate_external_agent` call to a `pgs-<role>-<copy>` runner, the
  hook walks up from cwd to find a `Claude-Production-Grade-Suite/`
  workspace and writes a stub receipt JSON under
  `.orchestrator/receipts/<ts>-<role>-<short>.json` so the audit trail
  survives even if the model forgets to write one. Orchestrator can
  enrich the stub afterwards.
- **P3 — runtime `!`<cmd>`` shell preprocessing** (monkey-patch on
  `qwenpaw.app.runner.runner.AgentRunner._maybe_inject_skill`). After a
  slash-skill invocation injects the skill body into the user message,
  the wrapper scans for `!`<cmd>`` patterns and replaces each with the
  command's stdout (10s timeout, errors collapsed into HTML comments
  so the model still sees them). Restores cwd-sensitive protocol
  loading the v0.1 port had to statify.
- **P4 — `SessionStart` + `UserPromptSubmit` equivalents** (`pre_reply`
  class hook). On the first prompt of each session, if cwd contains
  `Claude-Production-Grade-Suite/`, prepend a recommendation pointing
  at `/production-grade`. On every prompt, regex-match against
  activation rules (build/audit/test/deploy patterns) and inject a
  routing hint when one fires. Conservative — six rules total, no
  matches on neutral prompts.

All three are installed via a single `install_hooks(plugin_root)` call
from `plugin._on_startup`. Re-installable; idempotent (won't
double-register class hooks or double-patch the skill loader).

### Tracking — to reach 100% (per `plans/08_full_parity_architecture.md`)

Done in this release:
- P0 — Custom ACP runners (multi-agent + parallelism)
- P1 — Orchestrator dispatch preamble
- P2 — Auto-receipt enforcement
- P3 — Runtime `!`<cmd>`` shell preprocessing
- P4 — SessionStart + UserPromptSubmit class hooks

Still deferred (UX-only, per user direction):
- Frontend tool renderers (`registerToolRender` for AskUserQuestion / gate cards).
- `registerRoutes` task dashboard sidebar.

Net retention vs Claude Code production-grade: methodology content 100%,
pipeline orchestration ~95% (no longer single-agent-walk), hook surface
~90% (every event production-grade actually uses), UI primitives still
~20% (text-only gate ceremonies). Weighted: ~85-90%.

---

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
