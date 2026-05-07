# Claude Code Extension Surface — Authoritative Reference

> Pulled from the official docs at `https://code.claude.com/docs/en/...` (the older `docs.claude.com/en/docs/claude-code/...` URLs 301-redirect there). All facts verified against official pages on 2026-05-07. Subset relevant for porting `production-grade` to QwenPaw.

---

## 1. Skills (`SKILL.md`)

Source: https://code.claude.com/docs/en/skills

### Layout

A skill is a **directory** whose entrypoint is `SKILL.md` (capitalized). Other files in the directory are optional supporting material that Claude reads on demand (templates, scripts, reference docs).

```
my-skill/
├── SKILL.md           # required
├── reference.md       # optional, loaded on demand
└── scripts/helper.py  # optional, executed not loaded
```

### Locations & precedence (highest → lowest)

| Scope | Path | Notes |
|---|---|---|
| Enterprise (managed) | platform-specific managed-settings dir | Cannot be overridden |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Namespaced as `plugin-name:skill-name` |
| `--add-dir` | `<added>/.claude/skills/` | Only `.claude/skills/` is loaded from added dirs |

A skill in `.claude/commands/<name>.md` (flat-file legacy form) creates the same `/<name>` command. **Skills take precedence over commands of the same name**. Live change detection: editing files under existing skill dirs takes effect immediately; **creating a brand-new top-level `skills/` dir requires a restart**.

### `SKILL.md` frontmatter (YAML between `---`)

All fields are **optional**. Only `description` is recommended.

| Field | Type | Behavior |
|---|---|---|
| `name` | string | Display name. Defaults to directory name. **Lowercase letters, numbers, hyphens only. Max 64 chars.** |
| `description` | string | What the skill does + when to use it. Combined with `when_to_use`, **truncated at 1,536 chars** in the skill listing. |
| `when_to_use` | string | Appended to `description` for matching. Same 1,536-char cap. |
| `argument-hint` | string | Autocomplete hint, e.g. `[issue-number]`. |
| `arguments` | string \| YAML list | Named positional arguments (maps `$name` substitutions to positions). |
| `disable-model-invocation` | bool | If `true`, Claude cannot auto-invoke; only the user can run `/<name>`. Also blocks preloading into subagents. |
| `user-invocable` | bool | If `false`, hidden from `/` menu (Claude can still invoke). |
| `allowed-tools` | string \| list | Pre-approves these tools while the skill is active; doesn't restrict the toolset. |
| `model` | string | `sonnet` \| `opus` \| `haiku` \| full ID like `claude-opus-4-7` \| `inherit`. |
| `effort` | string | `low` \| `medium` \| `high` \| `xhigh` \| `max`. |
| `context` | string | Set to `fork` to run in a forked subagent context. |
| `agent` | string | Subagent type when `context: fork`. |
| `hooks` | object | Hooks scoped to this skill's lifecycle. |
| `paths` | string \| list | Glob patterns; auto-activate only when working with matching files. |
| `shell` | string | `bash` (default) or `powershell` for `` !`...` `` blocks. |

### Body conventions

- Markdown body **becomes the skill content injected as a single user message** when invoked. It stays in context for the rest of the session — **Claude does not re-read SKILL.md on later turns**.
- Auto-compaction re-attaches the most recent invocation of each skill, keeping the **first 5,000 tokens of each**, with a **combined budget of 25,000 tokens**.
- Keep `SKILL.md` under ~500 lines; move large reference into sibling files.

### Substitutions in body

| Placeholder | Meaning |
|---|---|
| `$ARGUMENTS` | Full argument string |
| `$ARGUMENTS[N]` / `$N` | 0-indexed positional argument |
| `$<name>` | Named argument from `arguments:` list |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_EFFORT}` | Active effort level |
| `${CLAUDE_SKILL_DIR}` | Absolute path to this skill's directory |

If user passes args but body has no `$ARGUMENTS`, Claude Code appends `ARGUMENTS: <input>` automatically.

### Dynamic context injection

- `` !`<command>` `` inline form runs shell **before the body is sent to the model**; output replaces the placeholder.
- Multi-line: fenced block opened with ` ```! `.
- Disabled per-source by `"disableSkillShellExecution": true` in settings.

### Runtime invocation (the `Skill` tool)

- The agent calls a `Skill` tool with the skill's `name`. Permission syntax: `Skill(name)` exact, `Skill(name *)` prefix-with-args.
- A few built-in commands route through Skill tool: `/init`, `/review`, `/security-review`. Most other built-ins (e.g. `/compact`) are not.

---

## 2. Hooks

Source: https://code.claude.com/docs/en/hooks

### Hook events (full list — ~29 events)

