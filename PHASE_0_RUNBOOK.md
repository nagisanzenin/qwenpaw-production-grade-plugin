# Phase 0 Runbook — Get QwenPaw Running, Then Verify Each Tier

You don't need any plugin code yet. The goal here is: install QwenPaw, get a chat working, and prove each of the six architecture tiers works in isolation **with the smallest possible test plugin**. Once all six spikes pass, the production-grade port becomes mostly content work (skill bodies + protocol files).

Track time: **~half a day to first chat, ~2 days through all spikes** if you've done plugin dev before; ~3-4 days otherwise.

---

## 0. Prerequisites

- **Python** between 3.10 and 3.13 inclusive. **Not 3.14** (`pyproject.toml: requires-python = ">=3.10,<3.14"`). You have 3.12 and 3.13 — either works.
- **A virtualenv** (cleaner than installing into system Python).
- **One LLM API key.** Easiest options:
  - **DashScope** (Qwen native) — sign up at https://dashscope.console.aliyun.com/. Best matchup with QwenPaw.
  - **Together AI** — you already have `TOGETHER_API_KEY` in `~/.config/temllm/together.env`. OpenAI-compatible.
  - **OpenAI** — if you have a key.
  - **Local model** — Ollama / LM Studio / vLLM. Slower to set up but no API cost.
- ~5 GB disk space for QwenPaw + dependencies.

---

## 1. Install QwenPaw (10 minutes)

You already have it cloned at `~/Documents/Github/QwenPaw/`. Install in editable mode so you can poke at the source.

```bash
cd ~/Documents/Github/QwenPaw
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .            # editable install
qwenpaw --version           # should print 1.1.6b1 or similar
```

**Common gotchas:**

