# Custom ACP Runners + Mission Mode — Feasibility Audit

> Verifies whether the production-grade plugin's "spawn 14 specialist subagents with fresh context, run several in parallel" semantics can be replicated on QwenPaw without modifying source.

## Bottom line

| Question | Verdict |
|---|---|
| Custom ACP runners replicate Claude Code subagent semantics? | ✅ **Yes**, with one re-entrancy caveat (register N suffixed copies for parallel-needing roles) |
| Plugin can install runners at startup? | ✅ Yes via `save_agent_config` |
| Build a Python ACP server from scratch? | ✅ Yes, ~150 lines, QwenPaw ships reference |
| Real subprocess parallelism? | ✅ Yes across distinct runner names |
| Streaming back to orchestrator? | ✅ Yes (text + tool events) |
| Self-approve permissions (skip user gates)? | ✅ Yes (server-driven decision) |
| `/mission` Mode as substrate? | ❌ **No** — hard-coded 3-role design, not extensible |

---

## Q1 — Custom ACP runners as subagent surrogates

### 1.1 Plugin-driven runner installation

ACP runners are persisted per-agent in `workspace_dir/agent.json` under `acp.agents`. Schema (`src/qwenpaw/config/config.py:55-67`):

```python
class ACPAgentConfig(BaseModel):
    enabled: bool = False
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    trusted: bool = True
    tool_parse_mode: str = "call_title"
    stdio_buffer_limit_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
```

Loading is mtime-cached (`config.py:1773-1786`); the live `ACPService` rebuilds whenever the config differs (`delegate_external_agent.py:42-54`):

```python
def _get_acp_service():
    agent_id = get_current_agent_id()
    agent_config = load_agent_config(agent_id)
    acp_config = agent_config.acp or ACPConfig()
    service = get_acp_service(agent_id)
    if service is None or getattr(service, "config", None) != acp_config:
        service = init_acp_service(agent_id, acp_config)
    return service
```

Plugin install pattern via `register_startup_hook` (`src/qwenpaw/plugins/api.py:89-119`):

```python
def install_runners():
    from qwenpaw.config.config import (
        load_agent_config, save_agent_config, ACPAgentConfig, ACPConfig,
    )
    SPECIALISTS = ["product-manager", "solution-architect", "software-engineer", ...]
    for agent_id in get_all_agent_ids():
        cfg = load_agent_config(agent_id)
        cfg.acp = cfg.acp or ACPConfig()
        for role in SPECIALISTS:
            for suffix in ["a", "b", "c"]:  # 3 copies for parallelism
                key = f"pgs-{role}-{suffix}"
                cfg.acp.agents[key] = ACPAgentConfig(
                    enabled=True,
                    command="python",
                    args=["-m", "production_grade.specialists", "--role", role],
                    env={"PG_ROOT": str(PLUGIN_ROOT)},
                    trusted=True,
                    tool_parse_mode="update_detail",
                    stdio_buffer_limit_bytes=50 * 1024 * 1024,
                )
        save_agent_config(agent_id, cfg)
```

> **Caveat:** Plugins load AFTER `start_all_configured_agents()` (`_app.py:307`), so any pre-initialized per-channel ACP services don't pick up new runners until the chat reloads. `delegate_external_agent` is lazy-init/chat-scoped so it will pick up new runners on first call.

### 1.2 Reference ACP server

QwenPaw itself ships `QwenPawACPAgent` (`src/qwenpaw/agents/acp/server.py:327-902`) implementing every method in the spec:

- `initialize` (439-466) — declares `AgentCapabilities(load_session=True, ...)`
- `new_session` (468-490) — returns `NewSessionResponse(session_id=..., config_options=...)`
- `prompt` (513-607) — streams via `self._conn.session_update(...)` with `update_agent_message`, `update_agent_thought`, `start_tool_call`, `update_tool_call`
- `cancel`, `close_session`, `set_session_model`, `set_config_option`, `list_sessions`, `load_session`, `resume_session`

Entry point (server.py:890-902):

