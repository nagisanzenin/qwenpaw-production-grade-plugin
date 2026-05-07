# Compatibility Matrix: production-grade (Claude Code) → QwenPaw

> Feature-by-feature port assessment. Sources cited inline. ✅ direct port, ⚠️ adaptable with rework, ❌ no clean port.
> Companion docs: `research_notes/01_production_grade_map.md`, `research_notes/02_qwenpaw_map.md`, `research_notes/03_qwenpaw_official_docs.md`, `research_notes/04_claude_code_official_docs.md`.

---

## Surface-by-surface comparison

### 1. Plugin manifest

| Aspect | Claude Code (production-grade) | QwenPaw | Status |
|---|---|---|---|
| Manifest path | `.claude-plugin/plugin.json` | `plugins/<id>/plugin.json` | ⚠️ relocate |
| Required fields | `name` (only) — but production-grade fills all | `id`, `name`, `version`, `description`, `entry.backend` | ⚠️ need `id` + Python entry |
| Versioning | Semver, manual bump | Semver in manifest; pyproject can pin `min_version` | ✅ |
| Author | `{name, email?}` object | string field | ✅ trivial |
| License | string | not in spec — store in `meta` if needed | ⚠️ |
| Keywords | `keywords[]` for marketplace search | not standardized | ⚠️ omit or stash in `meta.keywords` |
| Path overrides (skills/agents/commands/hooks) | per-key string\|array | not supported — all skills load from agent workspace; plugins register tools/providers | ❌ different model |

**Production-grade `plugin.json` (5.4.0):**
```json
{
  "name": "production-grade",
  "description": "...",
  "version": "5.4.0",
  "author": {"name": "nagisanzenin"},
  "license": "MIT",
  "keywords": ["production-grade","saas","orchestrator",...]
}
```

**QwenPaw target:**
```json
{
  "id": "production-grade",
  "name": "Production-Grade",
  "version": "5.4.0",
  "description": "...",
  "author": "nagisanzenin",
  "entry": {"backend": "plugin.py"},
  "dependencies": [],
  "min_version": "1.1.5",
  "meta": {
    "license": "MIT",
    "keywords": ["production-grade","saas","orchestrator",...]
  }
}
```

> **Doc:** plugins.en.md:88–101 (QwenPaw manifest) ; plugins-reference (Claude Code manifest).

---

### 2. Skills

