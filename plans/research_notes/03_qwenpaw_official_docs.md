# QwenPaw Official-Documentation Audit

> Distinguishes what is **publicly documented** (stable to depend on) from what is **source-only** (semi-private, may change).
> Local repo: `/Users/quanduong/Documents/Github/QwenPaw`
> Active version: `1.1.6b1` (beta) — `src/qwenpaw/__version__.py`
> Docs site: SPA at `https://qwenpaw.agentscope.io/` (content under `website/public/docs/<slug>.<lang>.md`)

---

## 1. Doc URL Structure (sidebar source-of-truth: `website/src/pages/Docs.tsx:154-216`)

Six groups, one slug per page (each at `https://qwenpaw.agentscope.io/docs/<slug>`):

- **Welcome:** `intro`, `quickstart`, `desktop`
- **Control:** `console`, `channels`, `commands`, `plan`, `heartbeat`, `memory`, `memory-evolving-and-proactive`
- **Agent:** `persona`, `multi-agent`, `skills`, `mcp`, `context`, `config`
- **Settings:** `models`, `security`, `backup`, `cli`, **`plugins`**
- **Practice:** `practice-agent-team`
- **Others:** `faq`, `api-tutorial`, `acp-integration`, `community`, `contributing`, `roadmap`

**Hidden:** `comparison` (linked only from FAQ).

**Confirmed:**
- ✅ `/docs/skills`, `/docs/plugins`, `/docs/mcp`, `/docs/multi-agent`, `/docs/acp-integration`, `/docs/commands`, `/docs/config`
- ❌ No dedicated "hooks" or "extension" page — hooks are a section inside `plugins`, extensibility is the `plugins` page.

---

## 2. Skill spec — official

Source: `website/public/docs/skills.en.md`, "Create manually in the workspace" (lines 244–283).

**Required frontmatter:** `name`, `description` only.
**Optional:** `metadata.requires.bins[]`, `metadata.requires.env[]`.

> "`name` and `description` are **required**. `metadata` is optional." (skills.en.md:255–279)

**Metadata key precedence (skills.en.md:396):** `metadata.openclaw.requires` → `metadata.qwenpaw.requires` → `metadata.requires` (first match wins).

**Runtime config injection:** env vars matched against `requires.env`, plus a JSON blob at `QWENPAW_SKILL_CONFIG_<SKILL_NAME>` (skills.en.md:316–397).

**`-en` / `-zh` filename suffixes are NOT in the spec.** That's a Claude Code convention only. QwenPaw selects language at the agent level via `agent.json.language` and `system_prompt_files`, not via skill filename. **Migration: ship one SKILL.md per skill, not paired language variants.**

**Source-only:** `metadata.qwenpaw.emoji` is honored at `src/qwenpaw/agents/skills_manager.py:2034,2060`, but undocumented.

**Marketplace sources (officially documented, skills.en.md:170–178, 217–218):**
- `https://skills.sh/...`
- `https://clawhub.ai/...`
- `https://skillsmp.com/...`
- `https://lobehub.com/...` and `https://market.lobehub.com/...`
- `https://github.com/...`
- `https://modelscope.cn/skills/...`

> If GitHub rate-limits, set `GITHUB_TOKEN` in Console → Settings → Environments. (skills.en.md:241)

**Porting implication:** Skill format is the **most stable** surface. Frontmatter = `name` + `description` (+ optional `metadata.requires`). Drop the `-en/-zh` pairing — not a QwenPaw spec.

---

## 3. Plugin spec — official

Source: `website/public/docs/plugins.en.md`, "Plugin Development" (70–260) and "PluginApi Reference" (1037–1075).

