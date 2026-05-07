# 100% Functional-Parity Architecture

> Plan to port the Claude Code "production-grade" plugin (v5.4.0) to QwenPaw with **100% functional retention** — including subagent fresh-context, parallel specialist execution, structured-options gate UI, skill-body preprocessing, CLAUDE.md auto-load, and the full hook surface — **without modifying QwenPaw source**.

This supersedes `05_compatibility_matrix.md` / `06_migration_plan.md` / `07_gotchas_and_risks.md` for the 100%-retention target. Those earlier docs describe the simpler ~85% plan; this one is the full path.

Verified by three deep research passes — see `research_notes/05_frontend_extension_audit.md`, `research_notes/06_acp_and_mission_audit.md`, `research_notes/07_hooks_and_loader_audit.md`.

---

## Bottom line

**100% functional retention is feasible.** Every Claude Code primitive production-grade depends on has a reachable surrogate in QwenPaw via documented or example-only extension points (with one TIER-3 monkey-patch for `!`shell`` skill preprocessing). Reliability is preserved by pinning the QwenPaw minor version and adding smoke tests for the patched paths.

| Claude Code primitive | Production-grade uses it? | QwenPaw mechanism | Tier |
|---|---|---|---|
| Skills (SKILL.md) | All 14 specialists | Native QwenPaw skills | T1 |
| Sub-agents (`Agent`/`Task`) | Implicit via `Skill` dispatch | Custom ACP runners | T1+T4 |
| Parallel sub-agents (Wave A/B/C) | Yes | N suffixed runner copies | T1 |
| `Skill` tool dynamic dispatch | Yes (orchestrator) | Custom MCP server tool | T1 |
| `AskUserQuestion` | All 6 UX rules + 3 gates | `registerToolRender` + custom MCP tool | T2 |
| `TaskCreate`/`TaskUpdate`/`TaskList` | Progress visibility | Custom MCP tool + `registerRoutes` dashboard | T2 |
| `WebSearch` (Freshness) | Tier 1-3 | `tavily_search` MCP (built-in) | T1 |
| `SessionStart` hook | `session-guard.sh` | `register_startup_hook` + `pre_reply` class hook | T1+T4 |
| `UserPromptSubmit` hook | `activation-rules.json` | `pre_reply` class hook OR `register_control_command` | T2/T4 |
| `PreToolUse`/`PostToolUse` | Not currently used | `pre_acting`/`post_acting` class hooks (available if needed) | T4 |
| `!`<cmd>`` skill preprocessing | All 14 skills (loads 8 protocols) | Monkey-patch `_maybe_inject_skill` + `post_acting` | T3+T4 |
| `${CLAUDE_PLUGIN_ROOT}` env | Hook commands | `os.environ["PG_ROOT"]` set in plugin startup | — |
| `Claude-Production-Grade-Suite/` workspace | Receipts, protocols, settings | Verbatim port (file-based) | — |
| `CLAUDE.md` auto-load | Inherited from Claude Code | `system_prompt_files += ["CLAUDE.md"]` (per-turn re-read native) | T1 |
| Marketplace install | `/plugin install` | `qwenpaw plugin install <git-url>` | T1 |

---

