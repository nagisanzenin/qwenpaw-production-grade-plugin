# qwenpaw-production-grade-plugin

QwenPaw port of the Claude Code [`production-grade`](https://github.com/nagisanzenin/claude-code-production-grade-plugin) plugin (v5.4.0 upstream). 14 specialist skills + 8 shared protocols for end-to-end production-ready software delivery.

**Status: v0.1 — installable.** The single-agent walk subset of the full plan. Drop-in install for QwenPaw `>=1.1.5`.

---

## Quick install

```bash
# 1. clone this repo
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin

# 2. make sure your upstream copy is around
git clone https://github.com/nagisanzenin/claude-code-production-grade-plugin \
  ~/Documents/Github/claude-code-production-grade-plugin

# 3. install into QwenPaw
qwenpaw plugin install . --force
qwenpaw plugin list   # expect: production-grade

# 4. restart QwenPaw and verify skills loaded
# (Ctrl-C qwenpaw app, then run `qwenpaw app` again)
qwenpaw skills list
```

Then in chat:

```
/production-grade  add a CRUD endpoint for a "tasks" resource
```

Detailed install + troubleshooting → [`INSTALL.md`](./INSTALL.md).

---

## Read in this order

### Plugin (v0.1)

- [`INSTALL.md`](./INSTALL.md) — install steps, verification, troubleshooting.
- [`plugin.json`](./plugin.json) — QwenPaw plugin manifest.
- [`plugin.py`](./plugin.py) — backend entry; registers a startup hook.
- [`production_grade/installer.py`](./production_grade/installer.py) — finds upstream, walks workspaces, ports skills + protocols.
- [`production_grade/port_logic.py`](./production_grade/port_logic.py) — adaptation rules (frontmatter strip, tool-name translation, `` !`<cmd>` `` handling).

### Plans

- [`08_full_parity_architecture.md`](./08_full_parity_architecture.md) — the **100% functional-retention** plan. Six-tier architecture (backend plugin + ACP runners + MCP server + frontend plugin + workspace state + pre-rendered skills). 18-28 days to v1.0.
- [`05_compatibility_matrix.md`](./05_compatibility_matrix.md) — original surface-by-surface scoping (~85% target).
- [`06_migration_plan.md`](./06_migration_plan.md) — phased plan for the 85% port.
- [`07_gotchas_and_risks.md`](./07_gotchas_and_risks.md) — blockers, risks, doc surprises.
- [`PHASE_0_RUNBOOK.md`](./PHASE_0_RUNBOOK.md) — five spikes that verify each architecture tier in isolation. Useful before tackling v0.2+.

### Foundational research

- [`research_notes/01_production_grade_map.md`](./research_notes/01_production_grade_map.md) — exhaustive Claude Code plugin inventory.
- [`research_notes/02_qwenpaw_map.md`](./research_notes/02_qwenpaw_map.md) — QwenPaw architecture (from source).
- [`research_notes/03_qwenpaw_official_docs.md`](./research_notes/03_qwenpaw_official_docs.md) — QwenPaw docs audit.
- [`research_notes/04_claude_code_official_docs.md`](./research_notes/04_claude_code_official_docs.md) — Claude Code docs reference card.
- [`research_notes/05_frontend_extension_audit.md`](./research_notes/05_frontend_extension_audit.md) — verifies AskUserQuestion / Gates / Dashboards are feasible.
- [`research_notes/06_acp_and_mission_audit.md`](./research_notes/06_acp_and_mission_audit.md) — verifies custom ACP runners replicate subagent semantics.
- [`research_notes/07_hooks_and_loader_audit.md`](./research_notes/07_hooks_and_loader_audit.md) — verifies AgentScope hooks reach + skill loader patching.

---

## v0.1 design notes

**This plugin does not bundle skill bodies.** The plugin reads from your local copy of the upstream Claude Code plugin (MIT licensed) at install time, applies the QwenPaw adaptation, and writes the adapted skills into your QwenPaw agent workspace at `~/.qwenpaw/workspaces/<agent_id>/skills/`. Your upstream is the source of truth; this plugin is the port tool.

This pattern means:

- **Updates to the upstream propagate** with one re-install: `git pull` in your upstream, `qwenpaw plugin install . --force`, restart QwenPaw.
- **Local edits to the upstream are honored** — the port reads whatever is in your `claude-code-production-grade-plugin/skills/` dir.
- **Your QwenPaw workspace is the artifact** — if you blow it away, re-install regenerates it.

### What works in v0.1

- All 14 specialist skills installed and routable via `/<skill_name>`.
- 8 shared protocols installed at `~/.qwenpaw/workspaces/<id>/production-grade-protocols/`.
- Tool-name translation (`Read` → `read_file`, `WebSearch` → `tavily_search`, etc.) — see `production_grade/port_logic.py:_TOOL_TRANSLATIONS`.
- Inline `` !`<cmd>` `` shell preprocessing replaced with explicit `read_file` instructions pointing at the workspace protocols dir.
- `Claude-Production-Grade-Suite/` workspace bootstrap done by the orchestrator skill body itself when a build kicks off (file ops, runtime-agnostic).

### What's deferred to v0.2+

See `08_full_parity_architecture.md` for the full plan. v0.1 omits:

- Custom ACP runners (specialists run in the orchestrator's context — no fresh context per role; long pipelines may drift).
- Custom MCP server (`pg__dispatch_specialist`, `pg__ask_user_question`, etc.).
- Frontend tool renderers (gates show as plain-text option lists).
- SessionStart project detection (the orchestrator skill body can detect `Claude-Production-Grade-Suite/` itself).
- UserPromptSubmit activation rules (you have to type `/production-grade` explicitly).

These add up to the difference between **~85% retention (v0.1)** and **100% retention (v1.0)**.

---

## License

MIT — see [`LICENSE`](./LICENSE).

This plugin ports the upstream `nagisanzenin/claude-code-production-grade-plugin` (also MIT). At install time, the port reads upstream content from your local clone and adapts it for QwenPaw; the plugin itself does not bundle upstream files.

QwenPaw is Apache-2.0; this plugin only uses its public extension points (no QwenPaw source modifications).