**Documented `plugin.json` fields (plugins.en.md:88–101):**

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "author": "Your Name",
  "entry": { "backend": "plugin.py" },
  "dependencies": [],
  "min_version": "0.1.0",
  "meta": {}
}
```

`entry.backend` and `entry.frontend` are both documented (94, 162). Frontend entry must be a JS bundle that uses host-injected `window.QwenPaw.host` (`React`, `antd`, `getApiUrl`, `getApiToken`) — plugins.en.md:244–252.

### Documented PluginApi (plugins.en.md:1037–1075)

- `register_provider(provider_id, provider_class, label, base_url, metadata)`
- `register_startup_hook(hook_name, callback, priority=100)`
- `register_shutdown_hook(hook_name, callback, priority=100)`
- `api.runtime` — accesses `provider_manager` (1102–1111)

### Source-only PluginApi (NOT documented)

Inspecting `src/qwenpaw/plugins/api.py`:

- `register_control_command(handler, priority_level=10)` (api.py:153–174) — **exists, undocumented**, even though slash commands are everywhere in the public docs
- `get_tool_config(tool_name, agent_id)` / `set_tool_config(...)` (api.py:187–217) — undocumented
- Frontend: `window.QwenPaw.registerRoutes`, `registerToolRender`, `window.QwenPaw.modules` — example-only; no schema

> ⚠ "The module structure inside `modules` is not maintained as a public API and may change across versions. Always verify compatibility before use." (plugins.en.md:260)

**Porting implication:** Manifest + the four backend registration calls (`provider`, `startup`, `shutdown`, plus monkey-patching) are stable enough to depend on. **`register_control_command` is semi-private — monkey-patch `AgentRunner.query_handler` instead** (the docs explicitly demonstrate this pattern at plugins.en.md:546–622). Frontend modules: plan to chase changes per release.

---

## 4. Hook surface — official

Source: `website/public/docs/plugins.en.md`, "register_startup_hook" / "register_shutdown_hook" (1053–1075) and "Priority System" (964–986).

**The ONLY public plugin hooks are:**
- **Startup hook** — runs once at app startup
- **Shutdown hook** — runs once at app shutdown

Priority semantics (plugins.en.md:967–986):
> "Lower priority values execute earlier — Priority 0 = Highest priority (executes first), Priority 100 = Default priority, Priority 200 = Low priority (executes last)"

**There is NO documented per-tool-call, per-prompt, pre-reply, or post-reply plugin hook.** The doc explicitly steers developers toward monkey-patching:

> "For plugins that need to modify QwenPaw behavior (like custom commands), you can use monkey patching" (plugins.en.md:1080)

The recommended pattern: patch `qwenpaw.app.runner.runner.AgentRunner.query_handler` (plugins.en.md:1083–1099).

### Source-only: AgentScope-native hook surface (reachable via monkey-patch)

`src/qwenpaw/agents/react_agent.py:446–487` shows QwenPaw internally registers four AgentScope `register_instance_hook` types:

- `pre_reasoning`
- `pre_reply`
- `post_acting`
- `post_reply`

These are **AgentScope** APIs (https://doc.agentscope.io/ → Agent → Hooks). A plugin can reach them only by monkey-patching `QwenPawAgent._register_hooks` or registering on the agent instance directly — neither is part of QwenPaw's public surface.

**Roadmap (`/docs/roadmap`):** No mention of hooks, plugins, or extension surface expansion. (Verified by reading `website/public/docs/roadmap.en.md`.)

**Porting implication:** This is the **single biggest gap** vs. Claude Code. Claude Code plugins routinely use `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`. QwenPaw exposes **none of these to plugins.** The supported workaround is monkey-patching, which is fragile across versions and explicitly flagged: "use with caution to avoid breaking core functionality" (plugins.en.md:1141).

---

## 5. Multi-agent / ACP — official

Two dedicated docs:

### `/docs/multi-agent` (`multi-agent.en.md`)

- Workspace isolation per agent
- Cross-agent collaboration via the **`multi_agent_collaboration` built-in skill** (multi-agent.en.md:259–264)
- CLI: `qwenpaw agents list`, `qwenpaw agents chat`
- REST: `POST /api/agents`, `X-Agent-Id` header on agent-scoped endpoints (multi-agent.en.md:594–627)

> "Multi-Agent Collaboration is a built-in skill that, when enabled, allows your agents to: Request other agents' specialized expertise, Access other agents' workspace data, Seek second opinions or professional reviews, Invoke specific agents when the user explicitly requests them" (multi-agent.en.md:259–264)

### `/docs/acp-integration` (`acp-integration.en.md`)

> "1. **QwenPaw using ACP as a Tool**: QwenPaw connects to external ACP runners and uses them as delegated collaborators. 2. **QwenPaw as an ACP Server**: external clients connect to QwenPaw over ACP" (3–6)

**Built-in runners** (acp-integration.en.md:84–93): `opencode`, `qwen_code`, `claude_code`, `codex`. Custom runners are configured via **Workspace → ACP** with fields `enabled`, `command`, `args`, `env`, `trusted`, `tool_parse_mode`, `stdio_buffer_limit_bytes` (39–55). **No public API for adding runners programmatically — config-only.**

**ACP server side:** documents 10 JSON-RPC methods (`initialize`, `new_session`, `load_session`, `resume_session`, `list_sessions`, `close_session`, `prompt`, `set_session_model`, `set_config_option`, `cancel`) and 4 streaming update types (`agent_message_chunk`, `agent_thought_chunk`, `tool_call`, `tool_call_update`) — acp-integration.en.md:148–173. Spec link: https://github.com/agentclientprotocol/python-sdk

**Porting implication:** Multi-agent is **first-class and stable** — port the production-grade orchestrator's "delegate to specialist" pattern onto `delegate_external_agent` directly. Adding new runners = JSON config; package config and have your installer write to Workspace → ACP.

---

## 6. MCP — official

`/docs/mcp` (`mcp.en.md`) — first-class.

- **Three transports:** `stdio`, `streamable_http`, `sse` (mcp.en.md:165–170)
- **Three JSON formats accepted:** `mcpServers`, direct key-value, single-client (54–101)
- **Full client schema** (172–186)
- **Auto-built-in:** `tavily_search` when `TAVILY_API_KEY` is set (142)
- **Hot-reload** of tool/MCP config without restart (213; config.en.md:319 confirms 2-second poll)

**Porting implication:** MCP is **the** stable, documented way to add external tool servers. If your plugin runs an out-of-process tool, MCP-ify it and ship the JSON config alongside.

---

## 7. Slash commands — official

`/docs/commands` (`commands.en.md`) thoroughly documents:

- **Conversation:** `/compact`, `/new`, `/clear`, `/history`, `/message`, `/compact_str`, `/summarize_status`, `/dump_history`, `/load_history`
- **Skill chat:** `/skills`, `/<skill_name>`, `/<skill_name> <input>`, `/[skill_name]`
- **Models:** `/model`, `/model list`, `/model <provider>:<model>`, `/model reset`, `/model info`
- **System:** `/stop`, `/daemon status|restart|reload-config|version|logs`, `/status`, `/restart`
- **Approval:** `/approval approve|deny|list|cancel`, `/approve`, `/deny`
- **Mission Mode:** `/mission`, `/mission status`, `/mission list` (PRD/worker/verifier pipeline) — 687–891
- **Plan Mode:** `/plan`, `/plan <description>`
- **Proactive Mode:** `/proactive`, `/proactive on|off`, `/proactive <minutes>`

**`register_control_command` is NOT mentioned in any public doc.** It exists in `src/qwenpaw/plugins/api.py:153` and `registry.py:225`, wired via `app/_app.py:362–368`. The handler must be a `BaseControlCommandHandler` (also undocumented).

**Documented path for adding a slash command:** monkey-patch `AgentRunner.query_handler` (plugins.en.md, Example 3 at 488–632).

**Porting implication:** Built-in commands are well-specified. **Don't use `register_control_command`** for portable plugin code — use the doc-recommended monkey-patch pattern.

---

## 8. Configuration — official

`/docs/config` (`config.en.md`) is one of the most thorough pages.

> "From v0.1.0, QwenPaw supports multi-agent. Configuration is split: **Global config (`config.json`)** and **Agent config (`agent.json`)**." (9–12)

**Global `~/.qwenpaw/config.json`** (147–204): `agents.active_agent`, `agents.profiles[id]` (`id`, `name`, `description`, `enabled`, optional `workspace_dir`), `last_api`, `show_tool_details`, `user_timezone`, `last_dispatch`. Backward-compat fields (`channels`, `mcp`, `tools`, `security`) are noted.

**Agent `~/.qwenpaw/workspaces/{id}/agent.json`** (206–565): `channels`, `mcp`, `heartbeat`, `running` (with `light_context_config`, `reme_light_memory_config`, `embedding_model_config`), `language`, `system_prompt_files`, `active_model`, `plan`, `approval_level`, `tools`, `security`, `last_dispatch`.

**Env vars** (84–125):
- **Path:** `QWENPAW_WORKING_DIR`, `QWENPAW_SECRET_DIR`, `QWENPAW_CONFIG_FILE`, `QWENPAW_HEARTBEAT_FILE`, `QWENPAW_JOBS_FILE`, `QWENPAW_CHATS_FILE`, `QWENPAW_TOKEN_USAGE_FILE`
- **Behavior:** `QWENPAW_LOG_LEVEL`, `QWENPAW_MEMORY_COMPACT_*`, `QWENPAW_CONSOLE_STATIC_DIR`
- **Security:** `QWENPAW_AUTH_ENABLED`, `QWENPAW_AUTH_USERNAME/PASSWORD`, `QWENPAW_TOOL_GUARD_ENABLED`, `QWENPAW_SKILL_SCAN_MODE`
- **Memory:** `FTS_ENABLED`, `MEMORY_STORE_BACKEND`, fallback `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL_NAME`

**Secrets:** `~/.qwenpaw.secret/providers.json` (default), `~/.qwenpaw.secret/envs.json` — clean split from working dir (44–47, 203–204).

> "Config changes are auto-reloaded without restart (polled every 2 seconds)." (config.en.md:706)

**ACP doc note:** legacy fallback dir is `~/.copaw` (acp-integration.en.md:202) — be aware on older installs.

**Porting implication:** Config shape is **second-most-documented** (after skills). Ship config as JSON patches, not CLI commands. Hot-reload means changes take effect within 2 seconds.

---

## 9. AgentScope upstream

QwenPaw is built on AgentScope and AgentScope Runtime (intro.en.md:29–31).

- `QwenPawAgent(ToolGuardMixin, ReActAgent)` (`src/qwenpaw/agents/react_agent.py:80`)
- Runner extends `agentscope_runtime.engine.runner.Runner` (`app/runner/runner.py:13`)
- FastAPI app inherits `agentscope_runtime.engine.app.AgentApp` (`_app.py:17`)
- Schemas: `AgentRequest`, `Message`, exceptions imported from `agentscope_runtime.engine.schemas`

**AgentScope upstream docs (`https://doc.agentscope.io/`):** sections include Tutorial, Workflow, Model and Context (Memory, Long-Term Memory), Tool (MCP, Agent Skill), **Agent (Hooks, Agent-to-Agent)**, Features.

