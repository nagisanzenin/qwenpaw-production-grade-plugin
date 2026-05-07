# QwenPaw Extension Surface — Complete Mapping

> Source: deep exploration of `/Users/quanduong/Documents/Github/QwenPaw/` (commit at clone time, May 2026). Version 1.1.5+, AgentScope base 1.0.19.post1, AgentScope Runtime 1.1.4.

## Executive Summary

QwenPaw is a Python-based multi-agent assistant built on AgentScope. It has a **real plugin architecture** (Python entry-point plugins + JSON manifests), a **SKILL.md system** very similar to Claude Code's, **lifecycle hooks** (startup/shutdown via PluginApi, plus a built-in BootstrapHook), **multi-agent delegation via ACP**, **MCP support**, and **slash + CLI commands**.

Critically: **skills in QwenPaw are passive instructional documents** read by the agent, not a tool the agent invokes. Claude Code's `Skill` tool model (agent dynamically invokes a skill) does NOT exist as such — but the SKILL.md format is nearly identical.

---

## 1. Top-level Layout

- **CLI entry**: `qwenpaw` (and legacy alias `copaw`) → `qwenpaw.cli.main:cli` (`pyproject.toml:73-75`)
- **Web console**: React/Vite at `website/`, served on port 8088 (default)
- **FastAPI backend**: `src/qwenpaw/app/` — REST routers for agents, chats, skills, providers, channels, MCP, settings
- **Docker**: `docker-compose.yml`, `deploy/`
- **Optional desktop**: pywebview (≥4.0) integration

## 2. Skill System (primary extension surface)

- **Format**: each skill = directory with a `SKILL.md` file (YAML frontmatter + markdown body). Mirrors Claude Code's skill model very closely.
- **Frontmatter fields observed**:
  ```yaml
  ---
  name: cron
  description: Use this skill only for scheduled or recurring tasks
  metadata:
    builtin_skill_version: "1.4"
    qwenpaw:
      emoji: "⏰"
  ---
  ```
- **Built-in location**: `src/qwenpaw/agents/skills/` (37 variants; `-en` and `-zh` paired)
- **Workspace location**: `~/.qwenpaw/{agent_id}/skills/`
- **Skill pool**: `~/.qwenpaw/skill_pool/` (shared across agents)
- **Manifest**: `~/.qwenpaw/{agent_id}/skill.json` — schema `workspace-skill-manifest.v1`, with per-channel routing matrix and per-skill enable flags
- **Loader**: `src/qwenpaw/agents/skills_manager.py` (`_iter_packaged_builtin_dirs`, `ensure_skills_initialized`, `resolve_effective_skills`)
- **Language preference**: `settings.json → builtin_skill_language: "en" | "zh"`
- **CLI**: `qwenpaw skills list|enable|disable|add|remove|install|uninstall` (`src/qwenpaw/cli/skills_cmd.py`)
- **Built-in skills (sample)**: `cron`, `pdf`, `xlsx`, `pptx`, `docx`, `browser_visible`, `browser_cdp`, `news`, `guidance`, `file_reader`, `chat_with_agent`, `multi_agent_collaboration`, `make_plan`, `himalaya`, `channel_message`, `dingtalk_channel`, `QA_source_index` (each in `-en` and `-zh`)

### Difference from Claude Code

| | QwenPaw | Claude Code |
|--|--|--|
| Language | en/zh paired dirs | single file |
| Activation | passive (loaded into context) | tool-invoked (`Skill` tool) |
| Routing | per-channel matrix | global enable/disable |
| Allowed-tools | NOT in frontmatter (use plugin tool config instead) | `allowed-tools:` in frontmatter |
| Sub-files | not standardized | referenced from SKILL.md body |

## 3. Plugin System (active extension)

Plugins are Python modules that **register** providers / tools / hooks / commands at runtime.

- **Manifest** (`plugin.json`): id, name, version, description, author, `entry.backend` (e.g., `plugin.py`), optional `entry.frontend` (`frontend/index.tsx`), `dependencies`, `min_version`, `meta.config_fields` (UI form spec)
- **Entry-point class**: must export `plugin = MyClass()` and have `register(api: PluginApi)`
- **Discovery**: `PluginLoader.discover_plugins()` scans `plugins/` for `plugin.json`
- **Loader**: `src/qwenpaw/plugins/loader.py` — `importlib.util` based
- **Registry singleton**: `src/qwenpaw/plugins/registry.py`
- **PluginApi** (`src/qwenpaw/plugins/api.py`):
  - `register_provider(provider_id, provider_class, label, base_url, **metadata)` — LLM provider
  - `register_startup_hook(hook_name, callback, priority=100)` — lower priority runs earlier
  - `register_shutdown_hook(hook_name, callback, priority=100)`
  - `register_control_command(handler, priority_level=10)` — extends slash-command surface
  - `get_tool_config(tool_name, agent_id)` / `set_tool_config(...)`
