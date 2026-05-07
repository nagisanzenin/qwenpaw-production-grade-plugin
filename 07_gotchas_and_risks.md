# Gotchas & Risks

> Things that don't translate cleanly, surprises in the docs, and risks to plan around. Pairs with `05_compatibility_matrix.md` and `06_migration_plan.md`.

---

## Hard blockers (no clean QwenPaw path)

### G-1. No `AskUserQuestion` primitive

**Claude Code:** structured-options UI with descriptions, headers, single/multi-select, "Other" escape hatch.

**QwenPaw:** no equivalent. The `/approval approve|deny|list|cancel` flow (commands.en.md:639–663) is the closest, but it's permission-only and doesn't carry rich option metadata.

**Impact:** every "gate ceremony" in production-grade (3 in Full Build mode; 1 each in Feature/Harden/Ship/Architect/Optimize) needs to be rewritten as plain-text option lists, with the model parsing the user's free-text reply.

**Mitigation:** Pattern A from `06_migration_plan.md §2.4` — render numbered options, ask the user to type the number or option name. Risk: ambiguous replies. Document in user docs that exact match is preferred.

### G-2. No in-process subagents

**Claude Code:** `Agent(subagent_type="Explore")`, `Agent(subagent_type="general-purpose")`, custom `.claude/agents/<name>.md` files. New context, separate transcript.

**QwenPaw:** only **external ACP runners** (`opencode`, `qwen_code`, `claude_code`, `codex`) and **peer agents** in the same workspace (`chat_with_agent`, `submit_to_agent`). Both incur process overhead; neither replicates Claude Code's lightweight in-process spawn.

**Impact:** v1 of the port should NOT try to replicate the multi-agent orchestration; collapse to single-agent flow (Option A in the migration plan).

### G-3. No per-tool / per-prompt plugin hooks