| Aspect | Claude Code | QwenPaw | Status |
|---|---|---|---|
| File | `<plugin>/skills/<name>/SKILL.md` | workspace `~/.qwenpaw/workspaces/<id>/skills/<name>/SKILL.md` (or shipped under `~/.qwenpaw/skill_pool/`) | ⚠️ install location |
| Frontmatter required | `description` recommended; all optional | `name` and `description` **required** (skills.en.md:255–279) | ⚠️ ensure both present |
| `allowed-tools` | yes — pre-approval list | **not in QwenPaw spec** — use `agent.json.tools` instead | ❌ drop from frontmatter |
| `model` | `sonnet`/`opus`/`haiku`/`inherit` | not in skill frontmatter — `agent.json.active_model` is the agent-wide model | ❌ drop from frontmatter |
| `disable-model-invocation` | yes | not documented | ❌ drop |
| `argument-hint`/`arguments` | yes (`$ARGUMENTS`, `$N`, `$<name>`) | not in QwenPaw spec | ❌ drop; rephrase prompts to expect free text |
| `paths` (auto-activate by file glob) | yes | not in QwenPaw spec | ❌ drop |
| `hooks` in frontmatter | yes (skill-scoped) | no | ❌ drop |
| `metadata.requires.{bins,env}` | not defined | yes — env injection (skills.en.md:316–397) | ✅ NEW capability for QwenPaw port |
| Body activation | injected once via `Skill` tool call; stays in context | passive: model reads from skill manifest into context | ⚠️ different invocation pattern |
| `` !`shell` `` preprocessing | yes (Claude Code runtime) | **not documented in QwenPaw skills** — body is injected as-is | ❌ replace with static content |
| Substitutions (`${CLAUDE_SKILL_DIR}`, `$ARGUMENTS`) | yes | no equivalents documented | ❌ replace with absolute paths or env vars |
| Language variants (`-en/-zh`) | not used | source has them but **not in spec** (skills.en.md doesn't define this) | ⚠️ ship one SKILL.md per skill (English content); handle Chinese later |
| Marketplace install | `/plugin install` | `qwenpaw skills install <slug>` from skills.sh, clawhub.ai, lobehub, github, modelscope (skills.en.md:170–178) | ⚠️ different |

#### Production-grade skill frontmatter (representative)

Production-grade uses minimal frontmatter (just `name` and `description`), so port is mostly content-rewrite:

```yaml
# Source (Claude Code)
---
name: production-grade
description: >
  Use when the user wants to build, create, or develop anything ...
---
```

```yaml
# Target (QwenPaw)
---
name: production-grade
description: >
  Use when the user wants to build, create, or develop anything ...
metadata:
  requires:
    bins: [git]   # if git is needed by the skill body
    env: []
  qwenpaw:
    emoji: "🏗"
---
```

#### Body translations needed

The biggest content surgery is the **inline `` !`cat ...` `` blocks** that production-grade uses to load shared protocols at skill startup (`research_notes/01_production_grade_map.md:97–105`). QwenPaw does not pre-process those. Three strategies:

1. **Inline the protocols** into each SKILL.md body (more text, no runtime dep).
2. **Move protocols into reference files** alongside SKILL.md and instruct the model to Read them (works because QwenPaw's `read_file` tool is built-in).
3. **Use `metadata.requires.env` to inject protocol JSON** via `QWENPAW_SKILL_CONFIG_<NAME>` env var (skills.en.md:316–397) — most flexible but requires plugin-side config writes.

> Recommendation: **strategy 2 (sibling reference files + Read instructions)** for the cleanest port; the orchestrator skill body lists the eight protocols and the model reads them via `read_file`.

---

### 3. Sub-agents / Agent dispatch

| Aspect | Claude Code | QwenPaw | Status |
|---|---|---|---|
| In-process subagents | yes — `Agent` tool spawns `.claude/agents/<name>.md` | **no in-process subagents** — only ACP external runners or peer agents | ❌ pattern shift |
| Built-in subagent types | `Explore`, `Plan`, `general-purpose`, etc. | none equivalent | ❌ |
| Agent file format | `.md` with frontmatter (system-prompt-replacement) | n/a | ❌ |
| Agent isolation | `isolation: "worktree"` | not exposed | ❌ |
| Agent memory | `memory: user/project/local` | per-agent workspace dir (multi-agent.en.md:230–248) | ⚠️ adapt |
| Spawning external agents | n/a (built-in) | `delegate_external_agent(runner, action, message)` (acp-integration.en.md:39–55,84–93) | ⚠️ external only |
| Inter-agent chat | `SendMessage(to=agentId)` (experimental) | `chat_with_agent`, `submit_to_agent`, `check_agent_task` (peer agents in same workspace) | ⚠️ adapt |
| Background tasks | `Agent(run_in_background=true)`, `Ctrl+B` | streaming AsyncGenerator from delegate, but no background flag | ⚠️ |

**Production-grade dispatch pattern** (`research_notes/01_production_grade_map.md:147–158`): the orchestrator skill calls `Skill(skill="production-grade:product-manager", ...)` to invoke each specialist. Then a separate `TeamCreate/TaskCreate/TaskUpdate` flow tracks parallel execution.

**Three porting options:**

**Option A — collapse to single-agent flow (RECOMMENDED for v1).**
Merge all 14 specialist skills into one big SKILL.md per *mode* (Full Build, Feature, Harden, Ship, ...). The single agent reads sequential phase instructions, calls tools to write artifacts, and self-routes through phases by reading the skill body. **No subagents needed.** Trade-off: longer single-agent reasoning chains, but matches QwenPaw's idiomatic flow.

**Option B — peer multi-agent (one QwenPaw agent per role).**
Provision 14 agents in QwenPaw (one per specialist). Use the `multi_agent_collaboration` built-in skill (multi-agent.en.md:259–264) to let the orchestrator agent invoke specialists via `chat_with_agent`. Requires user to create those agents on install. Heavyweight; closest to production-grade's mental model.

**Option C — ACP delegation to claude_code itself.**
QwenPaw can delegate to a `claude_code` ACP runner (acp-integration.en.md:84–93). The plugin could literally run the original Claude Code production-grade plugin **inside** Claude Code, called from QwenPaw. Defeats the purpose unless the user wants the Claude Code experience but routed through their QwenPaw frontend. Useful as a fallback but not a real port.

> Recommendation: **Option A** for v1. Document option B as a future power-user mode.

---

### 4. Hooks

This is the **single largest gap.**

| Claude Code event | Production-grade uses it? | QwenPaw equivalent | Status |
|---|---|---|---|
| `SessionStart` | ✅ → `hooks/session-guard.sh` (detects `Claude-Production-Grade-Suite/`) | **No public plugin hook.** AgentScope `pre_reasoning` via monkey-patch only. Closest official: BootstrapHook (one-shot first-prompt). | ⚠️ rework |
| `UserPromptSubmit` | ✅ → `activation-rules.json` (keyword/regex routing recommendations) | Documented escape hatch: monkey-patch `AgentRunner.query_handler` (plugins.en.md:1080–1099) | ⚠️ monkey-patch |
| `PreToolUse` / `PostToolUse` | not used by production-grade as far as we can see | AgentScope `post_acting` via monkey-patch | ⚠️ if needed |
| `Stop` / `SubagentStop` | not used | none | n/a |
| `PreCompact` / `PostCompact` | not used | none | n/a |
| `Notification`, `TaskCreated`, etc. | not used | none | n/a |

**Two hooks production-grade actually uses, mapped:**

#### A. `SessionStart` — project detection on session entry

Source: `hooks/hooks.json` and `hooks/session-guard.sh`.

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|clear|compact",
        "hooks": [{ "type": "command",
                    "command": "bash $CLAUDE_PLUGIN_ROOT/hooks/session-guard.sh",
                    "timeout": 10 }] } ]
  }
}
```

The script detects `Claude-Production-Grade-Suite/` in cwd and prompts the user with options.

**QwenPaw port:**

```python
# plugins/production-grade/plugin.py
class ProductionGradePlugin:
    def register(self, api: PluginApi):
        api.register_startup_hook(
            hook_name="pg_session_guard",
            callback=self._patch_query_handler,
            priority=50,
        )

    def _patch_query_handler(self):
        from qwenpaw.app.runner.runner import AgentRunner
        original = AgentRunner.query_handler

        async def patched(self, request, *args, **kwargs):
            cwd = request.context.get("cwd") or os.getcwd()
            suite_dir = Path(cwd) / "Claude-Production-Grade-Suite"
            if suite_dir.is_dir() and not _already_warned(self.session_id):
                guidance = _build_guidance_message(suite_dir)
                request = _prepend_system_message(request, guidance)
                _mark_warned(self.session_id)
            return await original(self, request, *args, **kwargs)

        AgentRunner.query_handler = patched
