# Install

Single canonical path. The plugin ships with skills + protocols already bundled; one command installs, one command verifies. If anything breaks, [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) covers every known failure.

---

## 0. Prerequisites

You must already have:

- **QwenPaw installed and running.** `qwenpaw app` boots, you can chat with it, an LLM provider is configured under Settings → Models.
- **Python `>=3.10,<3.14`.** QwenPaw's own requirement; this plugin inherits it.
- **The QwenPaw venv active in your shell.** `which qwenpaw` should print a path. If it doesn't, your venv isn't sourced — see TROUBLESHOOTING.md → "qwenpaw not on PATH".

If QwenPaw isn't running yet, see [PHASE_0_RUNBOOK.md](./PHASE_0_RUNBOOK.md). It walks you from zero to working chat.

---

## 1. Install

```bash
git clone https://github.com/nagisanzenin/qwenpaw-production-grade-plugin
cd qwenpaw-production-grade-plugin
make install
```

Under the hood `make install` runs `qwenpaw plugin install . --force` and prints next-step reminders.

You should see in the output:

```
📦 Installing plugin: Production-Grade (production-grade)
🔍 Validating plugin structure...
✓ Plugin installed
```

## 2. Restart QwenPaw

The plugin's install logic runs in a startup hook. The hook fires on app start, so you have to bounce `qwenpaw app`:

```bash
# In the terminal running qwenpaw app:
# Ctrl-C
qwenpaw app
```

Watch the new stdout for:

```
[production-grade] using bundled skills+protocols from /Users/.../qwenpaw-production-grade-plugin
[production-grade]   ✓ default: 14 skills
[production-grade] installed into 1 workspace(s)
```

If you don't see those lines after the restart, the hook didn't fire — see TROUBLESHOOTING.md → "Startup hook silent".

## 3. Verify

```bash
make verify
```

A clean run prints `all checks passed`. The script checks:

- `qwenpaw` is on PATH.
- `production-grade` is in `qwenpaw plugin list`.
- The bundled `skills/` and `protocols/` directories are intact (14 / 8).
- Each QwenPaw workspace has the skills installed under `skills/<name>/SKILL.md`.
- Each workspace's `skill.json` lists all 14 production-grade skills as `enabled`.

If anything fails, the output names the exact remediation — paste it in the [issues tab](https://github.com/nagisanzenin/qwenpaw-production-grade-plugin/issues) if you can't fix it from the message alone.

## 4. Sanity-check in chat

In the QwenPaw web console (default http://127.0.0.1:8088/), hard-refresh the browser (Cmd+Shift+R) so the React app picks up the new skills, then run:

```
/production-grade  in MODE=Explore, give me a 4-5 sentence overview of what you would do if I asked you to build a Tasks CRUD API. Use the Visual Identity protocol headers.
```

The reply should:

- Open with `━━━ Production-Grade ━━━` (or similar Unicode-rule header).
- Mention modes by name (`Full Build`, `Feature`, `Harden`, etc.).
- Mention which specialists it would dispatch.

If the reply is generic and skips the protocol headers, see TROUBLESHOOTING.md → "Methodology not engaged".

## 5. (Optional) Run a real pipeline

Once the smoke test passes, you can drive the full pipeline. Recommended first real test:

```bash
mkdir -p ~/scratch/tasks-api
```

Then in chat:

```
/production-grade

Create a minimal Tasks CRUD API at ~/scratch/tasks-api/.
Stack: Python 3.11+, FastAPI, SQLAlchemy + SQLite, pytest, ruff.
Endpoints: POST/GET /tasks, GET/PATCH/DELETE /tasks/{id}.
Auth: API-key header on writes. Engagement: Standard.
Acceptance: pytest passes; OpenAPI doc renders; ruff clean.
Production-grade deliverables: BRD, ADRs, security audit, runbook, README.
```

Expect 15-30 minutes wall-clock. After completion, audit with:

```bash
ls ~/scratch/tasks-api/Claude-Production-Grade-Suite/.orchestrator/receipts/
cd ~/scratch/tasks-api && pytest -q
```

A healthy run produces 6-12 receipt JSON files (each a phase outcome) and a green pytest.

---

## Updating

Two flavors:

**Just refresh skills from your local upstream and reinstall:**

```bash
make update    # equivalent to: upstream-pull → port-clean → install
```

**Major plugin update (new tag from this repo):**

```bash
cd ~/Documents/Github/qwenpaw-production-grade-plugin
git fetch && git checkout v0.x.y
make install
# restart qwenpaw app
make verify
```

---

## Uninstall

```bash
make uninstall
```

That removes the plugin from QwenPaw but leaves the workspace files alone (so you can reinstall and resume). To wipe the workspace traces too:

```bash
rm -rf ~/.qwenpaw/workspaces/*/skills/{production-grade,polymath,product-manager,solution-architect,software-engineer,frontend-engineer,qa-engineer,security-engineer,code-reviewer,devops,sre,technical-writer,data-scientist,skill-maker}
rm -rf ~/.qwenpaw/workspaces/*/production-grade-protocols
```

Skill manifest entries clean themselves up after the next QwenPaw restart.

---

## For maintainers — re-bundling from upstream

(Skip this section if you're just installing.)

If you maintain the upstream and want to ship a new bundled release:

```bash
cd ~/Documents/Github/qwenpaw-production-grade-plugin
make port-clean              # regenerates skills/ and protocols/ from upstream
git add skills/ protocols/
git commit -m "port: refresh bundled skills + protocols from upstream <sha>"
git tag v0.x.y
git push --follow-tags
```

The `--clean` flag wipes existing output before regenerating, so removed-upstream files don't linger. Only commit a new tag once `make verify` is green against the freshly-ported bundle.

---

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for the full failure-mode catalog.