## Six-tier plugin architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 6 — Pre-rendered skills (~/.qwenpaw/skill_pool/<name>/)    │  Optional fallback
├─────────────────────────────────────────────────────────────────┤
│ TIER 5 — Workspace state (Claude-Production-Grade-Suite/)       │  Runtime-agnostic, file-based
├─────────────────────────────────────────────────────────────────┤
│ TIER 4 — Frontend plugin (entry.frontend → dist/index.js)       │
│   • registerToolRender for AskUserQuestion / Gates / Tasks      │
│   • registerRoutes for /plugin/pg/dashboard sidebar             │
├─────────────────────────────────────────────────────────────────┤
│ TIER 3 — Custom MCP server (pg-orchestrator-mcp, stdio)         │
│   • mcp__pg__dispatch_specialist                                │
│   • mcp__pg__ask_user_question                                  │
│   • mcp__pg__gate_ceremony                                      │
│   • mcp__pg__task_create / task_update / task_list              │
│   • mcp__pg__receipt_write / receipt_verify                     │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2 — Custom ACP runners (one per specialist × N copies)     │
│   • pgs-product-manager-{a,b,c}                                 │
│   • pgs-solution-architect-{a,b,c}                              │
│   • pgs-software-engineer-{a,b,c,d}                             │
│   • ... 14 roles × 3-4 copies = ~42-56 runner configs           │
│   • Each = stdio Python ACP server loading ONE SKILL.md         │
├─────────────────────────────────────────────────────────────────┤
│ TIER 1 — Backend Python plugin (entry.backend → plugin.py)      │
│   • register_startup_hook → install ACP runners, MCP, hooks     │
│   • register_class_hook on QwenPawAgent (AgentScope hooks)      │
│   • Monkey-patches _maybe_inject_skill (skill preprocessing)    │
│   • register_control_command for slash commands                 │
│   • Spawns pg-orchestrator-mcp subprocess at startup            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tier 1 — Backend Python plugin

### What it does

1. Sets `os.environ["PG_ROOT"]` to the plugin install dir.
2. Spawns `pg-orchestrator-mcp` subprocess (Tier 3) and registers it as an MCP server in the active agent's `agent.json` via `save_agent_config`.
3. Writes 14 specialist ACP runners (with 3-4 suffixed copies each for parallelism) into `agent.json.acp.agents`.
4. Patches `qwenpaw.app.runner.runner.AgentRunner._maybe_inject_skill` to expand `` !`<cmd>` `` (TIER-3).
5. Patches `qwenpaw.agents.prompt.build_system_prompt_from_working_dir` to inject `CLAUDE.md` and project-detection prelude (TIER-3, plus rebinding the `react_agent` import).
6. `QwenPawAgent.register_class_hook` for:
   - `pre_reply` → SessionStart resume/clear matcher logic (one-time per session)
   - `post_acting` → expand `!`...`` in `read_file` results targeting `SKILL.md`; emit task progress events; write receipts
7. `register_control_command` for plugin slash commands (`/protocols`, `/pg-status`, etc.).
8. Pre-renders skills to `~/.qwenpaw/skill_pool/` if pre-rendering is preferred over runtime expansion (Tier 6 fallback).

### `plugin.py` skeleton

```python
"""Backend entry. Registers everything with QwenPaw via PluginApi."""
from __future__ import annotations
import asyncio, os, subprocess
from pathlib import Path
from qwenpaw.plugins.api import PluginApi
from production_grade.acp_install import install_specialist_runners
from production_grade.mcp_server import start_mcp_server
from production_grade.monkey_patches import (
    patch_maybe_inject_skill, patch_system_prompt_builder,
)
from production_grade.hooks import (
    SessionGuardHook, ProtocolExpander, ReceiptWriter,
)
from production_grade.commands import ProtocolsCommandHandler

ROOT = Path(__file__).resolve().parent

class ProductionGradePlugin:
    async def register(self, api: PluginApi):
        os.environ["PG_ROOT"] = str(ROOT)

        # Lifecycle hooks
        api.register_startup_hook(
            "pg_install",
            self._on_startup,
            priority=50,
        )
        api.register_shutdown_hook(
            "pg_shutdown",
            self._on_shutdown,
            priority=50,
        )

        # Slash commands
        api.register_control_command(
            ProtocolsCommandHandler(),
            priority_level=10,
        )

    async def _on_startup(self):
        # 1. ACP runner install
        await install_specialist_runners(plugin_root=ROOT)
        # 2. MCP server boot (subprocess)
        self.mcp_proc = await start_mcp_server(plugin_root=ROOT)
        # 3. Monkey-patches
        patch_maybe_inject_skill()
        patch_system_prompt_builder()
        # 4. Class hooks on QwenPawAgent
        from qwenpaw.agents.react_agent import QwenPawAgent
        QwenPawAgent.register_class_hook(
            "pre_reply", "pg_session_guard",
            SessionGuardHook(plugin_root=ROOT),
        )
        QwenPawAgent.register_class_hook(
            "post_acting", "pg_protocol_expander",
            ProtocolExpander(),
        )
        QwenPawAgent.register_class_hook(
            "post_acting", "pg_receipt_writer",
            ReceiptWriter(),
        )

    async def _on_shutdown(self):
        if self.mcp_proc:
            self.mcp_proc.terminate()
            try:
                await asyncio.wait_for(self.mcp_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.mcp_proc.kill()

plugin = ProductionGradePlugin()
```