```

**Caveats:** `AgentRunner.query_handler` is the QwenPaw-documented monkey-patch target (plugins.en.md:1083). Pin `qwenpaw>=1.1.5,<1.2`.

#### B. `UserPromptSubmit` — activation rules

Source: `skills/production-grade/hooks/activation-rules.json` — keyword/regex routing.

In Claude Code: a hook script reads the user's prompt, matches against activation rules, and prepends a recommendation message. In QwenPaw: same pattern, same monkey-patch target (every prompt flows through `query_handler`).

```python
def _check_activation_rules(prompt: str) -> Optional[str]:
    rules = json.load(...)["rules"]
    for r in rules:
        if any(kw in prompt.lower() for kw in r["keywords"]):
            return f"💡 Suggested skill: /{r['skill']} — {r['recommendation']}"
        if any(re.search(p, prompt, re.I) for p in r["intent_patterns"]):
            return f"💡 Suggested skill: /{r['skill']} — {r['recommendation']}"
    return None
```

> Both A and B share the same monkey-patch — fold them into one wrapper.

---

### 5. Slash commands

| Aspect | Claude Code | QwenPaw | Status |
|---|---|---|---|
| Custom slash commands | `/<plugin>:<command>` from `commands/<name>.md` (frontmatter optional) | Built-in commands only (commands.en.md). For plugin-defined commands: **monkey-patch `AgentRunner.query_handler`** (plugins.en.md:546–622, Example 3) | ⚠️ rework |
| `register_control_command` API | n/a | exists in source but **undocumented** (api.py:153) — avoid for portability | ⚠️ |
| `$ARGUMENTS` substitution | yes | n/a — body is plain markdown injected as context | ❌ |
| Built-in `/skills` listing | `/skills` (skill manager) | `/skills` (different command shape; see commands.en.md:289–306) | ⚠️ |

**Production-grade exposes:** `/production-grade:software-engineer`, `/production-grade:security-engineer`, etc. plus the top-level `/production-grade`. All are skill-routed (no separate `commands/` files).

In QwenPaw, **users invoke skills by mentioning them in the prompt or via the `/<skill_name>` form** (commands.en.md:289–306), e.g., `/software-engineer build the auth flow`. So the slash-command experience already exists for skills — just under the bare skill name (no `<plugin>:` prefix).

> No code change needed for the slash UX itself. Users say `/software-engineer ...` instead of `/production-grade:software-engineer ...`.

---

### 6. Marketplace / installation

| Aspect | Claude Code | QwenPaw | Status |
|---|---|---|---|
| Marketplace manifest | `.claude-plugin/marketplace.json` (Claude Code) | n/a — `qwenpaw plugin install <source>` accepts URL/local path/zip | ⚠️ |
| Hosted registry | yes (cache under `~/.claude/plugins/cache/`) | none default; community hubs (clawhub.ai, lobehub) for skills only | ⚠️ |
| Install command | `/plugin install production-grade@nagisanzenin` | `qwenpaw plugin install https://github.com/nagisanzenin/qwenpaw-production-grade-plugin/...` | ⚠️ |
| Per-user enable | `/plugin enable production-grade` | enabled via `~/.qwenpaw/config.json` after install | ⚠️ |

