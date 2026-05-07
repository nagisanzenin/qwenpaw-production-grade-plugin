# Migration Plan: production-grade → QwenPaw

> Concrete, phased plan for porting `nagisanzenin/claude-code-production-grade-plugin` v5.4.0 onto QwenPaw 1.1.5+. Pairs with `05_compatibility_matrix.md`.

---

## Decisions to lock in before coding

1. **Orchestration model** — Option A (single-agent walks the pipeline) **OR** Option B (peer multi-agent). This document assumes **Option A** for v1.0 of the QwenPaw port; Option B is sketched as a v2.0 milestone.
2. **Languages** — ship **English-only** SKILL.md files for v1.0 (skills.en.md spec doesn't define `-en/-zh`; Chinese can be added later via `agent.json.language` or a separate variant set).
3. **Distribution** — GitHub repo + `qwenpaw plugin install <git-url>`. No marketplace integration in v1.0.
4. **QwenPaw version target** — pin `qwenpaw>=1.1.5,<1.2`. Verify `agentscope` and `agentscope-runtime` versions in QwenPaw's `pyproject.toml` before pinning.
5. **`/mission` reuse** — investigate during phase 0 whether QwenPaw's built-in `/mission` mode (commands.en.md:687–891) covers Full Build well enough to skip the orchestrator skill entirely.

---

## Phase 0 — Discovery (1–2 days)

**Goal:** confirm the port is feasible at the level of detail we've assumed; find any blocker.

### 0.1 Spike: install QwenPaw locally

```bash
cd ~/Documents/Github/QwenPaw
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
qwenpaw init
qwenpaw skills list
qwenpaw plugin list
```

Confirm:
- [ ] `qwenpaw` CLI runs.
- [ ] Built-in skills are listed.
- [ ] `~/.qwenpaw/` workspace structure created as documented in config.en.md:147–204.

### 0.2 Spike: build and install the example plugin

```bash
cd ~/Documents/Github/QwenPaw/plugins/tool/gpt-image2
qwenpaw plugin install .
qwenpaw plugin list
```

Confirm:
- [ ] `plugin.json` schema is exactly as we documented.
- [ ] `PluginApi.register_startup_hook` fires.
- [ ] `register_control_command` works (or skip — undocumented).

### 0.3 Spike: write a one-liner SKILL.md and load it

```bash
mkdir -p ~/.qwenpaw/workspaces/<agent_id>/skills/hello
cat > ~/.qwenpaw/workspaces/<agent_id>/skills/hello/SKILL.md <<'EOF'
---
name: hello
description: Test skill that greets the user.
---
# Hello
Just say "hello" back.
EOF
qwenpaw skills enable hello --agent-id <agent_id>
```

Open the QwenPaw web console → start a chat → type `/hello`. Confirm the body is loaded into the model's context.

### 0.4 Spike: `/mission` exploration

Run a `/mission` flow end-to-end in QwenPaw with a small task. Compare the output to what production-grade's "Full Build" produces. **If `/mission` already does PRD → worker → verifier well, the port reduces to "ship our protocols and specialists; reuse `/mission` for the pipeline".** Document the outcome.

### 0.5 Spike: monkey-patch hookability

Write a tiny throwaway plugin that monkey-patches `AgentRunner.query_handler` to prepend a fixed string to every prompt. Confirm it fires on **first prompt of a session** and **every subsequent prompt**.

```python
# plugins/test/plugin.py
from qwenpaw.plugins.api import PluginApi

class TestPlugin:
    def register(self, api: PluginApi):
        api.register_startup_hook(
            hook_name="test_patch",
            callback=self._patch,
            priority=50,
        )
    def _patch(self):
        from qwenpaw.app.runner.runner import AgentRunner
        orig = AgentRunner.query_handler
        async def patched(self_, request, *a, **kw):
            print(f"[TestPlugin] prompt arrived: {request}")
            return await orig(self_, request, *a, **kw)
        AgentRunner.query_handler = patched

plugin = TestPlugin()
```

**Pass criteria:** every prompt prints to QwenPaw's stdout. If yes, the SessionStart and UserPromptSubmit production-grade hooks have a clean port path.

### 0.6 Spike: AgentScope hook reach (optional)

If we discover we need per-tool hooks (we don't think production-grade does, but verify), register an instance hook:

```python
# inside our plugin's startup
from qwenpaw.agents.react_agent import QwenPawAgent
# ... patch QwenPawAgent.__init__ to call self.register_instance_hook(...)
```

Confirm `pre_reasoning`, `pre_reply`, `post_acting`, `post_reply` all fire (react_agent.py:446–487). **Skip this spike if Phase 0.5 confirms `query_handler` is enough.**

**Phase 0 exit gate:** all spikes pass and decisions A–E are recorded in `decisions.md`.

---

## Phase 1 — Skeleton (2–3 days)

**Goal:** produce a minimal QwenPaw plugin that installs, enables, and loads two stub skills.

### 1.1 Repo layout

```
qwenpaw-production-grade-plugin/
├── README.md                        ← exists
├── 05_compatibility_matrix.md
├── 06_migration_plan.md
├── 07_gotchas_and_risks.md
├── decisions.md                      ← Phase-0 outputs
├── pyproject.toml                    ← package metadata, deps
├── plugin.json                       ← QwenPaw plugin manifest
├── plugin.py                         ← PluginApi entry
├── production_grade/                 ← Python package
│   ├── __init__.py
│   ├── activation_rules.py           ← UserPromptSubmit logic
│   ├── session_guard.py              ← SessionStart logic
│   ├── monkey_patch.py               ← runner integration
│   └── protocols.py                  ← protocol-loading helpers
├── skills/                           ← shipped SKILL.md files
│   ├── production-grade/SKILL.md
│   ├── polymath/SKILL.md
│   ├── product-manager/SKILL.md
│   ├── solution-architect/SKILL.md
│   ├── software-engineer/SKILL.md
│   ├── frontend-engineer/SKILL.md
│   ├── qa-engineer/SKILL.md
│   ├── security-engineer/SKILL.md
│   ├── code-reviewer/SKILL.md
│   ├── devops/SKILL.md
│   ├── sre/SKILL.md
│   ├── technical-writer/SKILL.md
│   ├── data-scientist/SKILL.md
│   └── skill-maker/SKILL.md
├── protocols/                        ← shared protocols (read by skills)
│   ├── ux-protocol.md
│   ├── input-validation.md
│   ├── tool-efficiency.md
│   ├── visual-identity.md
│   ├── freshness-protocol.md
│   ├── receipt-protocol.md
│   ├── boundary-safety.md
│   └── conflict-resolution.md
├── activation-rules.json
└── tests/
    ├── test_activation_rules.py
    └── test_session_guard.py
```

### 1.2 `plugin.json` (QwenPaw form)

```json
{
  "id": "production-grade",
  "name": "Production-Grade",
  "version": "0.1.0-port",
  "description": "Port of the Claude Code production-grade plugin to QwenPaw.",
  "author": "nagisanzenin (port: <your-name>)",
  "entry": { "backend": "plugin.py" },
  "dependencies": [],
  "min_version": "1.1.5",
  "meta": {
    "license": "MIT",
    "keywords": [
      "production-grade","saas","orchestrator","full-stack",
      "meta-skill","pipeline","devops","architecture",
      "testing","security","sre","ai","ml","llm"
    ],
    "homepage": "https://github.com/nagisanzenin/qwenpaw-production-grade-plugin"
  }
}
```

### 1.3 `plugin.py` (PluginApi entry)

```python
"""QwenPaw plugin entry for production-grade."""
from __future__ import annotations
from pathlib import Path
from qwenpaw.plugins.api import PluginApi
from production_grade.monkey_patch import patch_query_handler
from production_grade.session_guard import build_guard

ROOT = Path(__file__).parent
SKILLS_DIR = ROOT / "skills"
PROTOCOLS_DIR = ROOT / "protocols"

class ProductionGradePlugin:
    def register(self, api: PluginApi):
        api.register_startup_hook(
            hook_name="pg_install_skills_and_patch",
            callback=lambda: self._on_startup(api),
            priority=100,
        )
        api.register_shutdown_hook(
            hook_name="pg_unpatch",
            callback=self._on_shutdown,
            priority=100,
        )

    def _on_startup(self, api: PluginApi):
        # 1. Install skills into the active workspace skill pool
        self._install_skills_to_pool()
        # 2. Patch query_handler for SessionStart + UserPromptSubmit equivalents
        guard = build_guard(plugin_root=ROOT)
        patch_query_handler(guard)

    def _on_shutdown(self):
        # leave skills in place; only undo the patch if needed
        pass

    def _install_skills_to_pool(self):
        # Copy skills/* into ~/.qwenpaw/skill_pool/<name>/SKILL.md
        # if not already present (idempotent).
        ...

plugin = ProductionGradePlugin()
```

### 1.4 Stub skills

Two stubs only — `production-grade/SKILL.md` and `polymath/SKILL.md`. Confirm they show up in `qwenpaw skills list` and that `/production-grade` injects the body into context.

**Phase 1 exit gate:** `qwenpaw plugin install .` and `qwenpaw plugin list` show `production-grade` enabled. `/production-grade` prints the orchestrator skill body in chat.

---

## Phase 2 — Skills content port (3–5 days)

**Goal:** all 14 skills' SKILL.md bodies are ported, with shared protocols read from sibling files.

### 2.1 Frontmatter normalization

For each skill, strip Claude Code-specific fields:
- Remove `allowed-tools` (use `agent.json.tools.builtin_tools` instead, document in install instructions).
- Remove `model` from frontmatter (set globally via `agent.json.active_model`).
- Remove `disable-model-invocation`, `argument-hint`, `arguments`, `paths`, `hooks`.
- Keep `name`, `description`. Add `metadata.qwenpaw.emoji` for the orchestrator (optional).

### 2.2 Shared-protocol mechanism switch

Before:

```markdown
!`cat Claude-Production-Grade-Suite/.protocols/ux-protocol.md 2>/dev/null || true`
```

After (in SKILL.md body):

```markdown
## Required Reading

Before responding to the user, read these protocol files using the `read_file` tool:

1. `<plugin-root>/protocols/ux-protocol.md`
2. `<plugin-root>/protocols/input-validation.md`
3. `<plugin-root>/protocols/tool-efficiency.md`
4. `<plugin-root>/protocols/visual-identity.md`
5. `<plugin-root>/protocols/freshness-protocol.md`
6. `<plugin-root>/protocols/receipt-protocol.md`
7. `<plugin-root>/protocols/boundary-safety.md`
8. `<plugin-root>/protocols/conflict-resolution.md`

(`<plugin-root>` is exposed via the `PG_ROOT` env var that the plugin sets during startup.)
```

The plugin sets `PG_ROOT` at startup (via `os.environ` mutation); skills reference it. Alternative: inline the protocols directly into each SKILL.md body to avoid runtime path dependence (longer files, but zero coupling).

### 2.3 Tool-name substitutions

In each SKILL.md, replace Claude Code tool names with QwenPaw equivalents:

| Find | Replace |
|---|---|
| `Read tool` / `Read(...)` | `read_file tool` |
| `Write tool` / `Write(...)` | `write_file tool` |
| `Edit tool` / `Edit(...)` | `edit_file tool` |
| `Glob tool` | `glob_search tool` |
| `Grep tool` | `grep_search tool` |
| `Bash tool` / `Bash(...)` | `execute_shell_command tool` |
| `WebSearch tool` | `tavily_search MCP tool` |
| `AskUserQuestion(...)` ceremony | plain Markdown options + ask user to reply |
| `TaskCreate`/`TaskUpdate`/`TaskList` | progress messages + receipts |
| `Skill(...)` | "(orchestrator transitions to next phase by reading the next sub-skill body from disk)" |
| `Agent(...)` (Task) | `chat_with_agent` (peer) or `delegate_external_agent` (ACP) |
| `${CLAUDE_SKILL_DIR}` | `${PG_ROOT}` |
| `${CLAUDE_PLUGIN_ROOT}` | `${PG_ROOT}` |

### 2.4 `AskUserQuestion` rewrite

Production-grade uses `AskUserQuestion` heavily for gate ceremonies. QwenPaw has no equivalent primitive. Two replacement patterns:

**Pattern A (plain text + reply parsing):**
```markdown
## GATE 1: Requirements Approval

Choose one:

  1. **Approve** — proceed to architecture phase
  2. **Revise BRD** — request specific changes
  3. **Discuss** — open free-form chat about scope

Type the number (or option name) to continue.
```

**Pattern B (`/approval` integration):**
Hook into QwenPaw's `/approval approve|deny|list|cancel` flow (commands.en.md:639–663). The plugin emits an approval request; the user runs `/approval approve` or `/approval deny`. Cleaner UX but more code.

Recommend: **Pattern A for v1**, Pattern B for v2.

### 2.5 Per-skill validation

For each skill, run the spike from Phase 0.3 (drop into `~/.qwenpaw/skill_pool/<name>/`) and verify the body loads cleanly.

**Phase 2 exit gate:** every SKILL.md ports cleanly; `/<skill>` triggers the body in QwenPaw chat; the skill instructs the model to read the protocol files via `read_file`.

---

## Phase 3 — Activation logic (2–3 days)

**Goal:** session detection and prompt-routing recommendations work end-to-end.

### 3.1 `production_grade/session_guard.py`

```python
"""SessionStart equivalent — detect Claude-Production-Grade-Suite/ on first prompt."""
import json, re, os
from pathlib import Path

SUITE_DIR = "Claude-Production-Grade-Suite"

def build_session_guard(plugin_root: Path):
    """Return a callable that takes a prompt and returns optional system text to prepend."""
    seen_sessions: set[str] = set()

    def guard(session_id: str, cwd: str, prompt: str) -> str | None:
        if session_id in seen_sessions:
            return None
        seen_sessions.add(session_id)
        suite = Path(cwd) / SUITE_DIR
        if not suite.is_dir():
            return None
        adr_count = len(list(suite.rglob("ADR-*.md")))
        receipt_count = len(list(suite.glob(".orchestrator/receipts/*.json")))
        protocol_count = len(list(suite.glob(".protocols/*.md")))
        return _build_guidance(adr_count, receipt_count, protocol_count)

    return guard

def _build_guidance(adr, receipt, protocol):
    return (
        f"# Production-Grade Native Project Detected\n"
        f"This project contains {adr} ADRs, {receipt} pipeline receipts, "
        f"{protocol} protocols. Suggest invoking `/production-grade` to route the user's request."
    )
```

### 3.2 `production_grade/activation_rules.py`

```python
"""UserPromptSubmit equivalent — keyword/regex routing recommendations."""
import json, re
from pathlib import Path

class ActivationMatcher:
    def __init__(self, rules_path: Path):
        with rules_path.open() as f:
            self.rules = json.load(f)["rules"]

    def match(self, prompt: str) -> list[str]:
        suggestions: list[str] = []
        for r in self.rules:
            if any(kw in prompt.lower() for kw in r.get("keywords", [])):
                suggestions.append(self._format(r))
                continue
            if any(re.search(p, prompt, re.I) for p in r.get("intent_patterns", [])):
                suggestions.append(self._format(r))
        return suggestions[:2]  # max 2 per prompt, per activation-rules.json

    @staticmethod
    def _format(rule):
        return f"Suggested skill: /{rule['skill']} — {rule.get('recommendation','')}"
```

### 3.3 `production_grade/monkey_patch.py`

```python
"""Single monkey-patch wrapping both session-guard and activation-rule logic."""
def patch_query_handler(guard, matcher):
    from qwenpaw.app.runner.runner import AgentRunner
    original = AgentRunner.query_handler

    async def patched(self, request, *args, **kwargs):
        prompt = request.input or ""
        cwd = (getattr(request, "context", {}) or {}).get("cwd") or "."
        prepends: list[str] = []
        # SessionStart equivalent (one-shot per session)
        if (g := guard(self.session_id, cwd, prompt)):
            prepends.append(g)
        # UserPromptSubmit equivalent
        if (s := matcher.match(prompt)):
            prepends.extend(s)
        if prepends:
            request.input = "\n\n".join(prepends) + "\n\n---\n\n" + request.input
        return await original(self, request, *args, **kwargs)

    AgentRunner.query_handler = patched
```

> Field names (`request.input`, `self.session_id`) are best-guesses based on Phase 0.5 — verify exact attribute access during the spike and adjust before merging.

### 3.4 Tests

```python
# tests/test_activation_rules.py
def test_full_build_keyword():
    matcher = ActivationMatcher(Path("activation-rules.json"))
    assert "production-grade" in matcher.match("build me a SaaS")[0]

def test_no_match():
    matcher = ActivationMatcher(Path("activation-rules.json"))
    assert matcher.match("what's the weather?") == []
```

**Phase 3 exit gate:** in QwenPaw chat, typing "build me a SaaS" results in a system-prepended recommendation to use `/production-grade`. Entering a directory with `Claude-Production-Grade-Suite/` triggers the project-detection prompt on the first message.

---

## Phase 4 — Pipeline / orchestrator routing (5–7 days)

**Goal:** the orchestrator skill body itself runs the DEFINE → BUILD → HARDEN → SHIP → SUSTAIN pipeline as a single agent.

### 4.1 Rewrite the orchestrator skill body

The Claude Code orchestrator dispatches via the `Skill` tool (`research_notes/01_production_grade_map.md:147–158`):

```
Orchestrator: Skill(skill="production-grade:product-manager", args="DEFINE BRD")
```

In QwenPaw the equivalent is the orchestrator skill body **describing the phase to the model and then telling it to read the next sub-skill body from disk** as the model's next step:

```markdown
# Pipeline phase: DEFINE / Product Manager

You are now executing the Product Manager phase. Read these files in order:

1. `${PG_ROOT}/skills/product-manager/SKILL.md` (the methodology)
2. `${PG_ROOT}/protocols/receipt-protocol.md` (write a receipt when done)

Then perform the phase. When complete, write a receipt at:
`Claude-Production-Grade-Suite/.orchestrator/receipts/T1-product-manager.json`

After the receipt is written, transition to phase: Solution Architect.
```

The orchestrator becomes a **sequential read-and-execute loop** rather than a sub-skill dispatcher. The model handles state via reading and writing receipts.

### 4.2 Receipts & gates

Receipts already exist in production-grade (`research_notes/01_production_grade_map.md:358–380`). Port them verbatim.

Gate ceremonies use Pattern A from §2.4. Code-side, the orchestrator skill body just instructs the model: "After phase X completes, ask the user the gate question and wait for their reply."

### 4.3 Optional: peer-agent mode (Option B)

If we want the production-grade flavour where each specialist is a separate agent:

- Plugin install creates 13 QwenPaw agents (`qwenpaw agents create product-manager-pg`, etc.).
- Each agent has the corresponding SKILL.md preloaded.
- The orchestrator agent uses `chat_with_agent` to invoke specialists.

We will *not* build this for v1. Document it as `docs/multi-agent-mode.md` for v2.

**Phase 4 exit gate:** end-to-end test of the Feature mode (smallest mode) in QwenPaw chat. Confirms:
- [ ] Orchestrator routes through PM → Architect → Engineer → QA.
- [ ] Receipts get written.
- [ ] Gate prompt is shown to user; user reply continues pipeline.

---

## Phase 5 — Marketplace + docs (1–2 days)

### 5.1 README.md

Replace the placeholder with:

- One-paragraph description.
- Install instructions: `qwenpaw plugin install <git-url>`.
- Required setup: `TAVILY_API_KEY` for Freshness Protocol; QwenPaw 1.1.5+; per-agent skill enable.
- Quickstart (paste an example "build me a CRUD API" prompt; show expected output structure).
- Differences from the original Claude Code plugin (link to `05_compatibility_matrix.md`).
- License (MIT, with attribution to the original author).

### 5.2 Release artifact

```bash
git tag v0.1.0-port
git push origin v0.1.0-port
gh release create v0.1.0-port --generate-notes
```

### 5.3 User-facing CHANGELOG.md

Track diff vs. the upstream production-grade releases. (Most upstream changes will need a follow-up port; track them.)

**Phase 5 exit gate:** clean install on a fresh machine following only README instructions succeeds end-to-end.

---

## Phase 6 — QwenPaw-native enhancements (optional, post-v1)

These are not required for parity; they're QwenPaw-only features that production-grade can't have on Claude Code.

| Idea | What it adds |
|---|---|
| Wire Freshness Protocol to `tavily_search` MCP automatically | Drop the manual `TAVILY_API_KEY` setup step |
| Use `/cron` to schedule Production Readiness reviews | Periodic re-audit of long-lived projects |
| Use Channel routing to expose specialists per channel (DingTalk, etc.) | "Ping the security-engineer" from a Slack-like channel |
| ReMeLight long-term memory for cross-project learnings | Cumulative protocol learnings without an external file |
| `/mission` integration | Production-grade orchestration runs inside the built-in Mission Mode runtime |

Track these in `ROADMAP.md`.

---

## Schedule (calendar)

| Phase | Effort | Owner |
|---|---|---|
| 0. Discovery | 1–2 days | Plugin author |
| 1. Skeleton | 2–3 days | Plugin author |
| 2. Skills content port | 3–5 days | Plugin author + LLM-assisted |
| 3. Activation logic | 2–3 days | Plugin author |
| 4. Pipeline routing | 5–7 days | Plugin author + tester |
| 5. Marketplace + docs | 1–2 days | Plugin author |
| **Total v1.0 scope** | **2–3 weeks** elapsed | |
| 6. QwenPaw enhancements | open-ended | Future |

---

## Open questions (must resolve in Phase 0)

1. Does QwenPaw's SKILL.md body honour `${PG_ROOT}` substitution at injection time, or is the body literal? (Probably literal — verify in 0.3.)
2. Is `/mission` a partial replacement for the orchestrator skill?
3. What's the exact attribute path for the user prompt in `request` inside `AgentRunner.query_handler`? (Verify in 0.5.)
4. Is `register_control_command` worth using (vs monkey-patch) given it's source-only-documented? (Default: avoid.)
5. How are skill files distributed — per-agent workspace (`~/.qwenpaw/workspaces/<id>/skills/`) or shared pool (`~/.qwenpaw/skill_pool/`)? Pick the latter for cross-agent availability.
6. Does QwenPaw expose `cwd` to the runtime? (Hooks see `request.context.cwd`?) Confirm in 0.5.