### Stability tiering of Tier-1 surfaces

| Surface | Tier | Notes |
|---|---|---|
| `PluginApi.register_startup_hook` | T1 | Documented |
| `PluginApi.register_shutdown_hook` | T1 | Documented |
| `PluginApi.register_control_command` | T2 | Source-only but exported via PluginApi |
| `QwenPawAgent.register_class_hook` | T4 | AgentScope upstream — pin `agentscope==1.0.19.post1` |
| Monkey-patch `AgentRunner._maybe_inject_skill` | T3 | Internal name; pin minor version + smoke test |
| Monkey-patch `build_system_prompt_from_working_dir` | T3 | Same |

---

## Tier 2 — Custom ACP runners

### Install pattern

```python
# production_grade/acp_install.py
from pathlib import Path
from qwenpaw.config.config import (
    load_agent_config, save_agent_config, ACPAgentConfig, ACPConfig,
)
from qwenpaw.app.agent_context import get_all_agent_ids   # source-only

SPECIALISTS = {
    "polymath":           1,
    "product-manager":    1,
    "solution-architect": 1,
    "software-engineer":  4,   # parallel-heavy
    "frontend-engineer":  3,
    "qa-engineer":        3,
    "security-engineer":  2,
    "code-reviewer":      2,
    "devops":             2,
    "sre":                1,
    "technical-writer":   1,
    "data-scientist":     1,
    "skill-maker":        1,
}

async def install_specialist_runners(plugin_root: Path):
    for agent_id in get_all_agent_ids():
        cfg = load_agent_config(agent_id)
        cfg.acp = cfg.acp or ACPConfig()
        for role, copies in SPECIALISTS.items():
            for i in range(copies):
                suffix = chr(ord("a") + i)
                key = f"pgs-{role}-{suffix}"
                cfg.acp.agents[key] = ACPAgentConfig(
                    enabled=True,
                    command="python",
                    args=["-m", "production_grade.specialists",
                          "--role", role,
                          "--copy", suffix],
                    env={"PG_ROOT": str(plugin_root)},
                    trusted=True,
                    tool_parse_mode="update_detail",
                    stdio_buffer_limit_bytes=50 * 1024 * 1024,
                )
        save_agent_config(agent_id, cfg)
```

### The specialist runner (~150 lines)

```python
# production_grade/specialists/__main__.py
import asyncio, argparse, os, uuid
from pathlib import Path
import acp
from acp import Agent, AgentCapabilities, NewSessionResponse, PromptResponse
from acp.runtime import run_agent
from acp.updates import update_agent_message, text_block

class SpecialistACPAgent(Agent):
    def __init__(self, role: str, copy: str, plugin_root: Path):
        super().__init__()
        self.role = role
        self.copy = copy
        self.plugin_root = plugin_root
        self.skill_md = (plugin_root / "skills" / role / "SKILL.md").read_text()
        # 8 shared protocols loaded once at runner startup (fresh process per delegation)
        self.protocols = "\n\n".join(
            (plugin_root / "protocols" / fn).read_text()
            for fn in [
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
        system = f"# Production-Grade Protocols\n\n{self.protocols}\n\n# Role: {self.role}\n\n{self.skill_md}"
        async for delta in self._stream_llm(system, params.prompt):
            await self._conn.session_update(
                session_id=params.session_id,
                update=update_agent_message(text_block(delta)),
            )
        return PromptResponse(stop_reason="end_turn")

    async def _stream_llm(self, system: str, user_prompt):
        # Pluggable: Anthropic / DashScope / OpenAI-compatible
        # For Qwen via DashScope (production default):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            base_url=os.environ.get(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )
        stream = await client.chat.completions.create(
            model=os.environ.get("PG_SPECIALIST_MODEL", "qwen-max-latest"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": str(user_prompt)},
            ],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--role", required=True)
    p.add_argument("--copy", default="a")
    args = p.parse_args()
    plugin_root = Path(os.environ["PG_ROOT"])
    agent = SpecialistACPAgent(args.role, args.copy, plugin_root)
    asyncio.run(run_agent(agent, use_unstable_protocol=True))
```

