# qwenpaw-production-grade-plugin

Research and migration plan for porting the Claude Code [`production-grade`](https://github.com/nagisanzenin/claude-code-production-grade-plugin) plugin (v5.4.0) to **QwenPaw** (https://github.com/agentscope-ai/QwenPaw).

This repo currently contains the **research and migration plan** — not yet the runnable plugin. A v1.0 implementation following `06_migration_plan.md` is the next milestone.

---

## Read in this order

1. [`05_compatibility_matrix.md`](./05_compatibility_matrix.md) — what ports cleanly, what doesn't, surface by surface.
2. [`06_migration_plan.md`](./06_migration_plan.md) — phased plan with concrete steps, file layout, code sketches, exit gates.
3. [`07_gotchas_and_risks.md`](./07_gotchas_and_risks.md) — hard blockers, soft blockers, risks, doc surprises.

For deep background:

- [`research_notes/01_production_grade_map.md`](./research_notes/01_production_grade_map.md) — exhaustive inventory of the Claude Code plugin (1360 lines).
- [`research_notes/02_qwenpaw_map.md`](./research_notes/02_qwenpaw_map.md) — QwenPaw architecture (from source).
- [`research_notes/03_qwenpaw_official_docs.md`](./research_notes/03_qwenpaw_official_docs.md) — QwenPaw docs audit (what's documented vs. source-only).
- [`research_notes/04_claude_code_official_docs.md`](./research_notes/04_claude_code_official_docs.md) — Claude Code docs reference card.

---

## Headline findings

- **About 80% of production-grade ports cleanly.** Skills, protocols, the `Claude-Production-Grade-Suite/` workspace, and most tool primitives map directly. Skill format (`SKILL.md` + YAML frontmatter) is shared.
- **About 20% requires rework.** Specifically: the `Skill`-tool-driven orchestration, `AskUserQuestion` gate ceremonies, and the `SessionStart`/`UserPromptSubmit` hooks.
- **The single biggest gap is the hook surface.** QwenPaw plugins only expose `register_startup_hook` / `register_shutdown_hook`. Per-prompt hooks require monkey-patching `AgentRunner.query_handler` (officially documented escape hatch). Per-tool hooks require reaching into AgentScope (upstream, less stable).
- **Recommended v1 architecture:** single-agent walk through the pipeline (Option A in `06_migration_plan.md`). Multi-agent (one QwenPaw agent per specialist) is a v2 idea.
- **Required setup:** QwenPaw `>=1.1.5,<1.2`, `TAVILY_API_KEY` for Freshness Protocol, plus the standard `~/.qwenpaw/` workspace.
- **QwenPaw built-in `/mission` mode may overlap.** Phase-0.4 spike in the plan investigates whether to reuse it.

---

## Source repos under analysis

- `production-grade` (Claude Code plugin) — `~/Documents/Github/claude-code-production-grade-plugin/` (cloned at `64795da`).
- `QwenPaw` (AgentScope) — `~/Documents/Github/QwenPaw/` (cloned at first push).

License of this research repo: TBD (the source plugin is MIT; QwenPaw is Apache-2.0).