| Event | When it fires | Matcher |
|---|---|---|
| `SessionStart` | Session starts/resumes | `startup` \| `resume` \| `clear` \| `compact` |
| `Setup` | `--init-only`, `claude -p --init`, `--maintenance` | `init` \| `maintenance` |
| `InstructionsLoaded` | A `CLAUDE.md`/`.claude/rules/*.md` is loaded | `session_start` \| `nested_traversal` \| `path_glob_match` \| `include` \| `compact` |
| `UserPromptSubmit` | User submits prompt, before model sees it | none |
| `UserPromptExpansion` | Slash command/skill expands into a prompt | command name |
| `PreToolUse` | After tool args produced, before execution | tool name (regex if non-alphanumeric) |
| `PermissionRequest` | Permission dialog about to show | tool name |
| `PermissionDenied` | Auto mode classifier denied a tool call | tool name |
| `PostToolUse` | Tool call succeeded | tool name |
| `PostToolUseFailure` | Tool call failed | tool name |
| `PostToolBatch` | Batch of parallel tool calls resolved | none |
| `Notification` | Claude Code sends a notification | several types |
| `SubagentStart` | Subagent spawned | agent type |
| `SubagentStop` | Subagent finished | agent type |
| `TaskCreated` | `TaskCreate` ran | none |
| `TaskCompleted` | Task marked complete | none |
| `Stop` | Claude finished responding | none |
| `StopFailure` | Turn ended due to API error | error type |
| `TeammateIdle` | Teammate going idle | none |
| `ConfigChange` | Settings changed mid-session | source |
| `CwdChanged` | Working directory changed | none |
| `FileChanged` | Watched file changed on disk | literal filename(s) joined by `\|` |
| `PreCompact` / `PostCompact` | Before/after compaction | `manual` \| `auto` |
| `Elicitation` / `ElicitationResult` | MCP elicitation flow | MCP server name |
| `WorktreeCreate` / `WorktreeRemove` | Subagent worktree lifecycle | none |
| `SessionEnd` | Session terminating | several reasons |

### Stdin JSON shape (universal fields)

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "permission_mode": "default|plan|acceptEdits|auto|dontAsk|bypassPermissions",
  "hook_event_name": "PreToolUse",
  "agent_id": "...",
  "agent_type": "..."
}
```

Plus event-specific: `tool_name`, `tool_input`, `tool_use_id`, `tool_result` (Post*), `prompt` (UserPromptSubmit), etc.

### Exit code semantics

- `0` = success (stdout parsed as JSON if valid)
- `2` = **blocking error** (action blocked, stderr shown)
- Other = non-blocking error

### JSON output schema (universal envelope)

```json
{
  "continue": true,
  "stopReason": "...",
  "systemMessage": "...",
  "suppressOutput": false,
  "decision": "block",
  "reason": "...",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "..."
  }
}
```

`PreToolUse` uses `hookSpecificOutput.permissionDecision`: `allow` | `deny` | `ask` | `defer`.

### Hook configuration

| Location | Scope |
|---|---|
| `~/.claude/settings.json` | User |
| `.claude/settings.json` | Project, git-shared |
| `.claude/settings.local.json` | Project, gitignored |
| Plugin `hooks/hooks.json` | Plugin |
| Skill/Agent YAML `hooks:` frontmatter | Component lifetime |
| Managed policy settings | Org-wide |

### Hook entry shape

```jsonc
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write|mcp__memory__.*",
        "hooks": [
          {
            "type": "command|http|mcp_tool|prompt|agent",
            "command": "...",
            "if": "Bash(git *)|Edit(*.ts)",
            "timeout": 600,
            "async": false
          }
        ]
      }
    ]
  }
}
```

---

## 3. Sub-agents / Agent tool

Source: https://code.claude.com/docs/en/sub-agents

### Definition

A subagent = **Markdown file with YAML frontmatter** plus a body that becomes the **system prompt** (replaces the default Claude Code system prompt for that subagent).

### Locations & precedence

| Location | Scope |
|---|---|
| Managed settings dir | Org |
| `--agents '<JSON>'` CLI flag | Session |
| `.claude/agents/<name>.md` | Project |
| `~/.claude/agents/<name>.md` | User |
| `<plugin>/agents/<name>.md` | Plugin |

### Frontmatter

`name` and `description` required.

| Field | Description |
|---|---|
| `name` | Lowercase letters + hyphens only |
| `description` | Drives auto-invocation |
| `tools` | Allowlist (omit = all) |
| `disallowedTools` | Denylist |
| `model` | `sonnet` \| `opus` \| `haiku` \| `inherit` |
| `permissionMode` | **Ignored for plugin subagents** |
| `maxTurns` | Cap on agentic turns |
| `skills` | List to **preload** (full content injected at startup); subagents do NOT inherit parent skills |
| `mcpServers` | **Ignored for plugin subagents** |
| `hooks` | **Ignored for plugin subagents** |
| `memory` | `user` \| `project` \| `local` |
| `background` | Always run as background |
| `effort`, `isolation`, `color`, `initialPrompt` | … |

### Spawning

- `Agent` tool (renamed from `Task` in v2.1.63; `Task(...)` still works as alias) spawns subagents.
- Plugin agents addressed as `@agent-<plugin>:<agent>`.
- **Subagents cannot spawn other subagents.**
- Foreground/background; `Ctrl+B` backgrounds; disable with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`.