> Distribution: ship as a GitHub repo. Users `git clone` then `qwenpaw plugin install /path/to/clone`. (Or zip release artifacts.)

---

### 7. Skills the orchestrator depends on

Production-grade's orchestrator orchestrates 13 specialists via the `Skill` tool. In QwenPaw the cleanest equivalent is **a skill body that reads sibling reference files** and a single agent that walks the pipeline.

| Specialist skill | Notes for port |
|---|---|
| `polymath` | Dialogue-only; trivial direct port |
| `product-manager` | Generates BRD; trivial port |
| `solution-architect` | ADRs + API contracts; trivial port |
| `software-engineer` | Backend implementation; uses `read_file`/`write_file`/`edit_file`/`grep_search`/`glob_search`/`execute_shell_command` — all built-in QwenPaw tools |
| `frontend-engineer` | Same toolset; consider whether `browser_use` is enabled |
| `qa-engineer` | Trivial; uses `execute_shell_command` for test runs |
| `security-engineer` | Same |
| `code-reviewer` | Same; read-only |
| `devops` | Uses `execute_shell_command` for docker/terraform |
| `sre` | Trivial |
| `technical-writer` | Trivial |
| `data-scientist` | Trivial |
| `skill-maker` | Generates new skills — adapt to write `~/.qwenpaw/workspaces/<id>/skills/<name>/SKILL.md` |