- `playwright` is a heavy dep. If install hangs on it, run `pip install -e . --no-deps` then `pip install agentscope==1.0.19.post1 agentscope-runtime==1.1.4 httpx packaging` and add the rest manually as needed.
- `onnxruntime<1.24` — if pip resolves wrong, force `pip install 'onnxruntime<1.24'`.
- Apple Silicon: most things work; if you hit `lark-oapi` or `wecom-aibot-python-sdk` issues, you can comment them out of `pyproject.toml` for local dev (you don't need them for QwenPaw to run).

Initialize:

```bash
qwenpaw init --defaults
```

This creates `~/.qwenpaw/` and `~/.qwenpaw.secret/`.

Verify the file layout:

```bash
ls ~/.qwenpaw/
# expect: config.json, workspaces/, ...

ls ~/.qwenpaw.secret/
# expect: providers.json, envs.json
```

---

## 2. First chat (15 minutes)

Start the console:

```bash
qwenpaw app
```

You'll see something like:

```
INFO:     Uvicorn running on http://0.0.0.0:8088
```

Open http://127.0.0.1:8088/ in your browser.

**Wire up your model:**

1. Click **Settings → Models** in the sidebar.
2. Pick a provider (DashScope / OpenAI / Together / etc.).
3. Paste your API key.
4. Enable the provider and pick a model (e.g., `qwen-max-latest` for DashScope, `gpt-4o-mini` for OpenAI, `Qwen/Qwen2.5-72B-Instruct-Turbo` for Together).
5. Save.

**Then chat:**

1. Click the chat icon. Type "hi". Press send.
2. You should get a response within a few seconds.

**If chat fails:**
- Check the console terminal for stack traces.
- Most common: API key wrong scope, or model name typo. Fix in Settings → Models.

✅ **Spike 0 passes when you have a working chat.** Don't move on until this works.

---

## 3. Spike 1 — Install the bundled example plugin (15 minutes)

Verifies the plugin install pipeline works end-to-end.

```bash
cd ~/Documents/Github/QwenPaw/plugins/tool/gpt-image2
qwenpaw plugin install . --force
qwenpaw plugin list
# expect: gpt-image2-tool listed
```

Restart the console (`Ctrl+C`, then `qwenpaw app`). The plugin should now be enabled. Open the console UI → Settings → Tools → confirm `generate_image_gpt` is in the tool list (it'll be disabled by default; you'd need an OpenAI key to actually use it).

✅ **Spike 1 passes when `qwenpaw plugin list` shows the plugin and the tool appears in Settings.**

---

## 4. Spike 2 — Tier 1 hello-world backend plugin (30 minutes)

Tests: `register_startup_hook`, plugin discovery, plugin reload.

```bash
mkdir -p ~/dev/pg-test/hello-plugin
cd ~/dev/pg-test/hello-plugin
```

Create `plugin.json`:

```json
{
  "id": "hello-pg",
  "name": "Hello PG",
  "version": "0.0.1",
  "description": "Smoke-test plugin — prints on startup.",
  "author": "you",
  "entry": { "backend": "plugin.py" },
  "dependencies": [],
  "min_version": "1.1.5"
}
```

Create `plugin.py`:

```python
import logging
from qwenpaw.plugins.api import PluginApi

log = logging.getLogger("hello-pg")
log.setLevel(logging.INFO)

class HelloPlugin:
    async def register(self, api: PluginApi):
        api.register_startup_hook(
            "hello_startup",
            self._on_startup,
            priority=100,
        )

    async def _on_startup(self):
        log.info("HelloPlugin: startup hook fired ✓")
        print("[hello-pg] startup hook fired", flush=True)

plugin = HelloPlugin()
```

Install:

```bash
qwenpaw plugin install ~/dev/pg-test/hello-plugin --force
qwenpaw plugin list
```

Restart `qwenpaw app`. Watch the terminal — you should see `[hello-pg] startup hook fired`.

✅ **Spike 2 passes when you see the startup line in the QwenPaw stdout.**

If it doesn't fire: confirm `plugin = HelloPlugin()` is at module level (not inside `if __name__ == "__main__"`) and `register` is `async`.

---

## 5. Spike 3 — Tier 4 frontend tool renderer (1-2 hours)

Tests: `window.QwenPaw.registerToolRender`, custom UI rendering inline in chat.

This requires a build step (TypeScript → bundled JS). Use **esbuild** for simplicity.

```bash
mkdir -p ~/dev/pg-test/render-plugin/frontend/src
cd ~/dev/pg-test/render-plugin
```

Create `plugin.json`:

```json
{
  "id": "render-pg",
  "name": "Render Smoke Test",
  "version": "0.0.1",
  "description": "Smoke test for registerToolRender.",
  "author": "you",
  "entry": { "frontend": "frontend/dist/index.js" },
  "dependencies": [],
  "min_version": "1.1.5"
}
```

Create `frontend/package.json`:

```json
{
  "name": "render-pg-frontend",
  "version": "0.0.1",
  "private": true,
  "scripts": { "build": "esbuild src/index.tsx --bundle --format=esm --outfile=dist/index.js --external:react --external:react-dom" },
  "devDependencies": {
    "esbuild": "^0.21.0",
    "typescript": "^5.0.0",
    "@types/react": "^18.0.0"
  }
}
```

Create `frontend/src/index.tsx`:

```tsx
// React/antd come from the host — declare so TS doesn't complain.
declare const window: any;
const { React, antd } = window.QwenPaw.host;
const { Card, Tag } = antd;

function HelloToolCard(props: any) {
  const data = props.result ?? props;
  return (
    <Card title="Hello from a custom renderer 👋" style={{ marginTop: 12 }}>
      <Tag color="green">It works.</Tag>
      <pre style={{ fontSize: 11, marginTop: 8 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </Card>
  );
}

window.QwenPaw.registerToolRender?.("render-pg", {
  // Replace the renderer for any tool named "execute_shell_command"
  // — easy to trigger with "run `ls -la`" in chat.
  execute_shell_command: HelloToolCard,
});

console.info("[render-pg] frontend registered.");
```

Build:

```bash
cd frontend
npm install
npm run build
ls dist/
# expect: index.js
```

Install + restart QwenPaw:

```bash
cd ..
qwenpaw plugin install ~/dev/pg-test/render-plugin --force
# in another terminal:
# Ctrl-C qwenpaw app, then qwenpaw app
```

In the console, hard-refresh the browser (`Cmd+Shift+R`). Then in chat ask: "run ls -la in the cwd".

When the agent calls `execute_shell_command`, you should see the green "Hello from a custom renderer 👋" card instead of the default tool-call card.

✅ **Spike 3 passes when the custom card appears.** This validates Tier 4.

If it doesn't appear:
- Open browser devtools console; look for `[render-pg] frontend registered.` log.
- Look for a `[plugin:render-pg] registerToolRender → ...` log from the host.
- If neither: the bundle didn't load. Confirm `frontend/dist/index.js` exists and `plugin.json.entry.frontend` points at the right relative path.

---

## 6. Spike 4 — Tier 2 minimal custom ACP runner (2-3 hours)

Tests: writing a Python ACP server, registering it as a runner via `save_agent_config`, and delegating to it from chat.

This is the trickiest spike. Plan to take an afternoon.

### 6a. Tiny ACP echo server

```bash
mkdir -p ~/dev/pg-test/acp-plugin/echo_runner
cd ~/dev/pg-test/acp-plugin/echo_runner
```

Create `__main__.py`:

```python
"""Tiny ACP runner — echoes the prompt with a prefix."""
import asyncio, uuid
from acp import Agent, AgentCapabilities, NewSessionResponse, PromptResponse
from acp.runtime import run_agent
from acp.updates import update_agent_message, text_block

class EchoAgent(Agent):
    async def initialize(self, params):
        return AgentCapabilities(
            load_session=False,
            session_capabilities={"prompts": True, "tools": False},
        )

    async def new_session(self, params):
        return NewSessionResponse(session_id=str(uuid.uuid4()), config_options=[])

    async def prompt(self, params):
        text = ""
        # ACP protocol delivers the user prompt as a list of content blocks
        for blk in (params.prompt or []):
            if hasattr(blk, "text"):
                text += blk.text
        reply = f"[echo] You said: {text}"
        # Stream in chunks of 8 chars so you can SEE streaming working.
        for i in range(0, len(reply), 8):
            await self._conn.session_update(
                session_id=params.session_id,
                update=update_agent_message(text_block(reply[i:i+8])),
            )
            await asyncio.sleep(0.05)
        return PromptResponse(stop_reason="end_turn")

if __name__ == "__main__":
    asyncio.run(run_agent(EchoAgent(), use_unstable_protocol=True))
```

> **Note:** The exact attribute names on `params` (`params.prompt`, `params.session_id`) are inferred from QwenPaw's reference server at `src/qwenpaw/agents/acp/server.py:513-607`. If your ACP SDK version names them differently, adjust accordingly.

### 6b. Backend plugin that registers the runner

Back up one dir to `~/dev/pg-test/acp-plugin/`:

`plugin.json`:
```json
{
  "id": "echo-pg",
  "name": "Echo ACP Runner",
  "version": "0.0.1",
  "description": "Smoke test for custom ACP runners.",
  "author": "you",
  "entry": { "backend": "plugin.py" },
  "dependencies": [],
  "min_version": "1.1.5"
}
```

`plugin.py`:
```python
"""Register an 'echo' ACP runner at startup, scoped to all configured agents."""
import json, sys
from pathlib import Path
from qwenpaw.plugins.api import PluginApi

PLUGIN_ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

class EchoRunnerPlugin:
    async def register(self, api: PluginApi):
        api.register_startup_hook(
            "echo_runner_install",
            self._install_runner,
            priority=100,
        )

    async def _install_runner(self):
        # Lazy import — the plugin loads before some QwenPaw modules
        from qwenpaw.config.config import (
            load_agent_config, save_agent_config,
            ACPAgentConfig, ACPConfig,
        )
        # Walk every workspace under ~/.qwenpaw/workspaces/
        from qwenpaw.constant import WORKING_DIR
        ws_root = Path(WORKING_DIR).expanduser() / "workspaces"
        if not ws_root.exists():
            print("[echo-pg] no workspaces dir yet; skipping", flush=True)
            return
        for agent_dir in ws_root.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_id = agent_dir.name
            cfg = load_agent_config(agent_id)
            cfg.acp = cfg.acp or ACPConfig()
            cfg.acp.agents["echo-pg"] = ACPAgentConfig(
                enabled=True,
                command=PYTHON,
                args=["-m", "echo_runner"],
                env={"PYTHONPATH": str(PLUGIN_ROOT)},
                trusted=True,
                tool_parse_mode="call_title",
                stdio_buffer_limit_bytes=10 * 1024 * 1024,
            )
            save_agent_config(agent_id, cfg)
            print(f"[echo-pg] registered echo-pg runner for agent {agent_id}", flush=True)

plugin = EchoRunnerPlugin()
```

Install + restart:

```bash
qwenpaw plugin install ~/dev/pg-test/acp-plugin --force
# Ctrl-C, qwenpaw app
```

You should see the `[echo-pg] registered echo-pg runner for agent ...` log.

In QwenPaw chat, ask the agent:
> "Use delegate_external_agent to start a session with runner echo-pg, message 'hello world'"

The agent should call the tool. You should see streaming `[echo] You said: hello world` chunks come back.

✅ **Spike 4 passes when echo streams back into chat.** This validates Tier 2.

Common failures:
- `PYTHONPATH` not picked up → use absolute module path: `args=["-c", f"import sys; sys.path.insert(0, '{PLUGIN_ROOT}'); from echo_runner.__main__ import *"]`. Cleaner long-term: package as a real Python package with `pyproject.toml` and `pip install -e .` in the venv.
- ACP version mismatch → check `pip show agent-client-protocol` matches QwenPaw's pin (≥0.9.0).
- The runner spawns but errors silently → check `~/.qwenpaw/logs/` (or wherever QwenPaw writes ACP subprocess stderr) and the QwenPaw stdout.

---

## 7. Spike 5 — Tier 3 minimal custom MCP server (1-2 hours)

Tests: writing a Python MCP server, registering it via `agent.json.mcp_clients`, calling its tool from chat.

```bash
mkdir -p ~/dev/pg-test/mcp-plugin
cd ~/dev/pg-test/mcp-plugin
```

`plugin.json`:
```json
{
  "id": "echo-mcp",
  "name": "Echo MCP",
  "version": "0.0.1",
  "description": "Smoke test for custom MCP server registration.",
  "author": "you",
  "entry": { "backend": "plugin.py" },
  "dependencies": [],
  "min_version": "1.1.5"
}
```

`mcp_server.py`:
```python
"""Tiny MCP server with one tool."""
import asyncio
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

server = Server("echo-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(
        name="echo",
        description="Echoes its input back. Smoke test.",
        inputSchema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "echo":
        return [TextContent(type="text", text=f"[mcp-echo] {arguments['text']}")]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write,
            InitializationOptions(
                server_name="echo-mcp",
                server_version="0.0.1",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

`plugin.py`:
```python
"""Register an MCP server in agent.json.mcp_clients on startup."""
import sys
from pathlib import Path
from qwenpaw.plugins.api import PluginApi

PLUGIN_ROOT = Path(__file__).resolve().parent

class EchoMCPPlugin:
    async def register(self, api: PluginApi):
        api.register_startup_hook(
            "echo_mcp_install",
            self._install,
            priority=100,
        )

    async def _install(self):
        from qwenpaw.config.config import (
            load_agent_config, save_agent_config,
            MCPClientConfig,
        )
        from qwenpaw.constant import WORKING_DIR
        ws_root = Path(WORKING_DIR).expanduser() / "workspaces"
        if not ws_root.exists():
            return
        for agent_dir in ws_root.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_id = agent_dir.name
            cfg = load_agent_config(agent_id)
            cfg.mcp = cfg.mcp or {}
            cfg.mcp["echo-mcp"] = MCPClientConfig(
                name="echo-mcp",
                enabled=True,
                transport="stdio",
                command=sys.executable,
                args=[str(PLUGIN_ROOT / "mcp_server.py")],
                env={},
            )
            save_agent_config(agent_id, cfg)
            print(f"[echo-mcp] registered for agent {agent_id}", flush=True)

plugin = EchoMCPPlugin()
```

> **Caveat:** the exact `MCPClientConfig` field names should be verified against `qwenpaw.config.config` — they may differ slightly (e.g. `cwd`, `headers`, etc.). Open `src/qwenpaw/config/config.py` and search for `MCPClientConfig` — copy the field names exactly.

Make sure `mcp` Python package is installed:
```bash
pip install mcp
```

Install + restart QwenPaw. In chat: "use the mcp__echo-mcp__echo tool with text='hi'". You should see `[mcp-echo] hi` come back.

✅ **Spike 5 passes when the MCP tool call returns the echoed text.** This validates Tier 3.

---

## 8. After all five spikes pass

You now have proof that:
- Tier 1 (backend plugin + startup hook) works.
- Tier 2 (custom ACP runners with fresh-context subprocesses + streaming) works.
- Tier 3 (custom MCP server with custom tools) works.
- Tier 4 (frontend tool renderer) works.

The remaining tiers don't need spikes:
- Tier 5 (workspace `Claude-Production-Grade-Suite/` directory) is just file I/O.
- Tier 6 (pre-rendered skills) is just text generation at install time.

**Next step:** start Phase 1 of `08_full_parity_architecture.md` — the real plugin skeleton. The first specialist runner to wire up should be `polymath` (read-only dialogue, no tool dispatch needed) or `code-reviewer` (read-only analysis). That keeps the test loop tight while you debug the orchestrator.

---

## Common issues & escape hatches

| Symptom | Likely cause | Fix |
|---|---|---|
| `pip install -e .` hangs | playwright download | Run `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pip install -e .` |
| `qwenpaw app` boots but UI is blank | Frontend bundle missing | The pip wheel ships pre-built; if installed from source, build with `cd console && npm install && npm run build` |
| Chat sends but no response | Provider key wrong / model name typo | Settings → Models → re-test |
| Plugin registered but never loads | `plugin = X()` not at module level | Move out of `if __name__ == "__main__"` |
| Frontend renderer never fires | Bundle path / hard-refresh needed | Check browser devtools for `[plugin:<id>] registerToolRender → ...` log |
| ACP runner spawns but errors silently | Stdio buffer overflow / Python import path | Increase `stdio_buffer_limit_bytes`; use absolute Python module paths |
| MCP tool not in tool list | `qwenpaw mcp` config not picked up | Restart `qwenpaw app`; confirm `~/.qwenpaw/workspaces/<id>/agent.json` shows your entry |
| Class hook never fires | Hook name collision / wrong type | Use unique `hook_name`; verify `pre_reply` etc. spelling against `_react_agent_base.py:21-31` |

When stuck, the source is your friend. Useful greps:

```bash
cd ~/Documents/Github/QwenPaw/src
grep -rn "register_startup_hook" --include="*.py" | head
grep -rn "ACPAgentConfig" --include="*.py" | head
grep -rn "MCPClientConfig" --include="*.py" | head
grep -rn "register_class_hook" --include="*.py" | head
```

The reference plugin at `~/Documents/Github/QwenPaw/plugins/tool/gpt-image2/` is the canonical Tier 1 example. The reference ACP server at `~/Documents/Github/QwenPaw/src/qwenpaw/agents/acp/server.py` is the canonical Tier 2 example. The reference frontend host code at `~/Documents/Github/QwenPaw/console/src/plugins/hostExternals.ts` is the canonical Tier 4 contract.
