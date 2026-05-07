# Install

Two install modes:

- **Bundled (recommended for sharing):** the port has already been run; `skills/` and `protocols/` are committed in this repo. One command installs.
- **Live-port (recommended for the original author syncing with upstream):** the port runs at plugin install time, reading from your local upstream copy.

The plugin auto-detects which mode applies — bundled wins if `skills/` is populated.

---

## Prerequisites

- QwenPaw `>=1.1.5` installed and chat working (`qwenpaw app` boots, you can chat). If not, follow the QwenPaw quickstart first.
- An LLM provider configured in QwenPaw → Settings → Models.
- Python `>=3.10,<3.14`.

---

## Bundled install (3 commands)

```bash
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin
qwenpaw plugin install . --force
```

Restart QwenPaw (`Ctrl-C` and `qwenpaw app` again). On startup you should see:

```
[production-grade] using bundled skills+protocols from /…/qwenpaw-production-grade-plugin
[production-grade]   ✓ default: 14 skills
[production-grade] installed into 1 workspace(s)
```

**If you see "no bundled skills"** — the repo wasn't shipped with the bundled output. Switch to the live-port flow below.

---

## Live-port install (for the upstream author / fresh clones)

You need a local clone of the upstream Claude Code plugin (MIT licensed).

```bash
# 1. clone upstream
mkdir -p ~/Documents/Github
git clone https://github.com/nagisanzenin/claude-code-production-grade-plugin \
  ~/Documents/Github/claude-code-production-grade-plugin

# 2. clone this plugin
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin
qwenpaw plugin install . --force
```

The startup hook resolves upstream in this order:

1. `$CLAUDE_PRODUCTION_GRADE_UPSTREAM` env var
2. `~/Documents/Github/claude-code-production-grade-plugin/`
3. Sibling directory next to this plugin
4. `~/.claude/plugins/cache/nagisanzenin/production-grade/<version>/`

If your upstream lives elsewhere, set the env var before `qwenpaw app`.

Restart QwenPaw. Output:

```
[production-grade] live-porting from upstream at /Users/.../claude-code-production-grade-plugin
[production-grade]   ✓ default: 14 skills
[production-grade] installed into 1 workspace(s)
```

---

## Bundle the port (for the original author)

If you maintain the upstream and want to ship a self-contained release, run the port once and commit the output:

```bash
cd qwenpaw-production-grade-plugin
python -m production_grade.port_from_upstream --clean
git add skills/ protocols/
git commit -m "port: refresh bundled skills + protocols from upstream <commit-sha>"
git tag v0.1.0
git push --follow-tags
```

The `--clean` flag wipes existing `skills/` and `protocols/` first so removed-upstream files don't linger.

After a bundled push, anyone who clones gets the **bundled-install** flow (no upstream clone needed).

---

## Verify

```bash
qwenpaw plugin list
# expect: production-grade

qwenpaw skills list
# expect: production-grade, polymath, product-manager, solution-architect,
# software-engineer, frontend-engineer, qa-engineer, security-engineer,
# code-reviewer, devops, sre, technical-writer, data-scientist, skill-maker

ls ~/.qwenpaw/workspaces/*/skills/
# expect: 14 directories

ls ~/.qwenpaw/workspaces/*/production-grade-protocols/
# expect: 8 .md files
```

In chat:

```
/production-grade
```

Should load the orchestrator skill. Then:

```
/production-grade  add a CRUD endpoint for a "tasks" resource
```

The orchestrator should classify your request and walk through the appropriate phases.

---

## What works in v0.1

- All 14 specialist SKILL.md bodies installed and routable via `/<skill>`.
- 8 shared protocols at `~/.qwenpaw/workspaces/<id>/production-grade-protocols/`.
- Tool-name translation (`Read` → `read_file`, `WebSearch` → `tavily_search`, etc.).
- `Claude-Production-Grade-Suite/` workspace bootstrap done by the orchestrator skill body.

## What's deferred to v0.2+

See `08_full_parity_architecture.md`. v0.1 omits:

- ❌ Custom ACP runners (specialists run in the orchestrator's context).
- ❌ Custom MCP server.
- ❌ Frontend tool renderers (gates show as plain-text option lists).
- ❌ SessionStart project detection.
- ❌ UserPromptSubmit activation rules.

---

## Updating from upstream

If you bundled, just re-run the port and commit:

```bash
cd ~/Documents/Github/claude-code-production-grade-plugin
git pull
cd ~/Documents/Github/qwenpaw-production-grade-plugin
python -m production_grade.port_from_upstream --clean
git add skills/ protocols/
git commit -m "port: refresh from upstream <commit-sha>"
qwenpaw plugin install . --force
# restart qwenpaw app
```

In live-port mode, just `git pull` upstream and `qwenpaw plugin install . --force`.

---

## Uninstall

```bash
qwenpaw plugin uninstall production-grade
```

Manually clean leftover workspace files for a fresh state:

```bash
rm -rf ~/.qwenpaw/workspaces/*/skills/{production-grade,polymath,product-manager,solution-architect,software-engineer,frontend-engineer,qa-engineer,security-engineer,code-reviewer,devops,sre,technical-writer,data-scientist,skill-maker}
rm -rf ~/.qwenpaw/workspaces/*/production-grade-protocols
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No bundled skills/ in this plugin and no upstream … found` | Neither bundled nor upstream available | Run `python -m production_grade.port_from_upstream` (needs upstream cloned) OR set `CLAUDE_PRODUCTION_GRADE_UPSTREAM` |
| `qwenpaw skills list` shows nothing | Startup hook didn't fire | Confirm `qwenpaw plugin list` shows `production-grade` enabled; restart `qwenpaw app` |
| `/production-grade` returns nothing | Skill workspace install missing | `ls ~/.qwenpaw/workspaces/*/skills/production-grade/SKILL.md` should exist |
| Tool-name mismatch in chat | Port logic missed a translation | Open `production_grade/port_logic.py:_TOOL_TRANSLATIONS`; add the mapping; re-port; reinstall |
| `tavily_search` not found | `TAVILY_API_KEY` not set | Set the env var before `qwenpaw app`; without it the Freshness Protocol is skipped |
