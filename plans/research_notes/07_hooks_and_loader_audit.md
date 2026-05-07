# AgentScope Hooks + Skill Loader Patching — Feasibility Audit

> Verifies whether a plugin can reach Claude Code's hook depth and SKILL.md preprocessing capability **without modifying QwenPaw source**.

## Stability tiers used here

- **TIER-1 (official-doc):** documented in QwenPaw user docs.
- **TIER-2 (example-only):** referenced in code/example, not user docs.
- **TIER-3 (source-only):** internal name imported by other modules.
- **TIER-4 (upstream-only):** lives in AgentScope (pinned via `qwenpaw` deps).

---

## Target 1 — AgentScope per-turn hooks

### 1.1 Full hook taxonomy (TIER-4)

`AgentBase.supported_hook_types` (`agentscope/agent/_agent_base.py:34-40`):
```python
["pre_reply", "post_reply", "pre_print", "post_print", "pre_observe", "post_observe"]
```

`ReActAgentBase` extends (`agentscope/agent/_react_agent_base.py:21-31`):
```python
["pre_reply", "post_reply", "pre_print", "post_print", "pre_observe", "post_observe",
 "pre_reasoning", "post_reasoning", "pre_acting", "post_acting"]
```

`QwenPawAgent(ToolGuardMixin, ReActAgent)` inherits all 10. QwenPaw already uses 4 of them (`react_agent.py:457-486`).

### 1.2 Register API (TIER-4)

```python
# agentscope/agent/_agent_base.py:437-547
def register_instance_hook(self, hook_type, hook_name, hook): ...
@classmethod
def register_class_hook(cls, hook_type, hook_name, hook): ...
# Companion: remove_instance_hook, remove_class_hook, clear_instance_hooks
```

### 1.3 Reaching future agent instances

The runner builds a fresh agent every query (`runner.py:547`). Two strategies:

**Strategy A (preferred): `register_class_hook` on `QwenPawAgent`.** Class-level hooks bind to the class dict; every subsequent instance picks them up automatically. One call from the plugin's startup hook covers all sessions.

**Strategy B: monkey-patch `QwenPawAgent.__init__`** to call `self.register_instance_hook(...)` after `super().__init__()`. Heavier and more brittle; only needed for per-instance state.

### 1.4 What each hook can intercept

Pre-hooks receive `(self, deepcopy(kwargs))`; post-hooks receive `(self, deepcopy(kwargs), deepcopy(output))`. Returning a non-`None` value substitutes the kwargs/output for downstream hooks; returning `None` keeps the running value.

| Aim | Hook | Args | Mutation |
|---|---|---|---|
| Per-tool name + args | `pre_acting` | `kwargs={"tool_call": ToolUseBlock}` | Return new dict |
| Per-tool result | `post_acting` | `kwargs` + `output` (`dict \| None`) | Return new output |
| Per-message text | `post_reply` (final) or `pre_print`/`post_print` (per chunk) | `{"msg": Msg, "last": bool, ...}` | Mutate or return |
| Rewrite incoming prompt | `pre_reply` | `kwargs={"msg": Msg \| list[Msg], ...}` | Return modified kwargs |
| Compaction | **No hook.** `_compress_memory_if_needed()` not wrapped | — | Inspect via `pre_reasoning` |

### 1.5 Async semantics

`_AgentMeta` uses `await _execute_async_or_sync_func(pre_hook, ...)` — both sync and async accepted. Exception in hook propagates and aborts the wrapped method. Defensive `try/except` recommended (mirroring `BootstrapHook` at `qwenpaw/agents/hooks/bootstrap.py:96-101`).

### 1.6 Coverage matrix vs Claude Code events

| Claude Code event | Mechanism | Verdict |
|---|---|---|
| `SessionStart` startup matcher | `register_startup_hook` (TIER-1) | ✅ |
| `SessionStart` resume/clear/compact | `pre_reply` class hook + dedup set | ✅ |
| `UserPromptSubmit` | `pre_reply` — modify `msg.content` | ✅ |
| `UserPromptExpansion` | Monkey-patch `_maybe_inject_skill` | ⚠️ patch |
| `PreToolUse` | `pre_acting` | ✅ |
| `PostToolUse` | `post_acting` | ✅ |
| `PostToolUseFailure` | `post_acting` + output inspection | ✅ |
| `PostToolBatch` | `pre_reasoning` (next loop iter) | ⚠️ workaround |
| `Stop` | `post_reply` | ✅ |
| `SubagentStop` | `post_acting` filter on `chat_with_agent` | ⚠️ workaround |
| `PreCompact`/`PostCompact` | Memory size in `pre_reasoning`; or patch `_compress_memory_if_needed` | ⚠️ workaround |
| `Notification` | `post_reply` emit | ⚠️ workaround |
| `TaskCreated`/`TaskCompleted` | TaskTracker subscribe via wrapper | ⚠️ workaround |
| `FileChanged`/`CwdChanged` | OS-level watcher needed | ❌ out of scope |
| `SessionEnd` | `register_shutdown_hook` (process); `post_reply` + reference counting (per-session) | ✅ partial |