> All 13 specialists port directly as text. The "tool surface" they describe is mostly file ops + shell, all of which are built into QwenPaw.

---

### 8. Tool primitives used in skill bodies

| Claude Code tool | QwenPaw equivalent | Notes |
|---|---|---|
| `Read` | `read_file` | direct |
| `Write` | `write_file` | direct |
| `Edit` | `edit_file` | direct |
| `Glob` | `glob_search` | direct |
| `Grep` | `grep_search` | direct |
| `Bash` | `execute_shell_command` | direct |
| `WebSearch` | `tavily_search` (built-in MCP when `TAVILY_API_KEY` set, mcp.en.md:142) | ⚠️ require API key |
| `WebFetch` | manual fetch via shell + URL, or via MCP server | ⚠️ |
| `Skill` | n/a — skills are passive | rewrite orchestrator routing |
| `Agent` (Task) | `delegate_external_agent` (ACP) or `chat_with_agent` (peer) | ⚠️ pattern shift |
| `SendMessage` (resume) | `submit_to_agent` + `check_agent_task` (peer agents) | ⚠️ |
| `AskUserQuestion` | n/a — use plain text questions or `/approval` flow | ❌ pattern shift |
| `TaskCreate`/`TaskUpdate`/`TaskList` | n/a — there is no shared task list primitive | ❌ replace with file-based receipts |
| `TeamCreate`/`TeamDelete` | n/a — peer agents already exist; no team primitive | ❌ no-op |
| `ToolSearch` | n/a — QwenPaw doesn't gate tool schemas behind a search tool | ❌ no-op |
| `ExitPlanMode` | `/plan` command (commands.en.md:906–914) | ⚠️ |
| `EnterPlanMode` | `/plan` command | ⚠️ |
| `WebFetch` | run via MCP server like `playwright` if needed | ⚠️ |
| `ScheduleWakeup` | `/cron` skill + `qwenpaw cron` CLI (already a built-in QwenPaw skill) | ✅ |
| `RemoteTrigger` | likely `/proactive` mode | ⚠️ |

**The tool deltas that materially affect the port:**
1. **No `AskUserQuestion`** — production-grade's "gate ceremonies" (Visual Identity protocol §4) need rework. Either render plain Markdown options + ask for free-text reply, or hook the QwenPaw `/approval approve|deny` flow.
2. **No `TaskCreate` shared list** — production-grade tracks task progress via `TaskCreate`/`TaskUpdate` for human visibility. In QwenPaw, this needs to be either a file-based receipt log or progress messages emitted into the chat. Receipts are already used (`Claude-Production-Grade-Suite/.orchestrator/receipts/`); double up on those.
3. **No `WebSearch`** unless Tavily MCP is configured — Freshness Protocol needs `TAVILY_API_KEY` documented in install instructions.

---

### 9. State persistence (`Claude-Production-Grade-Suite/`)

Both runtimes are file-based. QwenPaw tools (`read_file`, `write_file`, `edit_file`) work identically. **The entire `Claude-Production-Grade-Suite/` directory structure ports verbatim.** No code changes needed.

The only difference is what triggers its detection:
- Claude Code: `SessionStart` hook + `session-guard.sh`
- QwenPaw: monkey-patched `query_handler` checks for the directory on every prompt (or, more efficiently, on first prompt only via a session flag).

---

### 10. Settings & configuration

| Aspect | Claude Code | QwenPaw | Status |
|---|---|---|---|
| Plugin user config | `plugin.json.userConfig` (typed; UI-prompted) | `plugin.json.meta.config_fields[]` (plugin example pattern, plugins.en.md) | ⚠️ different schema, similar idea |
| Per-tool permissions | settings.json `permissions.{allow,ask,deny}` | `agent.json.tools.<name>.{enabled, config}` + Tool Guard mixin (config.en.md:206–565) | ⚠️ different model |
| Auto-memory | `~/.claude/CLAUDE.md`, `MEMORY.md` (autoMemoryEnabled) | ReMeLight (different system) | ❌ different |
| Hot-reload | `/reload-plugins` | 2-second config poll (config.en.md:706) | ✅ better in QwenPaw |
| Env vars | `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` | `${QWENPAW_WORKING_DIR}`, `${QWENPAW_SECRET_DIR}`, plugin's own `__file__` derivations | ⚠️ different names |