### AgentScope hooks accessible via monkey-patch

`src/qwenpaw/agents/react_agent.py:446–487` registers:

- `pre_reasoning`
- `pre_reply`
- `post_acting`
- `post_reply`

via `self.register_instance_hook(hook_type, hook_name, hook)`. **This is the only path** to fine-grained per-prompt / per-tool intercepts in QwenPaw — but it's an upstream API outside QwenPaw's public surface. Requires version pinning of `agentscope` and `agentscope-runtime` in `pyproject.toml`.

### Toolkit / ReActAgent / Memory upstream

Not redocumented in QwenPaw. For Toolkit, ReActAgent reasoning loop, and `ReMe` memory backends (https://github.com/agentscope-ai/ReMe), consult AgentScope upstream and the ReMe repo.

**Porting implication:** A plugin willing to dig into AgentScope can register **per-turn hooks** by monkey-patching `QwenPawAgent`. This is the **only** path to per-prompt / per-tool intercepts. Pin `agentscope` and `agentscope-runtime` exactly.

---

## 10. Versioning & Stability

- **Active version:** `1.1.6b1` (beta) — `src/qwenpaw/__version__.py`. Declared dynamic in `pyproject.toml:51`.
- **No top-level `CHANGELOG.md`.** Release notes are per-version markdown under `website/public/release-notes/` (range: `v0.0.4` … `v1.1.5`), with sections "Added / Changed / Performance / Fixed". They read like changelogs, not breaking-change ledgers.

**Stability markers (grep `experimental|stable|beta|breaking` in plugins/skills docs):**
- Skills doc: AI-Optimize is **beta** (skills.en.md:157)
- Plugins doc: `window.QwenPaw.modules` flagged unstable (plugins.en.md:260); FAQ ack: "use with caution to avoid breaking core functionality" (1141)
- Config doc: hot-reload called out as stable (config.en.md:319)
- ACP doc: defaults ("trusted", `tool_parse_mode`) are implicitly stable (acp-integration.en.md:53)
- Roadmap: hooks/plugins/skills NOT mentioned in "In Progress / Planned" — implies no near-term breaking changes, but no explicit commitment

**Confirmed historical breaking changes:**
- v0.1.0 introduced multi-agent + the `~/.qwenpaw/workspaces/{id}/` layout. Automatic migration documented (multi-agent.en.md:230–248). Legacy fallback dir is `.copaw` — earlier brand rename.
- Skills doc dedicates "Upgrading from Earlier Versions" to the move from `active_skills/` + `customized_skills/` to a unified `skills/` (skills.en.md:400–420).

**Porting implication:** Pin `qwenpaw>=1.1.5,<1.2`. Watch per-release pages — there's no consolidated breaking-change ledger.

---

## Net assessment for the migration

| Surface | Doc | Stability | Recommendation |
|---|---|---|---|
| Skill (`SKILL.md`) | High | High | ✅ Direct port; `name`+`description`+optional `metadata.requires`; **no `-en/-zh`** |
| Plugin manifest (`plugin.json`) | High | High | ✅ Direct port; both `entry.backend` and `entry.frontend` documented |
| `register_provider` / startup / shutdown hooks | High | High | ✅ Safe |
| `register_control_command` | None (source-only) | Unknown | ⚠️ Avoid; monkey-patch `AgentRunner.query_handler` instead |
| Frontend `registerRoutes`/`registerToolRender` | Examples only | Medium | ⚠️ Use; expect minor tweaks per release |
| `window.QwenPaw.modules` | Explicit warning | **Unstable** | ❌ Last resort; pin tightly |
| Per-tool / per-prompt hooks | None (need AgentScope `register_instance_hook` via monkey-patch) | Unstable | ❌ Reach for it only when essential |
| MCP config | High | High | ✅ Ship JSON config |
| ACP delegation | High | High | ✅ Configure runners via UI/JSON |
| Slash command behavior | High | High | ✅ Document for users; avoid registering new ones programmatically |
| `config.json` / `agent.json` schemas | High | High | ✅ Write and hot-reload |
| Env vars | High | High | ✅ Safe to depend on |
| AgentScope underpinnings (Toolkit, ReActAgent, hooks, memory) | External | Pinned via deps | ⚠️ Pin exact versions |

**Largest single risk:** the per-prompt / per-tool hook gap. Claude Code's plugin model exposes those; QwenPaw does not. Official escape: monkey-patch (which the docs both demonstrate and warn about).