### Why N copies per role

QwenPaw's ACP service has a hard constraint at `service.py:72-80`: same `(chat_id, runner_name)` cannot run two turns concurrently. Production-grade's Wave B runs QA + Security + Code Review in parallel against the same code. To support this:

- 1 copy is enough for serial roles (PM, Architect, Polymath, …)
- 3-4 copies for parallel-heavy roles (SE, FE, QA, Security, Code Review, DevOps)

The orchestrator picks an unused copy by polling: `delegate_external_agent(action="start", runner="pgs-software-engineer-a")` → if busy, try `-b`.

---

## Tier 3 — Custom MCP server (`pg-orchestrator-mcp`)

### Tools exposed

These look like Claude Code's meta-tools to the orchestrator agent:

| Tool name | Purpose | Returns |
|---|---|---|
| `pg__dispatch_specialist` | Wraps `delegate_external_agent` to a specific runner | text + structured result |
| `pg__ask_user_question` | Renders structured options in chat (frontend) | user's chosen option |
| `pg__gate_ceremony` | Renders gate UI with metrics + decision options | user's decision |
| `pg__task_create` | Adds task to dashboard | task ID |
| `pg__task_update` | Updates task status | ack |
| `pg__task_list` | Lists current tasks | task array |
| `pg__receipt_write` | Writes a receipt JSON to `.orchestrator/receipts/` | receipt path |
| `pg__receipt_verify` | Confirms artifacts in receipt exist on disk | bool + missing list |
| `pg__send_message` | Inter-specialist message via shared file or peer chat | ack |

### Why MCP and not native plugin tools

- **MCP is TIER-1 stable** in QwenPaw (mcp.en.md, hot-reloaded via 2-second poll).
- Tools registered via MCP are auto-discovered by every QwenPaw agent.
- Naming convention `mcp__<server>__<tool>` is the pattern frontend renderers key on.
- Bonus: third-party tools can also use `pg__*` tools without QwenPaw-specific code.

### `pg__ask_user_question` flow

1. Orchestrator emits `mcp__pg__ask_user_question(question, header, options[])` tool call.
2. The MCP server receives it and **does not return immediately** — it stores the question in shared state, returns a "pending" placeholder.
3. The frontend's registered `registerToolRender` for `mcp__pg__ask_user_question` shows the structured UI (antd buttons).
4. User clicks an option → frontend POSTs the chosen label to `/console/chat` as a user message.
5. The orchestrator agent sees the next user message, parses it, and resumes.

