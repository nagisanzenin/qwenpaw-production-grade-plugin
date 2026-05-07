# qwenpaw-production-grade-plugin

QwenPaw port of the Claude Code [`production-grade`](https://github.com/nagisanzenin/claude-code-production-grade-plugin) plugin. **14 specialist skills + 8 shared protocols** turn QwenPaw from "writes code" into "delivers production-ready systems" — BRD, ADRs, tested code, security audit, CI/CD, runbook.

**Status:** v0.1.1 — installable. Single-agent walk through the pipeline. Drop-in for QwenPaw `>=1.1.5`.

---

## Quick install (3 minutes)

You need QwenPaw running and a chat session that already works. If you don't have that yet, see [PHASE_0_RUNBOOK.md](./PHASE_0_RUNBOOK.md) first.

```bash
# 1. clone
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin

# 2. install (your QwenPaw venv must be active — `which qwenpaw` should print a path)
make install

# 3. restart QwenPaw so the startup hook fires
#    (Ctrl-C the running `qwenpaw app`, then start it again in the same venv)

# 4. verify everything's wired
make verify
```

A successful `make verify` prints `all checks passed`. If anything fails it tells you exactly what to fix — see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for the full list of known failure modes.

Then in chat:

```
/production-grade  add a basic Tasks CRUD API at ~/scratch/tasks-api/
```

You should see the orchestrator engage with `━━━ Production-Grade ━━━`-style headers, walk through DEFINE → BUILD → HARDEN phases, and produce real artifacts under `~/scratch/tasks-api/Claude-Production-Grade-Suite/`. Verification: `pytest -q` in the project should be green and the receipts dir should have one JSON per completed phase.

---

## What's in here

```
plugin.json, plugin.py            QwenPaw plugin entry
production_grade/                 backend Python package (installer + port logic)
skills/                           14 specialist SKILL.md files (bundled)
protocols/                        8 shared protocol files (bundled)
scripts/verify.sh                 post-install sanity check
Makefile                          install / verify / port / update shortcuts

INSTALL.md                        canonical install path + verify steps
TROUBLESHOOTING.md                every known failure mode + fix
CHANGELOG.md                      release history
PHASE_0_RUNBOOK.md                pre-install: get QwenPaw itself working

plans/                            design + research docs (read for v0.2+ context)
```

---

## Common operations

| What | Command |
|---|---|
| Install or reinstall | `make install` |
| Verify install | `make verify` |
| Refresh skills from upstream | `make update` (pulls upstream, re-ports, reinstalls) |
| Remove plugin | `make uninstall` |
| Show all targets | `make help` |

---

## What v0.1.1 actually does

The plugin's startup hook copies the bundled SKILL.md files into each QwenPaw agent workspace, copies the 8 protocol files alongside them, and registers all 14 skills as `enabled` in the per-agent skill manifest (so they show up in the QwenPaw UI Skills tab).

That's it for v0.1.1. Specifically, **deferred to v0.2+**:

- Custom ACP runners (no fresh context per specialist; long pipelines may drift in single-agent mode).
- Custom MCP server for `pg__dispatch_specialist` / `pg__ask_user_question` etc.
- Frontend tool renderers — gates render as plain-text option lists (you type the option name).
- SessionStart project detection.
- UserPromptSubmit activation rules (must explicitly type `/production-grade`).

The full 100% functional-retention plan is in [`plans/08_full_parity_architecture.md`](./plans/08_full_parity_architecture.md).

---

## License

MIT — see [LICENSE](./LICENSE). This plugin ports the upstream `nagisanzenin/claude-code-production-grade-plugin` (also MIT) by the same author.
