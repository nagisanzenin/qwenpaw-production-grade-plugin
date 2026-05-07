# Troubleshooting

Failure modes we've actually seen during install + first-run, with the one-line fix for each. Search this file before opening an issue.

`make verify` catches most of these proactively — try it first.

---

## Install-time failures

### `qwenpaw: command not found`

Your QwenPaw venv isn't active in the current shell.

```bash
source ~/Documents/Github/QwenPaw/.venv/bin/activate
which qwenpaw   # should print …/.venv/bin/qwenpaw
```

If `.venv` doesn't exist, you haven't installed QwenPaw yet — see [PHASE_0_RUNBOOK.md](./PHASE_0_RUNBOOK.md).

To survive future shells, alias it in `~/.zshrc`:
```bash
alias qwen='source ~/Documents/Github/QwenPaw/.venv/bin/activate'
```

### `Plugin validation failed: No module named 'production_grade'`

You hit this on plugin versions before v0.1.1 — the validator imports `plugin.py` standalone without the package on `sys.path`. Fixed in v0.1.1 by lazy-importing inside the startup callback after pushing the plugin root onto `sys.path`.

```bash
cd ~/Documents/Github/qwenpaw-production-grade-plugin
git pull
make install
```

### `QwenPaw web console is not available`

You installed QwenPaw from source (`pip install -e .`) instead of from PyPI. The wheel ships a prebuilt console; the editable install doesn't.

```bash
cd ~/Documents/Github/QwenPaw/console
npm ci             # if no package-lock.json, use: npm install
npm run build      # ~30s
# Ctrl-C qwenpaw app, then restart
qwenpaw app
```

If `npm` itself is missing: `brew install node` (macOS) and retry.

### `make: command not found` (or no Makefile target works)

Either you're not in the plugin repo dir, or `make` isn't installed.

```bash
cd ~/Documents/Github/qwenpaw-production-grade-plugin
which make            # macOS ships make; Linux: apt install make
make help             # lists every available target
```

If `make` is unavailable, every target has a Python equivalent:
- `make install` → `qwenpaw plugin install . --force`
- `make verify` → `bash scripts/verify.sh`
- `make port-clean` → `python3 -m production_grade.port_from_upstream --clean`

---

## Post-install: nothing happens at startup

### Startup hook silent — no `[production-grade] …` in stdout

Three causes, in order of likelihood.

1. **You didn't actually restart `qwenpaw app`.** The startup hook fires once at app boot. `qwenpaw plugin install …` does NOT trigger it. Ctrl-C and restart.

2. **Plugin is installed but disabled.**
   ```bash
   qwenpaw plugin list
   ```
   Look for `production-grade` with an enabled flag. If disabled:
   ```bash
   qwenpaw plugin enable production-grade
   ```

3. **Plugin is installed and enabled, but the hook crashed silently.** Run `qwenpaw app` in a fresh terminal and watch all stdout. Look for `WARN install skipped:` lines. The exception message tells you what failed (usually a path issue). File an issue with the message.

### Skills aren't on disk

```bash
ls ~/.qwenpaw/workspaces/*/skills/ 2>/dev/null | sort -u
```

Should list 14 dirs. If empty:

- Did the startup hook fire? See above.
- Is your workspace named `default`? The installer iterates every dir under `~/.qwenpaw/workspaces/` — but if QwenPaw hasn't created a workspace yet, there's nothing to install into. Run `qwenpaw init --defaults` once, then restart `qwenpaw app`.

### QwenPaw UI Skills tab shows nothing for production-grade

This was the v0.1.0 bug — installer copied SKILL.md to disk but didn't update `<workspace>/skill.json` (the per-agent manifest QwenPaw reads). Fixed in v0.1.1.

```bash
# Confirm v0.1.1 (or later) is installed
qwenpaw plugin list | grep production-grade

# If still on v0.1.0, upgrade:
cd ~/Documents/Github/qwenpaw-production-grade-plugin
git pull
make install
# restart qwenpaw app
make verify
```

After restart and a hard browser refresh (`Cmd+Shift+R`), the 14 skills should appear in Settings → Skills.

If they still don't, manually re-enable each:
```bash
for s in production-grade polymath product-manager solution-architect software-engineer frontend-engineer qa-engineer security-engineer code-reviewer devops sre technical-writer data-scientist skill-maker; do
  qwenpaw skills enable "$s" --agent-id default
done
```

---

## In-chat: methodology not engaging

### `/production-grade` returns SKILL.md raw text instead of running the methodology

You're seeing this:
```
"type": "text",
"text": "---\nname: production-grade\n…
```

That means QwenPaw routed your `/`-prefixed message to `read_file` instead of injecting the body. Two workarounds:

1. **Use the skill name without leading slash** — describe the task in plain English and the model will autoload the matching skill via its description text:
   ```
   I want to build a production-grade Tasks CRUD API at ~/scratch/tasks-api/.
   ```
2. **If you want the slash form**, follow it with concrete arguments so QwenPaw's `_maybe_inject_skill` injects rather than reads:
   ```
   /production-grade build me a Tasks CRUD API
   ```
   (slash + space + words → injection; slash alone → file dump in some channels.)

### Reply doesn't have visual-identity headers

The agent loaded the SKILL.md but isn't following the Visual Identity protocol. Two fixes:

- Add explicit guidance: `Use the Visual Identity protocol headers (━━━ Role ━━━)`.
- Confirm the `/skills` listing includes `production-grade` — if missing, the body wasn't injected at all (re-run `make verify`).

### Agent calls `Agent(prompt=…)` or `AskUserQuestion(…)` and stalls

The model is trying to invoke Claude Code primitives that don't exist in QwenPaw. The skill body has `<!-- v0.1: do this work yourself -->` hints prefixed to those calls, but some models miss them. Reply:

```
do that work yourself in this turn — there are no subagents in v0.1.
For decisions, render numbered options in plain Markdown and I'll reply with the option name.
```

### Agent ignores cwd/project-root and writes to wrong dir

Tell it once at the start: `the project root for this run is /absolute/path/here` — the orchestrator skill body should pick that up and use it for the workspace bootstrap.

### `tavily_search` not found / Freshness Protocol skipped

You don't have a Tavily API key configured.

```bash
# Configure once via QwenPaw Settings → Models → MCP, or via env:
export TAVILY_API_KEY='your-key'
# Restart qwenpaw app
```

Without it, the Freshness Protocol degrades silently; the rest of the pipeline runs fine.

---

## When everything else has failed

```bash
# Capture every relevant signal
{
  echo "=== qwenpaw ==="; which qwenpaw; qwenpaw --version
  echo "=== plugin list ==="; qwenpaw plugin list
  echo "=== plugin paths ==="; ls -la ~/.claude/plugins/ 2>/dev/null
  echo "=== workspaces ==="; ls -la ~/.qwenpaw/workspaces/
  echo "=== skills on disk ==="; ls ~/.qwenpaw/workspaces/*/skills/ 2>/dev/null
  echo "=== skill manifest ==="; cat ~/.qwenpaw/workspaces/default/skill.json 2>/dev/null | head -100
  echo "=== verify ==="; bash scripts/verify.sh
} > /tmp/pg-debug.txt 2>&1
```

Open an issue with `/tmp/pg-debug.txt` attached.
