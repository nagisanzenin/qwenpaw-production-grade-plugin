# Install

This plugin is a **two-step install**:

1. Make sure you have a local copy of the upstream Claude Code plugin (it's MIT-licensed; the QwenPaw port reads its skill bodies and adapts them at install time).
2. Install this plugin into QwenPaw.

The plugin does **not** bundle the upstream skill content — your local upstream copy is the source of truth, and the adapted output lives in your QwenPaw workspaces under `~/.qwenpaw/workspaces/<agent_id>/skills/`.

---

## Prerequisites

- QwenPaw `>=1.1.5` installed and working (`qwenpaw app` boots, you can chat). If not, follow the QwenPaw quickstart, then come back.
- An LLM provider configured in QwenPaw → Settings → Models.
- Python `>=3.10,<3.14` (already required by QwenPaw).

---

## Step 1 — clone the upstream

The port tool looks for the upstream in this order:

1. `$CLAUDE_PRODUCTION_GRADE_UPSTREAM` env var (absolute path)
2. `~/Documents/Github/claude-code-production-grade-plugin/`
3. Sibling directory next to this repo
4. `~/.claude/plugins/cache/nagisanzenin/production-grade/<version>/`

Pick whichever fits. Easiest:

```bash
mkdir -p ~/Documents/Github
git clone https://github.com/nagisanzenin/claude-code-production-grade-plugin \
  ~/Documents/Github/claude-code-production-grade-plugin
```

If your upstream lives elsewhere:

```bash
export CLAUDE_PRODUCTION_GRADE_UPSTREAM=/abs/path/to/your/upstream
```

---

## Step 2 — install this plugin

Clone this repo, then install:

```bash
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin
qwenpaw plugin install . --force
qwenpaw plugin list
# expect: production-grade listed
```

Restart QwenPaw (`Ctrl-C` and `qwenpaw app` again). The startup hook fires once and you should see:

```
[production-grade] upstream → /Users/.../claude-code-production-grade-plugin
[production-grade]   ✓ default: 14 skills
[production-grade] installed into 1 workspace(s)
```

---

## Verify

In the QwenPaw web console (http://127.0.0.1:8088/), confirm the skills are picked up:

```bash
qwenpaw skills list
```

Should list `production-grade`, `polymath`, `product-manager`, `solution-architect`, `software-engineer`, `frontend-engineer`, `qa-engineer`, `security-engineer`, `code-reviewer`, `devops`, `sre`, `technical-writer`, `data-scientist`, `skill-maker`.

In chat, try the orchestrator:

```
/production-grade
```

You should see the orchestrator's methodology load. Then ask it something concrete:

```
/production-grade  add a basic CRUD endpoint for a "tasks" resource
```

The orchestrator should classify your request into a mode and walk through the appropriate phases.

---

## What works in v0.1

- All 14 specialist SKILL.md bodies installed and routable via `/<skill>`.
- 8 shared protocols installed at `~/.qwenpaw/workspaces/<id>/production-grade-protocols/`.
- Tool-name translation handled (`Read` → `read_file`, `WebSearch` → `tavily_search`, etc.).
- `Claude-Production-Grade-Suite/` workspace bootstrap is done by the orchestrator skill body itself when the user kicks off a build (file ops, runtime-agnostic).

## What's deferred to v0.2+

The matrix in `05_compatibility_matrix.md` and the architecture in `08_full_parity_architecture.md` describe the full 100% retention plan. v0.1 ships the **single-agent walk** subset:

- ❌ No custom ACP runners (specialists run in the same context as the orchestrator → no fresh context per role; long pipelines may drift).
- ❌ No custom MCP server (no `pg__dispatch_specialist`, `pg__ask_user_question`, etc.).
- ❌ No frontend tool renderers (gates render as plain-text option lists; user types the option name to advance).
- ❌ No SessionStart project detection (the orchestrator skill body checks for `Claude-Production-Grade-Suite/` itself if you want it to).
- ❌ No UserPromptSubmit activation rules (you have to type `/production-grade` explicitly).

These are tracked in `08_full_parity_architecture.md` for a future release.

---

## Updating

To pull the latest upstream methodology:

```bash
cd ~/Documents/Github/claude-code-production-grade-plugin
git pull
cd ~/Documents/Github/qwenpaw-production-grade-plugin
qwenpaw plugin install . --force
# restart qwenpaw app
```

The startup hook re-reads the upstream and overwrites the workspace skill files. Any local edits you made to `~/.qwenpaw/workspaces/<id>/skills/<name>/SKILL.md` are lost — keep edits in your upstream fork instead.

---

## Uninstall

```bash
qwenpaw plugin uninstall production-grade
```

Manually clean any leftover workspace files if you want a fresh state:

```bash
rm -rf ~/.qwenpaw/workspaces/*/skills/{production-grade,polymath,product-manager,solution-architect,software-engineer,frontend-engineer,qa-engineer,security-engineer,code-reviewer,devops,sre,technical-writer,data-scientist,skill-maker}
rm -rf ~/.qwenpaw/workspaces/*/production-grade-protocols
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `[production-grade] WARN install skipped: No upstream production-grade plugin found` | upstream not at any expected path | Set `CLAUDE_PRODUCTION_GRADE_UPSTREAM` or clone to the default path |
| `qwenpaw skills list` shows nothing | startup hook didn't fire | Confirm `qwenpaw plugin list` shows `production-grade` enabled; restart `qwenpaw app` |
| `/production-grade` returns no methodology | skill workspace install missing | Check `ls ~/.qwenpaw/workspaces/*/skills/production-grade/`; should contain `SKILL.md` |
| Tool name mismatch errors in chat | port logic missed a translation | Open `production_grade/port_logic.py` and add the tool to `_TOOL_TRANSLATIONS`; reinstall |
| `tavily_search` not found | TAVILY_API_KEY not configured | Set the env var before `qwenpaw app`; without it the Freshness Protocol is skipped |