```python
async def run_qwenpaw_agent(...):
    agent = QwenPawACPAgent(agent_id=agent_id, workspace_dir=workspace_dir)
    try:
        await run_agent(agent, use_unstable_protocol=True)
    finally:
        await agent._shutdown_workspace()
```

Required SDK: `acp` (already a QwenPaw transitive dep).

**Minimal specialist runner stub (~150 lines):**

```python
# production_grade/specialists/__main__.py
import asyncio, argparse, sys
from pathlib import Path
import acp
from acp import Agent, AgentCapabilities, NewSessionResponse, PromptResponse
from acp.runtime import run_agent
from acp.updates import update_agent_message, text_block

class SpecialistAgent(Agent):
    def __init__(self, role: str, plugin_root: Path):
        super().__init__()
        self.role = role
        self.skill_md = (plugin_root / "skills" / role / "SKILL.md").read_text()
        self.protocols = "\n\n".join(
            (plugin_root / "protocols" / f).read_text()
            for f in [
                "ux-protocol.md", "input-validation.md", "tool-efficiency.md",
                "visual-identity.md", "freshness-protocol.md",
                "receipt-protocol.md", "boundary-safety.md",
                "conflict-resolution.md",
            ]
        )

    async def initialize(self, params):
        return AgentCapabilities(
            load_session=False,
            session_capabilities={"prompts": True, "tools": True},
        )

    async def new_session(self, params):
        return NewSessionResponse(session_id=str(uuid.uuid4()), config_options=[])

    async def prompt(self, params):
        # Build system prompt = SKILL.md + 8 shared protocols
        system = f"{self.protocols}\n\n---\n\n{self.skill_md}"
        # Call the LLM (Anthropic / DashScope / etc) with system + user prompt
        async for delta in stream_llm_response(system, params.prompt):
            await self._conn.session_update(
                session_id=params.session_id,
                update=update_agent_message(text_block(delta)),
            )
        return PromptResponse(stop_reason="end_turn")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--role", required=True)
    p.add_argument("--plugin-root", default=os.environ.get("PG_ROOT"))
    args = p.parse_args()
    agent = SpecialistAgent(args.role, Path(args.plugin_root))
    asyncio.run(run_agent(agent, use_unstable_protocol=True))
```

### 1.3 Process model & parallelism

Sessions held in `ACPService._sessions` keyed by `(chat_id, agent)` (`service.py:43`). New conversations spawn fresh subprocesses (`service.py:269-280`):

```python
conn, process = await exit_stack.enter_async_context(
    spawn_agent_process(
        client,
        agent_config.command,
        *agent_config.args,
        cwd=cwd,
        env={**os.environ, **agent_config.env},
        transport_kwargs={"limit": agent_config.stdio_buffer_limit_bytes},
    ),
)
```

→ **Different runner names = different processes, fully parallel.**

**Hard constraint** (service.py:72-80): same `(chat_id, runner_name)` cannot run two turns concurrently:

```python
if (conversation.prompt_task is not None
    and not conversation.prompt_task.done()):
    raise ACPSessionError(
        f"Session {conversation.acp_session_id} is already processing a turn",
    )
```

**Workaround:** to run two `software-engineer` instances in parallel, register them as `pgs-software-engineer-a`, `-b`, `-c`. The plugin can register N copies up front. Not architecturally elegant but functionally complete.

Alternative: dispatch via `submit_to_agent` (which forks a child session with its own `chat_id`) for fan-out work.

### 1.4 Streaming + permission gates

Streaming contract: async dict-shaped events (`MessageHandler = Callable[[dict, bool], Awaitable[None]]`, `service.py:22`). Buffered + flushed every 1.0 s as `ToolResponse` snapshots (`delegate_external_agent.py:243-274`).

Event types from a custom runner:
- `agent_message_chunk` → text delta (accumulated, emitted via `_emit_assistant_text_delta` at `client.py:242-254`)
- `agent_thought_chunk` → silently swallowed (`client.py:153-155`) — orchestrator is blind to thoughts
- `tool_call` start / `tool_call_update` progress/end → emitted as `{"type": "tool_start"|"tool_update"|"tool_end", ...}` at `client.py:159-169` and `client.py:344-358`