**Claude Code:** `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, etc. are first-class, scoped by matcher.

**QwenPaw plugin API:** only `register_startup_hook` and `register_shutdown_hook`. Per-prompt requires monkey-patching `AgentRunner.query_handler` (officially documented at plugins.en.md:1080–1099). Per-tool requires monkey-patching AgentScope's `register_instance_hook` machinery (`pre_reasoning`, `pre_reply`, `post_acting`, `post_reply` — react_agent.py:446–487), which is upstream and unstable.

**Impact:** the plugin's two existing hooks (SessionStart and UserPromptSubmit) port via a single `query_handler` patch. **If we ever want PreToolUse-style intercepts**, we have to climb into AgentScope, which is fragile.

**Mitigation:** v1 doesn't need PreToolUse. Document this constraint in `decisions.md`.

---

## Soft blockers (workarounds exist but are awkward)

### G-4. SKILL.md doesn't run inline shell

**Claude Code:** the SKILL.md body is preprocessed: `` !`cat protocols/foo.md` `` is executed and the output replaces the placeholder before the model sees the body.

**QwenPaw:** the skill body is **injected as-is** (skills.en.md doesn't mention shell preprocessing; nothing in the codebase suggests it exists).

**Impact:** every `!`cat …`` block in the 14 skills must be rewritten.

**Mitigation:** two options:

1. **Inline** the protocols' contents into each SKILL.md body. Trade-off: ~8 × ~200 lines of redundant text per skill = ~1600 extra lines per skill × 14 skills = 22 000 lines of duplication. Token-heavy.
2. **Sibling-file Reads** — instruct the model to read the eight protocol files via `read_file` at startup. Trade-off: extra tool calls upfront; depends on knowing the plugin root path.

The migration plan picks option 2 (sibling reads) and threads `${PG_ROOT}` via env var.

### G-5. Tool name mismatches in skill bodies

Production-grade SKILL.md bodies mention "Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebSearch", "AskUserQuestion", "TaskCreate", "TaskUpdate", "Skill", "Agent" — all Claude-Code-specific.

**Mitigation:** mass find-and-replace per the table in `06_migration_plan.md §2.3`. Worth a unit test that greps the ported skill bodies for stale references (e.g., `WebSearch(`, `Skill(`, `Agent(`).

### G-6. No shared `TaskCreate`/`TaskList` primitive

Production-grade uses `TaskCreate`/`TaskUpdate` for human-visible progress. QwenPaw has no equivalent.

**Mitigation:** the `Claude-Production-Grade-Suite/.orchestrator/receipts/` directory already serves as the ground-truth state log. Skip `TaskCreate` and have the model emit progress messages into the chat plus write receipts.

### G-7. No `WebSearch` built-in

Production-grade's Freshness Protocol leans on `WebSearch`. QwenPaw ships `tavily_search` MCP only when `TAVILY_API_KEY` is set.

**Mitigation:** require `TAVILY_API_KEY` in install instructions. Add a one-time check in `plugin.py._on_startup` that warns if not configured.

### G-8. `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` substitutions

Production-grade hooks reference `${CLAUDE_PLUGIN_ROOT}`. QwenPaw has none.

**Mitigation:** during plugin startup, set `os.environ["PG_ROOT"] = str(Path(__file__).parent)`. Skills reference `${PG_ROOT}`. **Caveat:** child processes started from QwenPaw inherit env from the parent — make sure the patch happens before any tool spawns.

### G-9. Skill marketplace install isn't a thing for plugins

Production-grade is distributed via Anthropic's plugin marketplace. QwenPaw's `qwenpaw plugin install <source>` accepts a path/URL/zip but there's no public registry of plugins (yet).

**Mitigation:** distribute via GitHub repo + `qwenpaw plugin install <git-url>`. Document the install command prominently in README.md.

### G-10. No `disable-model-invocation` knob

Some Claude Code skills set `disable-model-invocation: true` (the user must explicitly invoke). QwenPaw skills are always model-discoverable through the description.

**Mitigation:** the production-grade orchestrator's sub-skills (e.g., `production-grade:software-engineer`) are intended to be called only by the orchestrator. With QwenPaw, the model could pick them directly. This is mostly fine — the descriptions can encode "only invoke as part of the production-grade pipeline" — but expect occasional drift.

---

## Risks (known unknowns)

### R-1. `AgentRunner.query_handler` signature drift

The exact attribute path to the user prompt and session ID inside `request` is unverified. Plugins.en.md:1083–1099 shows only the patch shape, not the request fields. **Action:** Phase-0.5 spike must capture the actual attributes; pin a unit test against a fake request to detect breakage when QwenPaw upgrades.

### R-2. `agentscope` / `agentscope-runtime` version creep

QwenPaw's per-turn hooks (if needed) live in upstream AgentScope. AgentScope ships independently. Pinning `qwenpaw>=1.1.5,<1.2` doesn't pin its transitive deps unless we also pin them or the plugin uses `dependencies` in `plugin.json`.

**Action:** read QwenPaw's `pyproject.toml` constraints; if AgentScope is loosely pinned, pin tighter in our plugin's `dependencies` list.

### R-3. `qwenpaw>=1.1.6b1` is a beta head

The active QwenPaw build is `1.1.6b1` (beta). The previous stable is `1.1.5` (last entry in `website/public/release-notes/`). Plugin schema and PluginApi might shift between beta releases.

**Action:** target stable `1.1.5` for v1; re-test on `1.1.6` before claiming compatibility.

### R-4. `~/.qwenpaw/workspaces/{id}/skills/` is per-agent

Skills are per-agent in the documented config, but the `~/.qwenpaw/skill_pool/` is workspace-shared (research_notes/02_qwenpaw_map.md). Need to verify which the plugin should write to during install.

**Action:** Phase-0.3 spike should test both. Default to `skill_pool/` for a single install across multiple agents.

### R-5. Channel routing changes the contract

QwenPaw skills have **per-channel routing** (`skill.json.skills.<name>.routing.<channel>.enabled`). A specialist enabled in `console` but disabled in `dingtalk` will be invisible there. The plugin needs to default-enable across all channels and document how users disable per-channel.

**Action:** spike whether the install can write `routing.*.enabled = true` for each shipped skill or whether QwenPaw infers it.

### R-6. Tool Guard might block built-in tools that production-grade SKILL.md bodies tell the model to use

Production-grade tells the model "use Bash to run pytest" and "use Edit to fix the code". QwenPaw's Tool Guard may have stricter defaults (per `agent.json.tools.builtin_tools.execute_shell_command.config.shell_evasion_check`).

**Action:** install instructions must call out which tools the plugin expects enabled. Possibly emit a startup-hook check that prints a warning if any required tool is disabled.

### R-7. `delegate_external_agent` runtime cost

If we ever take Option B (peer multi-agent) or Option C (delegate to claude_code ACP), each delegation spawns a subprocess. For a Full Build mode (14 specialists), that's potentially 14 subprocesses with their own model state. Token cost balloons; coordination overhead grows.

**Action:** stay in Option A for v1. Document peer-mode as v2 with a cost warning.

### R-8. The `Claude-Production-Grade-Suite/` directory is at project root

Production-grade writes `Claude-Production-Grade-Suite/` to the cwd. QwenPaw runs the agent in the agent's workspace, not the user's project root. **The "cwd" the agent sees might not be the user's git repo.**

**Action:** clarify in install instructions that production-grade's workflow assumes the user's project root is the agent's working directory. If QwenPaw's working directory model differs, the plugin may need to ask the user "what's your project root?" on first invocation.

### R-9. `register_control_command` evolution

The undocumented `register_control_command` (api.py:153) might become public — or get removed — in 1.2. We're not using it, but if we change our minds, we're betting on a private API.

**Action:** keep the monkey-patch path. Re-evaluate after QwenPaw 1.2 stable releases.

---

## Surprises in the docs

1. **`docs.claude.com/en/docs/claude-code/*` 301s to `code.claude.com/docs/en/*`.** All older Anthropic doc links should be updated.
2. **`Task` was renamed to `Agent` in Claude Code v2.1.63.** Both still work but new docs use `Agent`.
3. **Hook events expanded from ~9 to ~29** (research_notes/04_claude_code_official_docs.md §2). Production-grade only uses 2 of them — useful to know we don't need the full surface.
4. **Skills and slash commands are unified in Claude Code.** A single `<name>` resolves to either `commands/<name>.md` or `skills/<name>/SKILL.md`. Plugin namespace prefix `<plugin>:<name>` is structural.
5. **QwenPaw has a built-in `/mission` PRD/worker/verifier mode.** Possibly overlaps with production-grade's Full Build pipeline. Phase-0.4 spike investigates.
6. **`Claude Code` is one of QwenPaw's ACP runners** (acp-integration.en.md:84–93). The QwenPaw user can already delegate to Claude Code for code tasks — production-grade can orchestrate Claude Code from QwenPaw if we want.
7. **QwenPaw's skill marketplace URLs include clawhub.ai** (skills.en.md:170–178) — which is the same brand identity as the original Claude Code plugin. Worth coordinating with the plugin author.

---

## Test gating before each phase exits

Each phase's exit gate should run these before merging:

```bash
# 1. Manifest is valid
python -c "import json; json.load(open('plugin.json'))"

# 2. Skills load
qwenpaw plugin install . --force
qwenpaw skills list | grep production-grade

# 3. Skill body is injected
echo "/production-grade hello" | qwenpaw chat   # adapt to actual CLI form

# 4. Activation rules trigger
echo "build me a SaaS" | qwenpaw chat | grep -q "production-grade"

# 5. Project detection triggers
mkdir -p test-proj/Claude-Production-Grade-Suite/.protocols
cd test-proj && echo "hi" | qwenpaw chat | grep -q "Production-Grade Native Project Detected"

# 6. No stale Claude-Code references in ported skills
grep -RE "(Skill\(|Agent\(|TaskCreate|AskUserQuestion|WebSearch\()" skills/ | grep -v "tavily_search" || echo OK
```

(All of these are sketches — `qwenpaw chat` may not be the literal CLI; adapt during Phase 0.)

---

## Recommended risk posture

1. **Hard-pin `qwenpaw>=1.1.5,<1.2`** until 1.2 stable lands.
2. **Avoid `register_control_command`** and `window.QwenPaw.modules` (both flagged unstable in research_notes/03_qwenpaw_official_docs.md).
3. **Inline what you can, monkey-patch only when necessary.** One monkey-patch (the `query_handler`) covers both hook surfaces production-grade actually uses.
4. **Keep skills runtime-agnostic.** Their bodies are mostly text; portability across runtimes is the easiest part.
5. **Treat orchestration as the hardest sub-problem.** Most of the implementation work in this port is recasting the Skill-tool-driven orchestration as a single-agent walk through the pipeline.
