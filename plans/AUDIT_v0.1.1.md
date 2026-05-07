# v0.1.1 Functional-Parity Audit

> Honest comparison of what v0.1.1 ships vs. the Claude Code production-grade reference. Companion to [`08_full_parity_architecture.md`](./08_full_parity_architecture.md), which describes the path to 100%.

## Verdict

**~60-65% functional retention.** v0.1.1 is the "single-agent walk" subset:

- ✅ **Methodology content (~50% of total value):** 100% — all 14 specialist SKILL.md bodies + 8 shared protocols are bundled, adapted, and registered with QwenPaw.
- ⚠️ **Pipeline orchestration (~25%):** ~30% — the methodology runs sequentially in one agent's context. No fresh-context-per-specialist, no real Skill-tool dispatch.
- ⚠️ **UI/UX primitives (~15%):** ~20% — gates render as plain-text option lists, `AskUserQuestion` is a free-text fallback, no structured task tracking.
- ❌ **Multi-agent parallelism (~10%):** 0% — single agent, single thread, single context.

The user-facing experience: **the methodology produces real artifacts** (BRD, ADRs, code, tests, security audit, runbook, receipts) and the agent follows the protocols. It just does so in one long single-agent run instead of dispatching to 14 fresh subagents in parallel waves. Long pipelines (Full Build mode) drift; short pipelines (Feature, Review, Architect) work well.

---

## Surface-by-surface table

Stability tags: ✅ at parity • ⚠️ degraded but functional • ❌ not implemented

### Methodology content (100%)

| Feature | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| 14 specialist SKILL.md bodies | ✅ | ✅ ported via `port_logic.adapt_skill` | ✅ |
| 8 shared protocols (UX, validation, tool-efficiency, visual-identity, freshness, receipt, boundary-safety, conflict-resolution) | ✅ | ✅ bundled verbatim | ✅ |
| `Claude-Production-Grade-Suite/` workspace bootstrap | ✅ | ✅ orchestrator skill body does it | ✅ |
| Receipt schema + verification | ✅ | ⚠️ model writes receipts manually; no auto-verifier | ⚠️ |
| Tool-name compatibility | ✅ | ✅ Read→read_file, WebSearch→tavily_search, etc. | ✅ |
| `!`<cmd>`` skill-body shell preprocessing | ✅ | ⚠️ collapsed to `read_file` instructions at port time (cwd-static) | ⚠️ |

### Pipeline orchestration (~30%)

| Feature | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| `Skill(skill=...)` dynamic dispatch | ✅ orchestrator calls Skill tool | ❌ orchestrator instructs model to read sub-skill SKILL.md inline | ❌ |
| Specialist fresh context | ✅ each subagent = clean slate | ❌ everything in the orchestrator's growing context | ❌ |
| Phase machine (DEFINE → BUILD → HARDEN → SHIP → SUSTAIN) | ✅ | ⚠️ encoded in skill body; model walks it; no enforcement | ⚠️ |
| 3 approval gates (BRD, Architecture, Production Readiness) | ✅ structured ceremonies | ⚠️ plain-text option lists; user types option name | ⚠️ |
| Re-anchoring on phase transitions | ✅ orchestrator re-reads spec from disk | ⚠️ depends on model self-discipline | ⚠️ |
| 10 execution modes (Full Build/Feature/Harden/...) | ✅ | ✅ encoded in orchestrator body | ✅ |

### Multi-agent / parallelism (0%)

| Feature | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| Subagent spawn (`Agent`/`Task` tool) | ✅ | ❌ | ❌ |
| Wave A/B/C parallelism (QA + Security + Code Review running concurrently) | ✅ | ❌ all serialized | ❌ |
| Per-subagent isolation | ✅ separate transcripts | ❌ | ❌ |
| `SendMessage` resume semantics | ✅ | ❌ | ❌ |
| Background tasks (`run_in_background=true`) | ✅ | ❌ | ❌ |
| Worktree isolation | ✅ `isolation: "worktree"` | ❌ | ❌ |