**Permission semantics:** runner-driven. The runner chooses whether to call `request_permission`. If it does, control bubbles to user UI (`service.py:309-339`):

```python
if (permission_task in done
    and conversation.client.pending_permission is not None):
    finished_event = await conversation.client.finish_prompt()
    return {
        "status": "permission_required",
        "suspended_permission": (...),
        "event": finished_event,
    }
```

For Claude Code's "spawn 14 fresh subagents" pattern, **each parallel runner halts independently** when it asks for permission. Mitigation: a custom-built ACP server can simply **never send permission requests** — self-approve internally. The `trusted` flag in `ACPAgentConfig` appears UI-only (no consumer in `agents/acp/`); set `trusted=True` for the UI hint and self-approve in the runner code.

### 1.5 `tool_parse_mode` and `trusted` knobs

`tool_parse_mode` valid values: `{"call_title", "update_detail", "call_detail"}` (`config.py:70-74`). Consumed only in `client.py:360-411` for orchestrator-side display:

- `call_title` — title once, no progress
- `update_detail` — start + progress with full input details (used by `opencode`, `claude_code`)
- `call_detail` — details inline at start (used by `qwen_code`, `codex`)

Recommend `update_detail` for production-grade specialists (visible progress).

`trusted` — UI hint, not enforced server-side.

### 1.6 Q1 verdict

| Capability | Status |
|---|---|
| Fresh context per subagent | ✅ each runner is fresh subprocess; system prompt = its SKILL.md + protocols |
| Parallel execution | ✅ across distinct runner names; ❌ across same `(session_id, runner_name)` |
| Streaming back to orchestrator | ✅ via `agent_message_chunk` + tool events |
| Permission gating | ✅ optional (self-approve in custom server) |
| Plugin install at startup | ✅ via `save_agent_config` in startup hook |
| 14 parallel specialists | ✅ Requires N suffixed copies per role |

The `(session_id, runner_name)` re-entrancy constraint is the only Claude Code mismatch. Trivially solved with N copies. Functionally complete.

---

## Q2 — `/mission` Mode internals

### 2.1 What it does

Two-phase PRD → worker → verifier pipeline that runs the SAME main agent in two distinct modes. Phase 2 deactivates `mission_impl` tool group (`{edit_file, browser_use, desktop_screenshot}`) but keeps `execute_shell_command` and `write_file` for dispatch (`mission_runner.py:103-109`, `:187-195`).

Command flow:
1. `maybe_handle_mission_command` (`mission_dispatch.py:33`) parses `/mission <task>`.
2. `handle_mission_command` (`mission/handler.py:101`) creates loop dir, writes `task.md`, `progress.txt`, `loop_config.json`, and **rewrites the user prompt** to inject the master prompt.
3. `run_mission_phase1` or `run_mission_phase2` (`mission_runner.py:302`/`:470`) invokes the SAME agent in a loop.

### 2.2 Artifacts

```
{workspace_dir}/missions/mission-{YYYYMMDD-HHMMSS}/
├── prd.json          # task list with userStories + passes flags
├── loop_config.json  # phase, max_iterations, git context, session_id
├── task.md           # original task description
└── progress.txt      # append-only iteration log
```

PRD schema (`mission_runner.py:111-119`):
```python
_REQUIRED_PRD_FIELDS = {"userStories"}
_REQUIRED_STORY_FIELDS = {"id", "title", "description", "acceptanceCriteria", "priority"}
```

Story fields: `{id, title, description, acceptanceCriteria, priority, passes, notes}`. Verifier outputs `VERDICT: PASS|FAIL|PARTIAL` (`prompts.py:673-792`).

### 2.3 Custom roles?