- **CLI**: `qwenpaw plugin install|uninstall|list|info`
- **Example**: `plugins/tool/gpt-image2/` (manifest + `plugin.py` + `tool.py`)
- **Future**: `pyproject.toml` reserves `[project.entry-points."qwenpaw.doctor"]` for setuptools-style discovery (commented)

### Plugin lifecycle (canonical flow)

1. App starts → `PluginLoader.load_all_plugins(configs=...)`
2. For each `plugin.json` found → load module → instantiate → `register(api)`
3. Plugin calls `api.register_startup_hook(...)` (priority-sorted)
4. After all plugins registered, hooks fire in priority order
5. App ready; tools / providers / commands available
6. App shutdown → shutdown hooks fire (priority-sorted, reversed)

## 4. Tool System

- **Built-in tools registered in `src/qwenpaw/agents/react_agent.py:_create_toolkit()` (~line 217)**:
  `execute_shell_command`, `read_file`, `write_file`, `edit_file`, `grep_search`, `glob_search`, `browser_use`, `desktop_screenshot`, `view_image`, `view_video`, `send_file_to_user`, `get_current_time`, `set_user_timezone`, `get_token_usage`, `delegate_external_agent`, `list_agents`, `chat_with_agent`, `submit_to_agent`, `check_agent_task`
- **Per-agent tool config**: `~/.qwenpaw/{agent_id}/agent.json → tools.builtin_tools.<name>.{enabled, async_execution, config{...}}`
- **Tool Guard** (`src/qwenpaw/agents/tool_guard_mixin.py`, ~26 KB): mixin that intercepts `_acting`/`_reasoning` and applies per-tool approval gates and validation
- **Namesake strategy** when registering: `override`, `skip`, `raise`, `rename` (default `skip`)

## 5. Hook System (lifecycle)

Two distinct hook surfaces:

### a. Plugin lifecycle hooks (via PluginApi)

```python
api.register_startup_hook(hook_name="init_sdk", callback=fn, priority=0)
api.register_shutdown_hook(hook_name="cleanup_sdk", callback=fn, priority=100)
```

- Priority-sorted (lower runs earlier)
- Fired at app startup / shutdown
- NOT per-prompt or per-tool-call — these are app-lifecycle only

### b. Built-in agent-loop hooks

Found in `src/qwenpaw/agents/hooks/`:

- **BootstrapHook** (`bootstrap.py`): on first user interaction, prepends `BOOTSTRAP.md` guidance; one-shot (uses `.bootstrap_completed` flag in workspace)

> ⚠ **Gap vs Claude Code**: There is **no per-prompt / per-tool-call event hook surface** documented in QwenPaw equivalent to Claude Code's `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`. AgentScope's hook system likely exposes some of these internally, but they are not surfaced via plugin API at this version.

## 6. Slash Commands

### a. In-chat system commands (handled by `command_handler.py`)

```
/compact [instruction]   /new   /clear   /history
/compact_str   /summarize_status   /message TEXT
/dump_history   /load_history   /proactive   /plan [description]
```

`SYSTEM_COMMANDS = frozenset({...})` in `src/qwenpaw/agents/command_handler.py:38-52`. Detected by `is_conversation_command(query)`.

### b. Plugin-registered control commands

Via `api.register_control_command(handler, priority_level=10)` — adds new handlers to the conversation command surface. This is the extension hook for adding custom slash commands.

### c. CLI commands (Click-based, `src/qwenpaw/cli/`)

`init`, `app`, `agents`, `skills`, `plugin`, `cron`, `provider`, `channel`, `doctor`, `update`

## 7. Multi-Agent / Sub-Agent

QwenPaw's primary mechanism = **ACP (Agent Communication Protocol)** for talking to **external** agent processes:

- **Default ACP runners** (`src/qwenpaw/agents/acp/config.py:70-101`):
  - `opencode` (`opencode acp`)
  - `qwen_code` (`qwen --acp`)
  - `claude_code` (`npx @zed-industries/claude-agent-acp`)
  - `codex` (`npx @zed-industries/codex-acp`)
- **Tool**: `delegate_external_agent(action, runner, message, cwd, max_runtime)` — actions: `start`, `message`, `respond`, `close`. Streaming via async generator. Permission gates via ACP turn pause.
- **Inter-agent chat (peer)**: `chat_with_agent`, `submit_to_agent`, `check_agent_task` for talking to other QwenPaw agents in the same workspace

