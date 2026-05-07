# qwenpaw-production-grade-plugin

Research and migration plan for porting the Claude Code [`production-grade`](https://github.com/nagisanzenin/claude-code-production-grade-plugin) plugin (v5.4.0) to **QwenPaw** (https://github.com/agentscope-ai/QwenPaw) at **100% functional retention** — without modifying QwenPaw source.

---

## Read in this order

### 🎯 The flagship plan

1. **[`08_full_parity_architecture.md`](./08_full_parity_architecture.md)** — the **100% functional-retention** plan. Six-tier architecture (backend plugin + ACP runners + MCP server + frontend plugin + workspace state + pre-rendered skills). 18-28 days to v1.0.

### Earlier alternatives (kept for context)

2. [`05_compatibility_matrix.md`](./05_compatibility_matrix.md) — surface-by-surface assessment (the original ~85% scoping).
3. [`06_migration_plan.md`](./06_migration_plan.md) — phased plan for the 85% port (2-3 weeks).
4. [`07_gotchas_and_risks.md`](./07_gotchas_and_risks.md) — blockers, risks, doc surprises (still applicable to either plan).

### Foundational research

5. [`research_notes/01_production_grade_map.md`](./research_notes/01_production_grade_map.md) — exhaustive Claude Code plugin inventory (1360 lines).
6. [`research_notes/02_qwenpaw_map.md`](./research_notes/02_qwenpaw_map.md) — QwenPaw architecture (from source).
7. [`research_notes/03_qwenpaw_official_docs.md`](./research_notes/03_qwenpaw_official_docs.md) — QwenPaw docs audit.
8. [`research_notes/04_claude_code_official_docs.md`](./research_notes/04_claude_code_official_docs.md) — Claude Code docs reference card.
9. [`research_notes/05_frontend_extension_audit.md`](./research_notes/05_frontend_extension_audit.md) — verifies AskUserQuestion / Gates / Dashboards are feasible.
10. [`research_notes/06_acp_and_mission_audit.md`](./research_notes/06_acp_and_mission_audit.md) — verifies custom ACP runners replicate subagent semantics.
11. [`research_notes/07_hooks_and_loader_audit.md`](./research_notes/07_hooks_and_loader_audit.md) — verifies AgentScope hooks reach + skill loader patching.

---

## Headline findings

- **100% functional retention is feasible** without modifying QwenPaw source.
- **Three load-bearing extension points are confirmed:**
  - `registerToolRender` + `registerRoutes` (frontend) cover all UI primitives.
  - Custom ACP runners + `delegate_external_agent` cover subagent fresh-context and parallelism.
  - `register_class_hook` on `QwenPawAgent` (TIER-4 AgentScope) covers all hook events production-grade uses.
- **One TIER-3 monkey-patch needed** for `` !`<cmd>` `` skill-body preprocessing — covered by `_maybe_inject_skill` patch + `post_acting` class hook.
- **Reliability matches Claude Code's version** when:
  - QwenPaw minor version is pinned (`~1.1.5`).
  - Plugin startup runs a smoke test on the TIER-3 patch targets.
  - Hook bodies wrap in try/except (matches `BootstrapHook` pattern).
- **Effort:** ~3-4 weeks elapsed for v1.0 (vs. 2-3 weeks for the simpler 85% port).
- **Distribution:** GitHub repo + `qwenpaw plugin install <git-url>`. No marketplace integration in v1.0.

## Six-tier architecture (overview)

```
TIER 6  Pre-rendered skills (optional fallback)
TIER 5  Workspace state (Claude-Production-Grade-Suite/)
TIER 4  Frontend plugin (entry.frontend → dist/index.js)
        registerToolRender for AskUserQuestion / Gates / Tasks
        registerRoutes for sidebar dashboard
TIER 3  Custom MCP server (pg-orchestrator-mcp, stdio)
        pg__dispatch_specialist, pg__ask_user_question,
        pg__gate_ceremony, pg__task_*, pg__receipt_*
TIER 2  Custom ACP runners (one per specialist × N copies)
        14 roles × 3-4 copies = ~42-56 runner configs
        Each = stdio Python ACP server with one SKILL.md
TIER 1  Backend Python plugin (entry.backend → plugin.py)
        register_startup_hook → install ACP runners, MCP, hooks
        register_class_hook on QwenPawAgent
        Monkey-patch _maybe_inject_skill (skill preprocessing)
        register_control_command for slash commands
```

## Source repos under analysis

- `production-grade` (Claude Code plugin) — `~/Documents/Github/claude-code-production-grade-plugin/` (v5.4.0, commit `64795da`).
- `QwenPaw` (AgentScope) — `~/Documents/Github/QwenPaw/` (v1.1.6b1).

License of this research repo: TBD (the source plugin is MIT; QwenPaw is Apache-2.0).