### UI / UX primitives (~20%)

| Feature | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| `AskUserQuestion` structured options | ✅ buttons + descriptions + previews | ⚠️ plain Markdown numbered list; user types option name | ⚠️ |
| `TaskCreate`/`TaskUpdate`/`TaskList` visible progress | ✅ live UI panel | ❌ chat-emitted status lines + receipts after the fact | ❌ |
| Visual Identity protocol headers (`━━━ Role ━━━`) | ✅ | ✅ if model follows the protocol | ✅ |
| Gate ceremonies (header + metrics table + decision options) | ✅ structured cards | ⚠️ plain Markdown | ⚠️ |
| Tool-call renderers in chat | ✅ inline cards per tool | ❌ default tool-call display only | ❌ |
| Live task dashboard (sidebar panel) | ✅ Claude Code's task list | ❌ | ❌ |

### Hooks (limited)

| Event | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| `SessionStart` (project detection: scans for `Claude-Production-Grade-Suite/`, prompts user) | ✅ via `hooks/session-guard.sh` | ❌ | ❌ |
| `UserPromptSubmit` (activation rules: keyword/regex matching → suggest skill) | ✅ via `activation-rules.json` | ❌ user types `/production-grade` explicitly | ❌ |
| `PreToolUse` / `PostToolUse` | ✅ available (production-grade doesn't use directly) | ❌ no plugin path | ❌ |
| `Stop` / `SubagentStop` | ✅ | ❌ | ❌ |
| Plugin startup/shutdown | n/a | ✅ used by installer | ✅ |

### Distribution / install (~50%)

| Feature | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| Plugin manifest format | `.claude-plugin/plugin.json` | `plugin.json` | ✅ ported |
| Marketplace install (`/plugin install <name>@<marketplace>`) | ✅ Anthropic marketplace API | ⚠️ git-clone + `make install` | ⚠️ |
| Skill registration in agent's effective skill list | ✅ automatic | ✅ since v0.1.1 (was broken in v0.1.0) | ✅ |
| Version pinning + updates | ✅ | ✅ git tags | ✅ |

### Other

| Feature | Claude Code | v0.1.1 | Status |
|---|---|---|---|
| Permission gates (`permissions.allow/ask/deny`) | ✅ | ❌ no Tool-Guard config shipped | ❌ |
| `WebSearch` for Freshness Protocol | ✅ first-class | ⚠️ `tavily_search` MCP if `TAVILY_API_KEY` set | ⚠️ |
| `WebFetch` | ✅ | ⚠️ same MCP fallback | ⚠️ |
| Background execution | ✅ | ❌ | ❌ |
| `EnterPlanMode`/`ExitPlanMode` | ✅ | ⚠️ QwenPaw `/plan` command separately | ⚠️ |
| MCP server support (general) | ✅ | ✅ first-class on QwenPaw too | ✅ |
| Auto-memory / `MEMORY.md` | ✅ | ⚠️ QwenPaw's ReMeLight differs | ⚠️ |

---

## Where the gap actually hurts

For **short pipelines** (Feature mode: 1–4 specialists, 1 gate, ~10 min) — the gap is mostly cosmetic. The plain-text gate ceremony works; methodology fidelity is high.

For **medium pipelines** (Harden, Ship: 3–5 specialists, 1–2 gates, ~20 min) — context drift starts to bite. By turn 30+, the agent may forget which phase it's on, mix specialist personas, or skip receipts.

For **Full Build** (all 14 specialists, 5 phases, 3 gates, ~30+ min) — drift becomes severe. The agent often:
- Loses track of which phase it's supposed to be in
- Fails to re-anchor when transitioning
- Skips parallelizable specialists (Wave B QA + Security + Review collapse to sequential)
- Writes receipts inconsistently (some phases lose them)
- Exhausts context window mid-pipeline (orchestrator + 14 SKILL.md bodies + protocols = hundreds of KB)

This is the inherent ceiling of single-agent operation. **It's the architectural reason v0.2+ adds custom ACP runners** — fresh subprocesses per specialist eliminate context accumulation and enable real parallelism.

---

## Path to 100% (per `08_full_parity_architecture.md`)

To close each gap, what work is required:

| Gap | What it takes to close | Tier | Effort |
|---|---|---|---|
| Subagent fresh context | Custom ACP runners (1 per role × 3-4 copies for parallelism) | T2 | ~3-4 days |
| Wave parallelism | Same as above + orchestrator dispatches concurrently | T2 + skill body update | included |
| `Skill` tool dispatch | Custom MCP server with `pg__dispatch_specialist` tool | T3 | ~3 days |
| `AskUserQuestion` structured UI | Frontend plugin + custom MCP tool `pg__ask_user_question` | T3+T4 | ~3 days |
| Gate ceremonies (cards, tables) | Frontend plugin tool renderer | T4 | ~1 day per gate |
| `TaskCreate`/`Update`/`List` visible | Frontend plugin sidebar + backend SSE | T3+T4 | ~2 days |
| `SessionStart` project detect | Plugin startup hook + AgentScope class hook on `pre_reply` | T1+T4-via-monkey-patch | ~1 day |
| `UserPromptSubmit` activation | Same monkey-patch, different logic | T1 | ~0.5 days |
| `PreToolUse`/`PostToolUse` | AgentScope `register_class_hook` on `pre_acting`/`post_acting` | T4-upstream | ~1 day |
| Permission gates | Tool Guard config write at install time | T1 | ~0.5 days |
| `!`<cmd>`` runtime shell preprocessing | Monkey-patch `AgentRunner._maybe_inject_skill` | T3 | ~1 day |
| Marketplace install UX | Out of scope (depends on QwenPaw upstream) | — | — |

**Total to v1.0 (100% retention):** ~3-4 weeks of focused work, per the [`08_full_parity_architecture.md`](./08_full_parity_architecture.md) phased plan.

---

## Recommended v0.2 priority order

If you don't want to wait for v1.0, the highest-leverage next steps in order:

1. **Custom ACP runners** (closes the multi-agent + parallelism + context-drift gaps simultaneously). Single biggest jump.
2. **Custom MCP server + frontend renderer for `AskUserQuestion`** (fixes the UX downgrade on gates).
3. **`SessionStart` + `UserPromptSubmit` monkey-patches** (auto-routes the user without `/production-grade` prefix; restores the "this looks like a build, want me to run it production-grade?" prompt).
4. **`TaskCreate`/`Update` MCP tool + frontend dashboard** (visible progress; nicer than chat-emitted status lines).
5. **`PreToolUse`/`PostToolUse` AgentScope class hooks** (auto-receipt-write; reduces the "agent forgot to write receipt" failure mode).

Steps 1+2 alone push retention from ~65% to ~85%. Steps 1-3 push to ~92%. Steps 1-5 reach ~98%. Full ~100% requires Tier 6 (pre-rendered skills) + permission gates + marketplace polish.

---

## Honest summary table

| Bucket | Weight | v0.1.1 | Notes |
|---|---|---|---|
| Methodology content | 50% | 100% | All 14 SKILL.md bodies + 8 protocols ported faithfully |
| Pipeline orchestration | 25% | 30% | Single-agent walk; no real Skill dispatch; receipts manual |
| UI / UX primitives | 15% | 20% | Plain-text gates; no task UI; no tool renderers |
| Multi-agent parallelism | 10% | 0% | Not implemented |
| **Weighted total** | **100%** | **~60-65%** | |

Don't claim 100%. v0.1.1 is a useful, installable, runnable baseline that delivers production-grade artifacts in single-agent mode. The path to true parity is documented and tractable; it just isn't done yet.