### 1.7 Verdict

**HIGH feasibility for production-grade's actual surface.** The plugin's `hooks/hooks.json` declares ONE event (`SessionStart` with matchers `startup|clear|compact`) running ONE shell command. Fully reproducible via `register_class_hook("pre_reply", ...)` + `register_startup_hook` (for the startup matcher).

Concrete sketch:

```python
class ProductionGradePlugin:
    async def register(self, api):
        api.register_startup_hook(
            "session_guard_startup", self._session_guard_startup, priority=50,
        )
        from qwenpaw.agents.react_agent import QwenPawAgent
        QwenPawAgent.register_class_hook(
            "pre_reply", "session_guard_pre_reply", self._session_guard_per_session,
        )

    _seen_sessions: set[str] = set()

    async def _session_guard_per_session(self, agent, kwargs):
        sid = (agent._request_context or {}).get("session_id", "")
        if sid and sid not in self._seen_sessions:
            self._seen_sessions.add(sid)
            await self._run_session_guard("resume")
        return None

    async def _run_session_guard(self, matcher):
        plugin_root = Path(__file__).resolve().parent.parent
        script = plugin_root / "hooks" / "session-guard.sh"
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root),
               "CLAUDE_HOOK_MATCHER": matcher}
        await asyncio.to_thread(
            subprocess.run, ["bash", str(script)],
            env=env, timeout=10, check=False,
        )
```

---

## Target 2 — Skill loader interception (`!`<cmd>`` preprocessing)

### 2.1 Where SKILL.md content enters context

Three points:

**(a) Skill discovery — at agent construction.** `react_agent.py:393-398` calls `Toolkit.register_agent_skill` which reads frontmatter ONLY (upstream `tool/_toolkit.py:1456-1503`). Body is never read here. System prompt addition: `"Check {dir}/SKILL.md for how to use this skill"`.

**(b) Slash-style invocation — at user query.** `runner.py:185-259` (`_maybe_inject_skill`). When user types `/<skill_name> <input>`, lines 220-256 read SKILL.md and inline `post.content` (body after frontmatter):

```python
raw = read_text_file_with_encoding_fallback(skill_md)
post = fm.loads(raw)
merged = (
    f"Use the [{display_name}] skill in `{skill_dir}` to fulfill "
    f"user's task: {user_input}\n\n{post.content}"
)
AgentRunner._rewrite_last_message_text(msgs, merged)
```

**This is the first and best preprocessing point.** Fires for `/skill <input>` invocations only.

**(c) Model-driven `Read SKILL.md`.** Model issues `read_file` tool call. Body returned via `post_acting` hooks — second viable interception point.

### 2.2 Recommended approach: runtime monkey-patch (not pre-render)

Production-grade's `` !`cat CLAUDE.md` ``, `` !`ls Claude-Production-Grade-Suite/` `` etc. are **cwd-sensitive and file-state-sensitive** — pre-rendering would freeze stale state, defeating the point.

**Patch 1 — `_maybe_inject_skill`** (TIER-3):