---

### 11. Claude Code features that have NO QwenPaw equivalent

These need to be designed around or dropped:

1. **`AskUserQuestion`** — No structured-options UI primitive in QwenPaw plugin API.
2. **In-process subagents** with system-prompt-replacement.
3. **`Task`/`Agent` tool with built-in agent types** (`Explore`, `Plan`, etc.).
4. **`SendMessage` resume semantics** — peer agents support submit/check but not "resume the agent from this transcript point."
5. **`EnterWorktree`/`ExitWorktree`** — git worktree isolation per subagent.
6. **`PreToolUse`/`PostToolUse` plugin hooks** — only via AgentScope monkey-patch.
7. **`@agent-<name>` mention syntax** — different invocation pattern.
8. **`disable-model-invocation`** — no equivalent.
9. **Plugin-bundled `bin/` PATH injection** — n/a.
10. **`disableSkillShellExecution`** lockdown — QwenPaw has no skill shell preprocessing to disable.

---

### 12. QwenPaw features that production-grade does NOT use (yet)

Worth knowing they exist for future versions:

- **MCP-first integrations** (mcp.en.md): can replace any out-of-process tool with a hot-reloadable MCP server.
- **Channel routing** (channels.en.md): per-skill enable/disable per channel (DingTalk, Discord, etc.).
- **Heartbeat / Proactive mode** (heartbeat.en.md): scheduled or self-initiating agent runs.
- **Mission Mode** (commands.en.md:687–891): `/mission` PRD/worker/verifier pipeline — looks like a built-in mini-orchestrator that overlaps production-grade's purpose. Worth comparing.
- **Plan Mode** (commands.en.md:906–914): `/plan` for plan-first execution.
- **Tool Guard** (`src/qwenpaw/agents/tool_guard_mixin.py`): per-tool approval with config.

> The `/mission` built-in is worth investigating before launching a port — if it covers 80% of production-grade's "Full Build" mode, the port becomes a much smaller surface (specialist skills + protocols only).

---

## TL;DR matrix

| Production-grade component | Port path | Effort |
|---|---|---|
| 14 SKILL.md files | Direct content port; minor frontmatter cleanup; inline `` !`cat` `` → sibling-file-reads | M |
| 8 shared protocol files | Direct port (text only) | S |
| `plugin.json` manifest | Translate to QwenPaw schema | S |
| `hooks/session-guard.sh` (`SessionStart`) | Monkey-patch `AgentRunner.query_handler` in plugin startup | M |
| `activation-rules.json` (`UserPromptSubmit`) | Same monkey-patch; merge with above | S |
| Orchestrator's `Skill(skill="…")` calls | Rewrite as in-skill phase routing OR peer-agent `chat_with_agent` calls | L |
| `AskUserQuestion` ceremonies | Rewrite as plain-text option lists + free-text reply OR `/approval` integration | M |
| `TaskCreate`/`TaskUpdate` progress tracking | Replace with progress messages + existing receipts | S |
| `Claude-Production-Grade-Suite/` workspace | Verbatim — file-based, runtime-agnostic | none |
| Marketplace install | Document `qwenpaw plugin install <git-url>` | S |

**Total feasibility: ~80% direct port** (skills, protocols, workspace, tool primitives). **~20% requires rework** — primarily the orchestration pattern, hook surface, and `AskUserQuestion`-driven gate ceremonies.

The single biggest design decision is **option A vs option B** for the orchestrator (single-agent walk vs. peer multi-agent). Option A is the path of least resistance.