Alternative: use **MCP elicitation** (`Elicitation` event in Claude Code's hook list — not exposed to QwenPaw plugins, but the Anthropic MCP spec has it). For QwenPaw, the simpler approach above (MCP tool returns a marker, frontend handles UX, user reply parsed by orchestrator) is more robust.

### MCP server stub

```python
# production_grade/mcp_server.py
import asyncio, json, sys
from pathlib import Path
from mcp.server.stdio import stdio_server
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

server = Server("pg-orchestrator-mcp")

@server.list_tools()
async def list_tools():
    return [
        {"name": "pg__dispatch_specialist", "description": "...",
         "inputSchema": {"type": "object", "properties": {
             "specialist": {"type": "string"},
             "task": {"type": "string"},
         }, "required": ["specialist", "task"]}},
        # ... other tools
    ]

@server.call_tool()
async def call_tool(name, arguments):
    if name == "pg__dispatch_specialist":
        return await dispatch(arguments["specialist"], arguments["task"])
    if name == "pg__ask_user_question":
        return await ask_user(arguments)
    # ...

async def dispatch(specialist: str, task: str):
    # Pick first available copy by polling
    for copy in "abcd":
        runner = f"pgs-{specialist}-{copy}"
        if not is_busy(runner):
            return await delegate(runner, task)
    raise RuntimeError(f"No free copy for {specialist}")

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write,
            InitializationOptions(server_name="pg-orchestrator-mcp",
                                  server_version="0.1.0"))

async def start_mcp_server(plugin_root: Path):
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "production_grade.mcp_server",
        env={**os.environ, "PG_ROOT": str(plugin_root)},
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    # Register with QwenPaw MCP config so the agent connects via stdio
    # (use existing MCPClientConfig API in agent.json)
    return proc
```

The MCP server is registered with QwenPaw the same way any MCP server is — via `agent.json.mcp_clients` or via `qwenpaw mcp add` CLI. Plugin's startup hook does this programmatically through `save_agent_config`.

---

## Tier 4 — Frontend plugin (`entry.frontend`)

Build target: a single JS bundle (TypeScript → Vite/esbuild) shipped at `dist/index.js`. Loaded by QwenPaw's plugin loader (`console/src/plugins/usePluginLoader.ts:39-58`), which fetches via `/api/plugins`, wraps in Blob URL, and dynamic-imports.

### `frontend/index.tsx` (compiled to `dist/index.js`)

```tsx
import * as React from "react";   // resolved to window.QwenPaw.host.React
import { Card, Button, Table, Space, Typography, Collapse, List, Tag } from "antd";

const PLUGIN_ID = "production-grade";

// ── Tool renderers ─────────────────────────────────────────────────────────

function AskUserQuestionCard({ result }: any) {
  const data = typeof result === "string" ? JSON.parse(result) : result;
  const send = async (label: string) => {
    const url = (window as any).QwenPaw.host.getApiUrl("/console/chat");
    const token = (window as any).QwenPaw.host.getApiToken();
    await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        input: [{ role: "user", content: [{ type: "text", text: label }] }],
        session_id: (window as any).currentSessionId,
        stream: true,
      }),
    });
  };
  return (
    <Card title={data.header} style={{ marginTop: 12 }}>
      <Typography.Paragraph>{data.question}</Typography.Paragraph>
      <Space direction="vertical" style={{ width: "100%" }}>
        {data.options.map((o: any) => (
          <Button key={o.label} block onClick={() => send(o.label)}>
            <strong>{o.label}</strong> — {o.description}
          </Button>
        ))}
      </Space>
    </Card>
  );
}

function GateCeremonyCard({ result }: any) {
  const d = typeof result === "string" ? JSON.parse(result) : result;
  const decide = async (decision: string) => {
    /* same POST as AskUserQuestionCard */
  };
  return (
    <Card title={`◆ GATE ${d.gate_number}: ${d.gate_name}`} style={{ marginTop: 12 }}>
      <Table
        dataSource={d.metrics}
        columns={[
          { title: "Metric", dataIndex: "key" },
          { title: "Value", dataIndex: "value" },
        ]}
        pagination={false}
      />
      {d.diff && (
        <Collapse>
          <Collapse.Panel header="Show diff" key="1">
            <pre>{d.diff}</pre>
          </Collapse.Panel>
        </Collapse>
      )}
      <Space style={{ marginTop: 12 }}>
        {d.decisions.map((dec: any) => (
          <Button
            key={dec.id}
            type={dec.recommended ? "primary" : "default"}
            onClick={() => decide(dec.id)}
          >
            {dec.label}
          </Button>
        ))}
      </Space>
    </Card>
  );
}

function TaskListCard({ result }: any) {
  const tasks = typeof result === "string" ? JSON.parse(result) : result;
  return (
    <List
      dataSource={tasks.tasks || []}
      renderItem={(t: any) => (
        <List.Item>
          <Tag color={
            { todo: "default", in_progress: "processing",
              done: "success", failed: "error" }[t.state] || "default"
          }>
            {t.state}
          </Tag>
          <Typography.Text>{t.name}</Typography.Text>
        </List.Item>
      )}
    />
  );
}

// ── Persistent dashboard route ─────────────────────────────────────────────

function PGDashboard() {
  const [tasks, setTasks] = React.useState<any[]>([]);
  const [receipts, setReceipts] = React.useState<any[]>([]);
  React.useEffect(() => {
    const url = (window as any).QwenPaw.host.getApiUrl(
      "/plugins/pg/state/stream",
    );
    const es = new EventSource(url);
    es.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "task") setTasks(msg.tasks);
      if (msg.type === "receipt") setReceipts(msg.receipts);
    };
    return () => es.close();
  }, []);
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>Production-Grade Pipeline</Typography.Title>
      <Typography.Title level={4}>Tasks</Typography.Title>
      <List dataSource={tasks} renderItem={(t: any) => (
        <List.Item>{t.state} — {t.name}</List.Item>
      )} />
      <Typography.Title level={4}>Receipts</Typography.Title>
      <List dataSource={receipts} renderItem={(r: any) => (
        <List.Item>{r.task} — {r.agent} — {r.status}</List.Item>
      )} />
    </div>
  );
}

// ── Registration ───────────────────────────────────────────────────────────

(window as any).QwenPaw.registerToolRender?.(PLUGIN_ID, {
  mcp__pg__ask_user_question: AskUserQuestionCard,
  mcp__pg__gate_ceremony:     GateCeremonyCard,
  mcp__pg__task_list:         TaskListCard,
});

(window as any).QwenPaw.registerRoutes?.(PLUGIN_ID, [{
  path: "/plugin/pg/dashboard",
  component: PGDashboard,
  label: "PG Pipeline",
  icon: "🏗",
  priority: 5,
}]);
```

### Backend SSE endpoint for the dashboard

Tier 1 plugin's startup hook also exposes an SSE endpoint via FastAPI router registration. Pattern reference: `console/src/api/modules/plan.ts:52-115` (`/plan/stream`). The plugin can register a router on QwenPaw's FastAPI app (it inherits from `agentscope_runtime.engine.app.AgentApp`).

---

## Tier 5 — Workspace state

The `Claude-Production-Grade-Suite/` directory ports verbatim — file-based, runtime-agnostic. Same structure as production-grade:

```
Claude-Production-Grade-Suite/
├── .protocols/                 ← shared protocols (8 files)
├── .orchestrator/
│   ├── settings.md             ← engagement mode
│   ├── receipts/               ← T*-{agent}.json per task
│   ├── codebase-context.md     ← brownfield context
│   ├── rework-log.md
│   ├── activation-log.json
│   └── compound-learnings.md
├── product-manager/
├── solution-architect/
├── ... (per-specialist workspaces)
```

The MCP server's `pg__receipt_write` and `pg__receipt_verify` tools manage `.orchestrator/receipts/` directly. The orchestrator skill body instructs the model to write receipts after each phase.

---

## Tier 6 — Pre-rendered skills (optional)

The plugin's startup hook can pre-render skills to `~/.qwenpaw/skill_pool/<name>/SKILL.md` with protocols inlined and `!`...`` expanded once. **Not the primary path** — runtime expansion via Tier 1 monkey-patches is more faithful (because `!`<cmd>`` is cwd-sensitive). Use pre-rendering only if monkey-patches need to be skipped (e.g., for forward compatibility).

---

## Hooks coverage matrix (final)

| Claude Code event | Production-grade uses? | QwenPaw mechanism |
|---|---|---|
| `SessionStart` (startup) | ✅ session-guard.sh | `register_startup_hook` (T1) |
| `SessionStart` (resume/clear/compact) | ✅ same | `register_class_hook("pre_reply")` + dedup set (T4) |
| `UserPromptSubmit` (activation rules) | ✅ activation-rules.json | `register_class_hook("pre_reply")` (T4) — same pre_reply path, different logic |
| `PreToolUse` | ⚠️ not used directly | `register_class_hook("pre_acting")` available (T4) |
| `PostToolUse` | ✅ implicit (receipts) | `register_class_hook("post_acting")` for receipt writes (T4) |
| `Stop` | ⚠️ implicit (gate transitions) | `register_class_hook("post_reply")` (T4) |
| `SubagentStop` | ✅ implicit (specialist completion) | `delegate_external_agent` returns when runner completes |
| `Notification` | ❌ not used | `post_reply` emit if needed |
| `PreCompact`/`PostCompact` | ❌ not used | n/a |
| `SessionEnd` | ❌ not used | `register_shutdown_hook` (T1) |

Production-grade only uses 2 hook events directly. Both are reachable. The other ~27 Claude Code events are not load-bearing for this port.

---

## Reliability strategy

The 100% retention path uses 3 monkey-patches and several class hooks. To match Claude Code's reliability:

### Version pinning

`plugin.json` declares:
```json
{
  "min_version": "1.1.5",
  "dependencies": [
    {"name": "qwenpaw", "version": "~1.1.5"}
  ]
}
```

Plus a runtime smoke test in startup hook:
```python
async def _smoke_test_patched_paths():
    """Confirm the patched names still exist; abort if not."""
    from qwenpaw.app.runner import runner as _r
    from qwenpaw.agents import prompt as _p
    if not hasattr(_r.AgentRunner, "_maybe_inject_skill"):
        raise RuntimeError("QwenPaw API changed: _maybe_inject_skill missing")
    if not hasattr(_p, "build_system_prompt_from_working_dir"):
        raise RuntimeError("QwenPaw API changed: build_system_prompt missing")
```

### Error containment

Every hook wraps its body in `try/except` and logs failures without raising — mirroring `BootstrapHook`'s pattern. If a class hook errors, the agent turn continues; the protocol is just skipped for that turn. Production-grade's existing `boundary-safety.md` protocol covers this gracefully.

### CI gating

Test matrix:
- Latest `qwenpaw` 1.1.x → must pass
- Latest beta (e.g., `1.1.6b1`) → may pass with warnings
- Future `1.2.x` → blocking warning, opt-in flag

### Forward-compatibility plan

When QwenPaw changes:
1. Smoke test fails on startup → plugin refuses to load with a clear error.
2. User sees a clear message: "Production-grade plugin needs an update for QwenPaw 1.2; see <repo> for compatible version."
3. Maintainer updates the patches and ships a new release tag.

---

## Phased build plan (revised for 100% retention)

### Phase 0 — Discovery (1-2 days)

- Spike: install QwenPaw locally; build and install gpt-image2 example plugin to confirm pipeline.
- Spike: write minimal ACP runner stub; register via `save_agent_config`; call `delegate_external_agent` to confirm spawn + streaming.
- Spike: write minimal frontend plugin with one `registerToolRender`; confirm tool call rendering works in chat.
- Spike: write minimal MCP server with one tool; register via `agent.json.mcp_clients`; confirm tool listing and call flow.

### Phase 1 — Tier 1 backend skeleton (2-3 days)

- `plugin.py` with `register_startup_hook` registering all class hooks and monkey-patches.
- ACP runner installer for one specialist (`product-manager`) only.
- Confirm class hook fires on chat turns; smoke-test patched names.

### Phase 2 — Tier 3 MCP server (3-4 days)

- Implement all 9 tools (`pg__dispatch_specialist`, `pg__ask_user_question`, `pg__gate_ceremony`, `pg__task_create/update/list`, `pg__receipt_write/verify`, `pg__send_message`).
- Subprocess lifecycle management.
- State store for pending questions (in-memory + JSON snapshot).

### Phase 3 — Tier 2 ACP runners (3-4 days)

- Specialist runner module for 14 roles.
- Pluggable LLM client (DashScope default; OpenAI-compatible fallback).
- N suffixed copies per role; busy-detection and round-robin in `pg__dispatch_specialist`.

### Phase 4 — Tier 4 frontend (3-5 days)

- `AskUserQuestionCard`, `GateCeremonyCard`, `TaskListCard` tool renderers.
- `PGDashboard` route with SSE.
- Build pipeline: TypeScript → esbuild → `dist/index.js`.
- FastAPI router registration for `/plugins/pg/state/stream` SSE endpoint.

### Phase 5 — Skill content port (3-5 days)

- Port all 14 SKILL.md bodies. Tool name find/replace where Claude-Code-specific.
- 8 protocol files copied verbatim.
- The orchestrator skill body issues `pg__dispatch_specialist` calls; specialists' bodies remain unchanged.

### Phase 6 — End-to-end + reliability (2-3 days)

- Full Build mode end-to-end test (all 14 specialists, 3 gates, receipts).
- Wave B parallelism stress test (3 specialists running concurrently).
- Frontend gate ceremony manual test.
- CI matrix: 1.1.5 / 1.1.6b1 / 1.2.0 (when available).

### Phase 7 — Marketplace + docs (1-2 days)

- README, install guide, FAQ.
- `qwenpaw plugin install <git-url>` flow.
- Tagged release.

**Total: 18-28 days elapsed for v1.0 with 100% retention.** Compare to the simpler 85% port plan (`06_migration_plan.md`) at 14-21 days. The extra ~5-7 days buys: true subagent fresh-context, real parallelism, structured-options UI, gate ceremonies, dashboard.

---

## Risks (all mitigated)

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_maybe_inject_skill` renamed | Low (TIER-3, stable name) | Version pin + smoke test |
| `build_system_prompt_from_working_dir` rebind misses a call site | Low | Test confirms patched function fires from `react_agent` |
| ACP runner re-entrancy (concurrent same-runner calls) | Medium | N suffixed copies; busy polling in `pg__dispatch_specialist` |
| Frontend renderer prop shape change | Low (example-doc-grade) | Defensive parsing, fallback render |
| MCP server crashes mid-pipeline | Medium | Restart on failure; receipts persist on disk |
| Tavily key missing | Medium | Plugin startup checks; emits clear error |
| LLM provider rate limits during parallel waves | High | Configurable parallelism cap; queue inside `pg__dispatch_specialist` |
| QwenPaw 1.2 breaking changes | Unknown | Smoke test refuses load with clear message |

---

## Net assessment

Compared to the 85% port:

| Dimension | 85% port | 100% port |
|---|---|---|
| Specialist fresh context | ❌ single-agent drift | ✅ ACP fresh subprocess |
| Wave A/B/C parallelism | ❌ serialized | ✅ N copies + concurrent dispatch |
| AskUserQuestion UX | ⚠️ plain-text fallback | ✅ structured antd UI |
| Gate ceremonies | ⚠️ plain-text | ✅ tables + decision buttons |
| TaskCreate/List | ⚠️ progress messages | ✅ live dashboard |
| `!`<cmd>`` skill preprocessing | ⚠️ inline or sibling-file Read | ✅ runtime expansion |
| CLAUDE.md auto-load | ❌ manual setup | ✅ system_prompt_files |
| SessionStart matchers | ✅ via `query_handler` patch | ✅ via class hooks (cleaner) |
| Effort | 2-3 weeks | 3-4 weeks |
| Reliability | TIER-3 monkey-patch only | TIER-2 + TIER-3 + TIER-4; pinned with smoke tests |

**The 100% port is feasible. Reliability matches Claude Code's version when QwenPaw minor version is pinned and smoke tests guard the patched paths.** The effort delta over the 85% plan is 1 week, mostly in the frontend + MCP server tiers.

The single largest engineering investment is the MCP server (Tier 3) — but it's also the highest-leverage component, since it provides the same tool surface every QwenPaw agent (not just production-grade) can reuse.

---

## Open questions for Phase 0

1. Does `get_all_agent_ids()` exist on `qwenpaw.app.agent_context` or do we need to enumerate via `~/.qwenpaw/workspaces/`? (Source check needed.)
2. What's the maximum throughput for ACP delegation in a single chat session before `service.py:269-280`'s subprocess spawn becomes the bottleneck? (Phase 0 stress test.)
3. Does QwenPaw's web console reload the frontend bundle when a plugin is reinstalled, or does it require a full page refresh? (Affects dev iteration speed.)
4. Are there frontend prop-shape changes between QwenPaw 1.1.5 and 1.1.6b1 that break tool renderers? (Phase 0 cross-version test.)
5. For Wave B parallelism, what's the LLM-provider rate-limit ceiling we should plan around? (Configure max parallel dispatches accordingly.)

These are not blockers; they're calibration knobs.
