# qwenpaw-production-grade-plugin

**Turn QwenPaw from "writes code" into "delivers production-ready systems."**

This plugin gives QwenPaw 14 specialist personas (Product Manager, Solution Architect, Software Engineer, QA, Security, DevOps, …) plus 8 shared protocols. When you ask QwenPaw to build something, an **orchestrator** agent dispatches each phase to a fresh specialist subprocess (BRD, ADRs, code, tests, security audit, CI/CD, runbook), then materializes the deliverables on disk. Multi-agent dispatch + Wave-A/B/C parallelism replace the old single-agent walk that would drift after many turns.

Port of the Claude Code [`production-grade`](https://github.com/nagisanzenin/claude-code-production-grade-plugin) plugin (same author, same MIT license).

**Current release:** v0.2.0 — multi-agent ACP dispatch + per-role runner logs + stale-snapshot detector. Tested end-to-end against QwenPaw 1.1.6b1.

---

## Quick install (5 minutes)

**Prerequisites**

- A working QwenPaw `>=1.1.5` install with at least one LLM provider configured (you should already be able to chat with QwenPaw at `http://localhost:<port>`)
- The shell where you'll run `qwenpaw app` has the QwenPaw venv activated — `which qwenpaw` should print a path under your QwenPaw checkout

That's it. The plugin pulls API keys from QwenPaw's secret store automatically — no shell `export` required for runners.

**Install**

```bash
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin
make install
```

`make install` runs `qwenpaw plugin install . --force`, drops a `.dev_source` marker for stale-snapshot detection, then reminds you to restart `qwenpaw app`.

**Restart QwenPaw**

Stop the running `qwenpaw app` (`Ctrl-C` in its terminal) and start it again. You should see this banner near the bottom of the boot output:

```
[production-grade] v0.2.0 starting (plugin root: ...)
[production-grade] using bundled skills+protocols from ...
[production-grade]   ✓ default: 14 skills
[production-grade]   ✓ default: registered 22 ACP runners
[production-grade]   ✓ P3: !`<cmd>` runtime expansion installed
[production-grade]   ✓ P4: session guard + activation rules
[production-grade]   ✓ P2: auto-receipt for delegate_external_agent
[production-grade] specialist runners registered in N workspace(s)
```

**Verify**

```bash
make verify
```

A passing run ends with `0 FAIL, 0 warn — all checks passed`. Any failure prints exactly what to fix.

---

## Your first test (30 seconds)

In the QwenPaw chat, send this **exact prompt** — the activation phrase matters:

```
use /production-grade skill
Build me a small Python CLI that takes a folder of images and resizes them all to a target width. Put it in ~/scratch/img-cli.
```

> **Why "use /production-grade skill"?** The slash command alone (`/production-grade ...`) sometimes lets the orchestrator do the work inline instead of dispatching. Saying "use /production-grade skill" pins the activation. We're working to make this unnecessary, but for now this is the magic phrase.

You should see, in order:

1. The orchestrator calls `delegate_external_agent(runner="pgs-product-manager-a", ...)` — a fresh subprocess spawns, logs land at `~/.qwenpaw/logs/pg-runner-product-manager.log`
2. Then `pgs-solution-architect-a` (architecture / ADRs)
3. Then `pgs-software-engineer-a` (implementation skeleton)
4. **Wave-B in parallel** — `pgs-qa-engineer-a` + `pgs-security-engineer-a` + `pgs-code-reviewer-a` fire concurrently
5. Then `pgs-devops-a`, `pgs-technical-writer-a` as the methodology requires
6. Real files land in `~/scratch/img-cli/` (code, tests, README, Dockerfile)
7. Receipts auto-write to `~/scratch/img-cli/Claude-Production-Grade-Suite/.orchestrator/receipts/`

Watch progress in three places:

```bash
# orchestrator activity
tail -f ~/.qwenpaw/qwenpaw.log

# specialist runner activity (one file per role; PID disambiguates copies)
tail -f ~/.qwenpaw/logs/pg-runner-*.log

# files being written
watch -n 2 'find ~/scratch/img-cli -type f | head'
```

---

## What you get

```
~/scratch/img-cli/
├── pyproject.toml                    ← packaging
├── README.md                         ← usage
├── src/img_cli/
│   ├── __init__.py
│   ├── cli.py                        ← argparse entry
│   └── core.py                       ← resize logic
├── tests/
│   └── test_core.py                  ← unit tests
├── Dockerfile                        ← optional, from devops phase
└── Claude-Production-Grade-Suite/
    └── .orchestrator/
        └── receipts/
            ├── 01-product-manager-….json
            ├── 02-solution-architect-….json
            ├── 03-software-engineer-….json
            └── …                      ← one per phase, recording artifacts + metrics
```

The receipts give you a full audit trail of what each specialist produced and what artifacts the orchestrator wrote on its behalf.

---

## Common operations

| Task | Command |
|---|---|
| Install or reinstall | `make install` |
| Iterate during development (shutdown → install → restart-prompt) | `make dev` |
| Verify everything's wired | `make verify` |
| List registered runners | `make runner-list` |
| Smoke-test a runner standalone | `make runner-smoke` |
| Refresh skills from upstream Claude Code plugin | `make update` |
| Remove plugin | `make uninstall` |
| Show all Make targets | `make help` |

---

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│  user types: use /production-grade skill build me an X      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
            ┌──────────────────────────────┐
            │  ORCHESTRATOR (QwenPaw chat) │  reads dispatch protocol
            │  reads SKILL.md (~7KB        │  from this plugin's
            │  binding-instruction-only)   │  v02_dispatch_preamble.md
            └──────────────┬───────────────┘
                           │
        delegate_external_agent(runner="pgs-product-manager-a", …)
                           ▼
            ┌──────────────────────────────┐    fresh subprocess
            │  pgs-product-manager-a       │    via QwenPaw's ACP
            │  loads role's full SKILL.md  │    spawn_agent_process
            │  + 8 protocols as system     │    (stdio JSON-RPC)
            │  prompt (~62KB)              │
            └──────────────┬───────────────┘
                           │  streams BRD text back
                           ▼
            ┌──────────────────────────────┐
            │  ORCHESTRATOR receives text  │
            │  writes BRD to disk via      │
            │  write_file tool             │
            │  writes receipt.json (P2)    │
            └──────────────┬───────────────┘
                           │  next phase…
```

Key design choices:

- **Orchestrator's SKILL.md is dispatch-only.** Replaced the original 76KB v0.1 body with 7KB of binding-instruction + Phase→Runner mapping, so the model can't get distracted into doing specialist work itself.
- **Specialist methodology lives in each role's own SKILL.md.** The runner subprocess loads it as system prompt. Orchestrator never sees it — keeps signals clean.
- **Per-role copies (`-a`, `-b`, `-c`) for parallelism.** QwenPaw's ACP service can't run two turns of the same `(session, runner)` pair concurrently, so Wave-B (QA + Security + Reviewer) uses `pgs-qa-engineer-a`, `pgs-security-engineer-a`, `pgs-code-reviewer-a` as 3 different runners.
- **API keys flow from QwenPaw's secret store.** The installer reads each workspace's active model, pulls the encrypted API key from `~/.qwenpaw.secret/providers/`, decrypts via QwenPaw's own `secret_store`, and injects into the runner's env per-workspace. No shell `export` required.

---

## Troubleshooting

### Symptoms checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| Orchestrator writes files inline, never dispatches | Activation phrase not strong enough | Use `use /production-grade skill ...` instead of bare `/production-grade ...` |
| `delegate_external_agent` times out at 60s | Runner subprocess died on import | Check `~/.qwenpaw/logs/pg-runner-*.log` for stack trace; usually missing PYTHONPATH after stale install |
| Empty specialist responses | Cross-turn history not flowing | Use `action="start"` for each new phase (this is the default in our preamble) |
| `runner 'pgs-implementation-a' not available` | Orchestrator hallucinating runner name | Restart `qwenpaw app` so the latest preamble loads — see [Stale snapshots](#stale-snapshots) |
| Edits to source not reflected in chat | Snapshot stale | Run `make dev` (shutdown + reinstall + restart-prompt) |

### Stale snapshots

`qwenpaw plugin install . --force` copies your source tree into `~/.qwenpaw/plugins/<id>/` as a snapshot. **Subsequent edits to your source aren't picked up until the next install.** This trips up plugin developers iterating in the source repo.

We ship a stale-snapshot detector that catches this. At every `qwenpaw app` startup, the plugin compares source `.py` mtimes against the snapshot's. If source is newer by >5 seconds, it prints:

```
[production-grade] ⚠  source repo at /path/to/source
[production-grade]    has changes 47s newer than this snapshot.
[production-grade]    Run `make install` (in source) to refresh.
[production-grade]    Otherwise QwenPaw runs stale plugin code.
```

If you see that, run `make dev` (or `make install` + restart manually).

End-users who installed via `qwenpaw plugin install <git-url>` don't have a `.dev_source` marker and never see the warning — intentional.

### Where to look when something fails

1. **Plugin startup banner** — visible in the terminal where `qwenpaw app` runs. If you don't see `[production-grade] v0.2.0 starting`, the plugin didn't load.
2. **`~/.qwenpaw/qwenpaw.log`** — orchestrator-side activity, including LLM token counts, tool calls, cancellations.
3. **`~/.qwenpaw/logs/pg-runner-<role>.log`** — specialist-side activity, including LLM provider/model/base_url, prompt/response sizes, history depth, tracebacks. PID is on every line so concurrent copies are distinguishable.
4. **`make verify`** — automated sanity check. Catches missing artifacts, wrong runner counts, hooks not attached.

If all four look fine but the pipeline misbehaves, file an issue with the relevant `pg-runner-*.log` excerpt attached.

---

## What's in this repo

```
plugin.json, plugin.py            QwenPaw plugin entry — startup hook + diagnostics
production_grade/                 backend Python package
  installer.py                    ports skills/protocols into each workspace
  acp_install.py                  registers pgs-<role>-<copy> ACP runners + env
  hooks.py                        P2 (auto-receipt) + P3 (skill loader) + P4 (session guard)
  specialists/runner.py           the ACP server every runner subprocess runs
  v02_dispatch_preamble.md        the 7KB orchestrator dispatch directive
skills/                           14 specialist SKILL.md files (bundled)
protocols/                        8 shared protocol files (bundled)
scripts/verify.sh                 post-install sanity check
Makefile                          install / dev / verify / port / runner-smoke

CHANGELOG.md                      release history
plans/                            design + research docs
```

---

## Versions and compatibility

| Plugin version | QwenPaw min | Status |
|---|---|---|
| v0.2.0 | 1.1.5 | current — multi-agent dispatch + parallelism |
| v0.1.1 | 1.1.5 | older single-agent walk; still works, less robust |

`make verify` confirms QwenPaw version compatibility.

---

## License

MIT — see [LICENSE](./LICENSE). This plugin ports the upstream Claude Code [`production-grade`](https://github.com/nagisanzenin/claude-code-production-grade-plugin) plugin (also MIT) by the same author.