> Claude Code's "subagent" / `Agent` tool with built-in agent types maps to QwenPaw's `delegate_external_agent` to a specific ACP runner. **There is no in-process subagent** primitive (everything is a subprocess).

## 8. MCP Support

Full first-class support:

- **Config**: `MCPClientConfig` (`src/qwenpaw/config/config.py`); transports: `stdio`, `streamable_http`, `sse`
- **API endpoints** (`src/qwenpaw/app/routers/mcp.py`): `GET/POST/PUT/DELETE /mcp/clients{/key}`, `POST /mcp/clients/{key}/test`
- **Injection**: clients passed to `react_agent.__init__(..., mcp_clients=...)`; tools auto-registered into toolkit
- Env/header masking for sensitive fields

## 9. Configuration

Layout under `~/.qwenpaw/`:

```
config.json                 # global
agents/{agent_id}/
  agent.json                # per-agent (active model, tools, channels, ACP, memory)
  skills/<skill>/SKILL.md   # workspace skills
  skill.json                # skill manifest
  .bootstrap_completed      # bootstrap one-shot flag
skill_pool/skill.json       # shared pool manifest
settings.json               # global UI settings (language, theme, builtin_skill_language)
```

Env vars (prefix `QWENPAW_`, legacy `COPAW_`):
`QWENPAW_WORKING_DIR`, `QWENPAW_SECRET_DIR`, `QWENPAW_CONFIG_FILE`, `QWENPAW_LOG_LEVEL`, `QWENPAW_OPENAPI_DOCS`, `QWENPAW_RUNNING_IN_CONTAINER`, `QWENPAW_MODEL_PROVIDER_CHECK_TIMEOUT`.

## 10. Security

- **Tool Guard** mixin — pre-execution validation, per-tool approval gates
- **Skill Scanner** (`src/qwenpaw/security/skill_scanner/`) — rules-based scan of skills on load
- **File access**: workspace-relative validation, symlink/zip-slip prevention in plugin downloads
- **Channel policies**: `dm_policy`, `group_policy`, `allow_from` lists

## 11. Comparison Matrix (high level)

| Feature | Claude Code | QwenPaw | Direct port? |
|---|---|---|---|
| Skill (markdown + frontmatter) | YES | YES | ✅ direct (need en/zh + drop `allowed-tools` field) |
| `Skill` tool (dynamic invocation) | YES | NO (passive load) | ❌ pattern shift |
| Plugin manifest (`.claude-plugin/plugin.json`) | JSON-only | `plugin.json` + Python entry | ⚠️ need a Python wrapper |
| Plugin marketplace | YES (registries.json + cache) | install via `qwenpaw plugin install <src>` | ⚠️ different |
| Hook events (SessionStart, PreToolUse, …) | YES (settings.json) | NO equivalent surface | ❌ likely needs custom code or upstream PR |
| Startup/shutdown hooks | NO direct equivalent | YES (PluginApi) | ✅ |
| Slash commands | markdown files in `.claude/commands/` | `/system`-handler + `register_control_command` | ⚠️ rewrite |
| Sub-agents (in-process, named) | YES (`Agent(subagent_type=...)`) | only ACP external runners + peer chat | ⚠️ pattern shift |
| MCP servers | YES | YES | ✅ |
| Background tasks | YES (run_in_background) | unclear (delegation streaming exists) | ⚠️ |
| Auto-memory MEMORY.md | optional, harness-managed | ReMeLight (different) | ⚠️ |
| Tool permission/approvals | settings.json + harness | Tool Guard + per-tool config | ⚠️ |

---

## File manifest (for migration reference)

| Path | Purpose |
|---|---|
| `src/qwenpaw/agents/skills_manager.py` | skill loader / manifest |
| `src/qwenpaw/plugins/api.py` | PluginApi |
| `src/qwenpaw/plugins/registry.py` | central singleton |
| `src/qwenpaw/plugins/loader.py` | discovery + load |
| `src/qwenpaw/plugins/architecture.py` | manifest dataclasses |
| `src/qwenpaw/agents/react_agent.py` | toolkit init |
| `src/qwenpaw/agents/command_handler.py` | system commands |
| `src/qwenpaw/agents/hooks/bootstrap.py` | bootstrap hook |
| `src/qwenpaw/agents/tools/delegate_external_agent.py` | ACP delegation |
| `src/qwenpaw/config/config.py` | config schemas |
| `src/qwenpaw/cli/plugin_commands.py` | `qwenpaw plugin ...` |
| `src/qwenpaw/cli/skills_cmd.py` | `qwenpaw skills ...` |
| `plugins/tool/gpt-image2/` | reference plugin (manifest + entry + tool) |