```python
import re, subprocess, os
from qwenpaw.app.runner import runner as _runner

_BACKTICK_BANG_RE = re.compile(r"!`([^`]+)`")

def _expand_backtick_bang(body, cwd):
    def run(m):
        try:
            out = subprocess.run(m.group(1), shell=True, capture_output=True,
                                 text=True, timeout=10, cwd=cwd)
            return (out.stdout or out.stderr or "").rstrip()
        except Exception as e:
            return f"[backtick-bang failed: {e}]"
    return _BACKTICK_BANG_RE.sub(run, body)

_orig = _runner.AgentRunner._maybe_inject_skill

def _patched(query, msgs, skills):
    res = _orig(query, msgs, skills)
    if res is None and msgs:
        last = msgs[-1]
        content = getattr(last, "content", None)
        if isinstance(content, list):
            for blk in content:
                if isinstance(blk, dict) and blk.get("type") == "text":
                    blk["text"] = _expand_backtick_bang(blk["text"], cwd=os.getcwd())
    return res

_runner.AgentRunner._maybe_inject_skill = staticmethod(_patched)
```

**Patch 2 — `post_acting` hook** for `read_file` SKILL.md results:

```python
async def expand_skill_md_reads(agent, kwargs, output):
    tc = kwargs.get("tool_call") or {}
    if tc.get("name") != "read_file":
        return None
    args = tc.get("input") or {}
    if not str(args.get("path", "")).endswith("SKILL.md"):
        return None
    if not isinstance(output, dict):
        return None
    for blk in output.get("content", []):
        if isinstance(blk, dict) and blk.get("type") == "text":
            blk["text"] = _expand_backtick_bang(blk["text"], os.getcwd())
    return output

QwenPawAgent.register_class_hook("post_acting", "expand_skill_md", expand_skill_md_reads)
```

Both patches together = 100% retention of production-grade protocol bootstrap.

Stability: TIER-3. Pin `qwenpaw` minor version; add 5-line smoke test.

---

## Target 3 — System prompt dynamic injection

### 3.1 Re-read frequency

System prompt is rebuilt **every query** at `runner.py:655`:
```python
agent.rebuild_sys_prompt()
```

`rebuild_sys_prompt` → `_build_sys_prompt()` → `build_system_prompt_from_working_dir(...)` (`prompt.py:232-320`). That re-reads `AGENTS.md`, `SOUL.md`, `PROFILE.md` (or whatever `system_prompt_files` lists) **on every turn**. Files mutated between turns ARE picked up.

### 3.2 Routes

**Route A — write to disk** (TIER-1). Plugin startup hook adds `Z_PLUGIN_PRELUDE.md` to workspace and updates `agent.json.system_prompt_files`.

**Route B — monkey-patch `build_system_prompt_from_working_dir`** (TIER-3):

```python
import qwenpaw.agents.prompt as _qp_prompt
import qwenpaw.agents.react_agent as _ra

_orig_build = _qp_prompt.build_system_prompt_from_working_dir

def _patched_build(*args, **kwargs):
    sys_prompt = _orig_build(*args, **kwargs)
    cwd = os.getcwd()
    if (Path(cwd) / "Claude-Production-Grade-Suite").exists():
        sys_prompt += "\n\n# Production-Grade Suite Active\n..."
    for cm in (Path(cwd) / "CLAUDE.md", Path.home() / ".claude" / "CLAUDE.md"):
        if cm.exists():
            sys_prompt += f"\n\n# {cm.name}\n\n" + cm.read_text(encoding="utf-8")
    return sys_prompt

_qp_prompt.build_system_prompt_from_working_dir = _patched_build
_ra.build_system_prompt_from_working_dir = _patched_build  # rebind import
```

**Double-patch is required** because `react_agent.py:30` does `from .prompt import build_system_prompt_from_working_dir`, capturing the name at import time.

### 3.3 CLAUDE.md equivalence

Use Route A (TIER-1):
1. On install, copy `~/.claude/CLAUDE.md` to `<workspace>/CLAUDE.md`.
2. Update `<workspace>/agent.json` to set `"system_prompt_files": ["AGENTS.md", "SOUL.md", "PROFILE.md", "CLAUDE.md"]`.

Use Route B (TIER-3) only for dynamic per-turn content.

### 3.4 Verdict

**HIGH feasibility.** Per-turn re-read is already the QwenPaw default.

---

## Target 4 — `register_control_command`

### 4.1 Handler contract (TIER-3)

`BaseControlCommandHandler` (`base.py:42-71`):
```python
class BaseControlCommandHandler(ABC):
    command_name: str = ""
    @abstractmethod
    async def handle(self, context: ControlContext) -> str: ...
```

`ControlContext` carries `workspace`, `payload`, `channel`, `session_id`, `user_id`, `agent_id`, `args`. Handler returns `str` rendered as `TextBlock`.

### 4.2 Plugin pipeline wiring

`_app.py:362-389`:
```python
control_commands = plugin_loader.registry.get_control_commands()
for cmd_reg in control_commands:
    register_command(cmd_reg.handler)
    command_registry.register_command(
        f"/{cmd_reg.handler.command_name}",
        priority_level=cmd_reg.priority_level,
    )
```

So `api.register_control_command(handler)` is wired to:
1. Global `_COMMAND_REGISTRY` dispatcher (`command_dispatch.py:68-70`)
2. Channel-level `CommandRegistry` for routing/priority

### 4.3 Pros over monkey-patching `query_handler`

- Single supported entry point (TIER-2 via PluginApi)
- Channel priority routing automatic
- Survives `query_handler` refactors (700 LOC, complex async generator)
- Idiomatic with built-in commands (`/stop`, `/model`, `/skills`)

### 4.4 Known caveats

- **Double-prefix bug.** `_app.py:373` prepends `/` when calling `register_command(f"/{cmd_reg.handler.command_name}", ...)`. If `command_name = "/myfoo"`, you get `"//myfoo"`. **Set `command_name = "myfoo"`** (no prefix).
- Plugin commands do NOT auto-appear in `/skills` listings (skills handler reads workspace skill manifest, not `_COMMAND_REGISTRY`).
- No autocomplete in console UI.

### 4.5 Sketch

```python
class ProtocolsCommandHandler(BaseControlCommandHandler):
    command_name = "protocols"  # NO leading slash
    async def handle(self, ctx):
        target = ctx.args.get("_raw_args", "").strip() or "list"
        if target == "list":
            return "Protocols: Boundary Safety, Receipt, Freshness, ..."
        return f"Protocol {target}: ..."

class ProductionGradePlugin:
    async def register(self, api):
        api.register_control_command(ProtocolsCommandHandler(), priority_level=10)
```

### 4.6 Verdict

**Use `register_control_command` over monkey-patching `query_handler`.** Materially safer. TIER-2 vs TIER-3 monkey-patch.

---

## Cross-target summary

| Need | Best path | Tier |
|---|---|---|
| `SessionStart` startup matcher | `PluginApi.register_startup_hook` | T1 |
| `SessionStart` resume/clear/compact | `register_class_hook("pre_reply")` + dedup | T4 |
| `PreToolUse`/`PostToolUse` | `register_class_hook("pre_acting"/"post_acting")` | T4 |
| `UserPromptSubmit` rewrite | `register_class_hook("pre_reply")` | T4 |
| Outgoing message rewrite | `register_class_hook("post_reply")` | T4 |
| Skill `!`cmd` expansion (slash) | Monkey-patch `_maybe_inject_skill` | T3 |
| Skill `!`cmd` expansion (read-by-tool) | `post_acting` hook scanning `read_file` | T4 |
| CLAUDE.md auto-load | `system_prompt_files += ["CLAUDE.md"]` | T1 |
| Slash command `/protocols` | `PluginApi.register_control_command` | T2 |
| Pre/Post-Compact, FileChanged, CwdChanged | None — out of scope or wrapper-based | — |

**Overall verdict on 100% functional retention:** Production-grade's actual surface is **fully replicable** without modifying QwenPaw source. Risk concentrated in TIER-3 patches (`_maybe_inject_skill`, `build_system_prompt_from_working_dir` rebind); mitigate by version-pinning + 5-line smoke test.

---

## Critical references

- `agentscope/agent/_agent_base.py:34-40,437-547` — base hook list, register_*_hook
- `agentscope/agent/_react_agent_base.py:21-31` — extended hook list
- `agentscope/agent/_agent_meta.py:71-90` — pre/post-hook execution semantics
- `agentscope/tool/_toolkit.py:1456-1556` — `register_agent_skill` (frontmatter-only)
- `qwenpaw/agents/react_agent.py:80,158,388-487,547-557` — agent class, hook registrations
- `qwenpaw/agents/prompt.py:232-320` — `build_system_prompt_from_working_dir`
- `qwenpaw/app/runner/runner.py:186-259,547-655` — `_maybe_inject_skill`, `rebuild_sys_prompt`
- `qwenpaw/app/runner/control_commands/base.py:19-71` — handler contract
- `qwenpaw/app/runner/control_commands/__init__.py:35-103,174-216` — registry, dispatch
- `qwenpaw/app/_app.py:362-389` — plugin → control-command wiring (note `/` double-slash)
- `qwenpaw/plugins/api.py:89-174` — `register_startup_hook`, `register_control_command`
- `qwenpaw/agents/hooks/bootstrap.py:42-103` — canonical hook signature reference