**NO.** The PRD/worker/verifier triplet is **hard-coded**:
- `MASTER_PROMPT` (`prompts.py:14-464`) — controller behavior
- `WORKER_PROMPT_TEMPLATE` (`prompts.py:470-573`) — generic implementer
- `VERIFIER_PROMPT_TEMPLATE` (`prompts.py:673-792`) — adversarial verifier

`build_master_prompt` (`prompts.py:819-863`) accepts only config args (`loop_dir`, `agent_id`, `max_iterations`, `verify_commands`, `git_context`, `workspace_dir`); no plugin-supplied prompts. Search for `register_mission_role` / `mission_role_registry` returns zero results.

Workers are real configured QwenPaw agents (not subagent-style); master dispatches via `submit_to_agent(to_agent=WORKER_AGENT_ID, text=...)` (`prompts.py:367-368`). To run production-grade as Mission, you'd register 14 separate full QwenPaw agents — heavyweight, not faithful.

### 2.4 State management

Disk-based, no in-memory state between turns. Per-turn state read from `loop_config.json` + `prd.json`. No FastAPI router for mission, no programmatic dispatch hook. A plugin would have to either drop files into the mission dir or inject `/mission`-prefixed messages.

### 2.5 Failure modes

- Worker fail → master retries up to 3× per story (`prompts.py:421`)
- PRD invalid at Phase 2 entry → reverts phase to `prd_generation` (`mission_runner.py:502-520`)
- PRD schema fix loop → 2 auto-fix attempts (`mission_runner.py:299` `_MAX_PRD_FIX_ATTEMPTS`)
- Max iterations → emits `mission_max_iterations` (`mission_runner.py:602-622`); state preserved on disk
- User cancels mid-run → state stays on disk; resumable via `detect_active_mission_phase`
- **No `/mission resume` or `/mission retry` command** — user starts new mission to continue

### 2.6 Q2 verdict

**Cannot host production-grade at 100% retention.** Specific gaps:

1. No plugin extensibility — master/worker/verifier prompts are hard-coded constants
2. Wrong dispatch substrate — workers are full QwenPaw agents over HTTP, not lightweight subagents
3. ONE user gate (PRD confirmation) ≠ production-grade's 3 named gates (BRD, Architecture, Production Readiness)
4. No formal architecture/contract artifacts — only `prd.json` user stories

Mission Mode's spine (phase machine + on-disk PRD + iteration loop) is structurally similar but not extensible. **Use as inspiration for the loop pattern; do not graft production-grade onto it.**

---

## Concrete port shape

1. **Plugin's `register_startup_hook` writes 14 `ACPAgentConfig` entries** into each agent's `agent.json` (one per specialist; for parallel-needing roles, register N suffixed copies).
2. **Plugin ships 14 tiny stdio ACP server modules** (one per role), each loading its specialist SKILL.md as system prompt and self-approving permissions.
3. **Plugin ships ONE orchestrator skill** (the entry point — equivalent to production-grade's `production-grade` skill) that calls `delegate_external_agent` to dispatch specialists.
4. **The orchestrator skill encodes the 10 modes / 3 approval gates / artifact pipeline in its own system prompt** — it is the brain; specialists are the hands.

## Critical files

- `src/qwenpaw/agents/acp/server.py` — reference ACP server implementation (902 lines)
- `src/qwenpaw/agents/acp/service.py` — client/orchestrator side
- `src/qwenpaw/agents/acp/client.py` — event handlers, permission flow, tool_parse_mode dispatch
- `src/qwenpaw/agents/tools/delegate_external_agent.py` — the delegation tool
- `src/qwenpaw/config/config.py:55-117` — ACP config schema
- `src/qwenpaw/plugins/api.py:89-119` — `register_startup_hook` extension point
- `src/qwenpaw/app/_app.py:304-419` — plugin loader entry
- `src/qwenpaw/agents/mission/mission_runner.py` — Mission Mode engine
- `src/qwenpaw/agents/mission/prompts.py` — hard-coded role prompts (MASTER/WORKER/VERIFIER)
- `src/qwenpaw/agents/mission/handler.py` — command parsing
- `src/qwenpaw/agents/mission/state.py` — loop dir + persistence