### `SendMessage` (resume) semantics

- New invocation = fresh context.
- `SendMessage` (gated by `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) takes `to: agentId`, resumes with full transcript.

### Migration-relevant facts

1. **Subagent file is system-prompt-replacement**, not prefix.
2. **Tool field is allowlist, `disallowedTools` is denylist** — denylist runs first.
3. **Plugin subagents lose `hooks`/`mcpServers`/`permissionMode`** by design.
4. **`memory` scope creates real disk dirs** the subagent uses Read/Write/Edit on.

---

## 4. Slash commands

Sources: https://code.claude.com/docs/en/skills + https://code.claude.com/docs/en/commands

**Custom commands have been merged into skills.** A file at `.claude/commands/<name>.md` and a skill at `.claude/skills/<name>/SKILL.md` both create `/<name>` and use **the same frontmatter**. If both exist, the skill wins.

### Namespacing

- User/project: bare name (`/deploy`).
- **Plugin: always namespaced**: `/<plugin-name>:<command-name>`.
- MCP-exposed prompts: `/mcp__<server>__<prompt>`.

### Built-in commands (highlights)

`/add-dir`, `/agents`, `/clear`, `/compact`, `/config`, `/context`, `/diff`, `/doctor`, `/effort`, `/exit`, `/help`, `/hooks`, `/init`, `/login`, `/mcp`, `/memory`, `/model`, `/permissions`, `/plan`, `/plugin`, `/recap`, `/rewind`, `/sandbox`, `/security-review`, `/skills`, `/status`, `/statusline`, `/tasks`, `/theme`, `/tui`, `/usage`, `/voice`.

### Bundled skills

`/batch`, `/claude-api`, `/debug`, `/fewer-permission-prompts`, `/loop`, `/simplify`, `/init`, `/review`, `/security-review`.

---

## 5. Plugins & marketplaces

Sources: https://code.claude.com/docs/en/plugins, https://code.claude.com/docs/en/plugins-reference, https://code.claude.com/docs/en/plugin-marketplaces

### Plugin directory layout

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json        # ONLY plugin.json goes inside
├── skills/<name>/SKILL.md
├── commands/<name>.md
├── agents/<name>.md
├── hooks/hooks.json
├── .mcp.json
├── .lsp.json
├── monitors/monitors.json
├── bin/                   # added to Bash PATH while plugin enabled
├── settings.json          # only `agent` and `subagentStatusLine` honored
└── themes/                # experimental
```

### `plugin.json` schema

Only `name` is strictly required.

```jsonc
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "...",
  "author": { "name": "...", "email": "..." },
  "homepage": "...",
  "repository": "...",
  "license": "MIT",
  "keywords": ["..."],

  "skills":   "./custom/skills/",
  "commands": ["./custom/cmd.md"],
  "agents":   ["./custom/agents/x.md"],
  "hooks":    "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json",

  "experimental": {
    "themes":   "./themes/",
    "monitors": "./monitors.json"
  },

  "userConfig": {
    "api_token": {
      "type": "string|number|boolean|directory|file",
      "title": "...",
      "sensitive": true,
      "required": false,
      "default": "..."
    }
  },

  "channels": [{ "server": "telegram", "userConfig": { /* */ } }],
  "dependencies": [{ "name": "secrets-vault", "version": "~2.1.0" }]
}
```

### Plugin env vars

- `${CLAUDE_PLUGIN_ROOT}` — install dir (changes on update)
- `${CLAUDE_PLUGIN_DATA}` — `~/.claude/plugins/data/<id>/` (persistent)

### `marketplace.json`

File: `<repo>/.claude-plugin/marketplace.json`. Lists plugins with `source` field that's polymorphic:

| `source` | Required |
|---|---|
| `"./relative/path"` | (string) |
| `{ "source": "github", "repo": "owner/repo", "ref"?, "sha"? }` | `repo` |
| `{ "source": "url", "url": "https://...", "ref"?, "sha"? }` | `url` |
| `{ "source": "git-subdir", "url", "path" }` | `url`, `path` |
| `{ "source": "npm", "package", "version"?, "registry"? }` | `package` |

### Install flow

`/plugin marketplace add <repo>` → `/plugin install <name>@<marketplace>` → `/plugin enable|disable|update|uninstall`.

---

## 6. Settings

Source: https://code.claude.com/docs/en/settings

### Precedence (highest → lowest)

1. Managed policy
2. CLI args
3. `.claude/settings.local.json` (gitignored)
4. `.claude/settings.json` (git)
5. `~/.claude/settings.json`

**Array-valued settings concatenate and dedupe** across scopes.

### Key sections

```jsonc
{
  "permissions": {
    "allow": ["Bash(npm run *)"],
    "ask":   ["Bash(git push *)"],
    "deny":  ["Read(./.env)"],
    "defaultMode": "default|plan|acceptEdits|auto|dontAsk|bypassPermissions",
    "additionalDirectories": [".."]
  },
  "env": { "FOO": "bar" },
  "model": "claude-sonnet-4-6",
  "hooks": { /* per §2 */ },
  "enabledPlugins": { "formatter@acme-tools": true },
  "extraKnownMarketplaces": { "acme-tools": { /* */ } },
  "autoMemoryEnabled": true,
  "autoMemoryDirectory": "~/my-memory-dir",
  "allowedMcpServers": [{ "serverName": "github" }],
  "deniedMcpServers":  [{ "serverName": "filesystem" }],
  "skillOverrides": { "deploy": "off" },
  "agent": "code-reviewer",
  "disableAllHooks": false,
  "disableSkillShellExecution": false
}
```

---

## 7. MCP

Source: https://code.claude.com/docs/en/mcp

### Adding servers

```bash
claude mcp add --transport http  <name> <url>
claude mcp add --transport sse   <name> <url>     # deprecated
claude mcp add --transport stdio <name> -- <command> [args]
claude mcp add-json <name> '{"type":"http","url":"..."}'
```

### Scopes (high → low)

1. Local (default) → `~/.claude.json` under `projects.<cwd>.mcpServers`
2. Project → `.mcp.json` at project root
3. User → `~/.claude.json` top-level
4. Plugin
5. Claude.ai connectors

### `.mcp.json` (project)

```jsonc
{
  "mcpServers": {
    "my-server": {
      "type": "stdio|http|sse|ws",
      "command": "...", "args": ["..."],
      "env": { "KEY": "${VAR}" },
      "url": "...", "headers": {},
      "headersHelper": "/path/to/script",
      "alwaysLoad": true,
      "oauth": { /* */ }
    }
  }
}
```

### Tool naming

`mcp__<server>__<tool>` — e.g., `mcp__memory__create_entities`.

---

## 8. Memory

Source: https://code.claude.com/docs/en/memory

### Two systems

| | CLAUDE.md | Auto memory |
|---|---|---|
| Author | You | Claude |
| Loaded | Every session (full content) | Every session (first 200 lines / 25 KB of `MEMORY.md`) |

### CLAUDE.md location resolution

| Scope | Path |
|---|---|
| Managed | `/Library/Application Support/ClaudeCode/CLAUDE.md` etc. |
| Project | `./CLAUDE.md` or `./.claude/CLAUDE.md` |
| Local | `./CLAUDE.local.md` |
| User | `~/.claude/CLAUDE.md` |

### Loading rules

- Walks up from cwd to root; concatenates each level.
- Order: root → cwd (cwd-level instructions arrive last).
- Subdirectory CLAUDE.md files are **lazy-loaded** when Claude reads files in that subdir.
- Imports: `@path/to/file.md` (max 5 hops).

### Auto memory

- Stored at `~/.claude/projects/<git-repo>/memory/`.
- Files: `MEMORY.md` (index, ≤ 200 lines / 25 KB) + topic files.
- Toggle: `autoMemoryEnabled` setting or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.

---

## Cross-cutting facts for QwenPaw porting

1. **The doc base has moved**: `docs.claude.com/en/docs/claude-code/*` 301-redirects to `code.claude.com/docs/en/*`.
2. **`Skill`, `Agent`, `SendMessage`, `ToolSearch`, `AskUserQuestion`, `ExitPlanMode`** are the meta-tools the runtime injects beyond the obvious file-IO/Bash set.
3. **`Task` was renamed to `Agent` in v2.1.63**; both still work.
4. **The Skill tool routes both user-authored skills and a small set of built-in commands** (`/init`, `/review`, `/security-review`).
5. **Plugin namespacing is structural, not cosmetic**: `<plugin>:<component>` is how the runtime disambiguates and how permission rules and `@`-mentions reference plugin components.
