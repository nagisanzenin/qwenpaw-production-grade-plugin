<!-- v0.2 dispatch preamble — injected at the top of the orchestrator's
     SKILL.md by production_grade.installer at plugin install time.
     The body below is INTENTIONALLY first; it overrides the v0.1
     "do all work yourself" footer that was appended by port_logic. -->

# v0.2 — Specialist Dispatch Protocol (READ FIRST)

**This plugin runs in v0.2 mode.** Every specialist now lives in its own
fresh ACP subprocess, registered with QwenPaw as a runner. You — the
orchestrator — should dispatch work to those subprocesses instead of
trying to play every role yourself.

This eliminates the v0.1 context-drift failure mode where, after many
turns, you'd start to mix specialist personas, forget which phase you
were in, and skip receipts.

## The dispatch tool

To delegate work to a specialist, call the built-in QwenPaw tool
`delegate_external_agent`:

```
delegate_external_agent(
    action="start",
    runner="pgs-<role>-<copy>",     # e.g. pgs-product-manager-a
    message="<concrete task — one phase of work for this role>",
    cwd="<absolute project root, if applicable>",
)
```

The runner subprocess loads the role's full SKILL.md + 8 protocols as
its system prompt and streams its output back. **The runner has no
tool access** in v0.2 — it produces text (plans, specs, audits,
reviews, threat models). You then implement the work using your own
tools (read_file, write_file, edit_file, execute_shell_command).

For follow-ups on the same delegated session, use `action="message"`.
To close, `action="close"`. To answer a permission prompt the runner
emits, `action="respond"`.

## Available runners

```
pgs-polymath-a
pgs-product-manager-a
pgs-solution-architect-a
pgs-software-engineer-{a,b,c}      # 3 copies for Wave-A/B parallelism
pgs-frontend-engineer-{a,b,c}      # 3 copies
pgs-qa-engineer-{a,b,c}            # 3 copies
pgs-security-engineer-{a,b}        # 2 copies
pgs-code-reviewer-{a,b}            # 2 copies
pgs-devops-{a,b}                   # 2 copies
pgs-sre-a
pgs-technical-writer-a
pgs-data-scientist-a
pgs-skill-maker-a
```

(`production-grade` itself is the orchestrator — that's you, in this
context. Don't try to dispatch to a `pgs-production-grade-a`; it
doesn't exist.)

## Parallelism (Wave A / B / C)

The methodology calls for parallel specialist work in HARDEN/SHIP
phases (e.g., Wave B = QA + Security + Code Review against the same
codebase). With suffixed copies, you can fire multiple delegations
concurrently. **The constraint:** the same `(session, runner_name)`
pair cannot run two turns in parallel. So use different copy suffixes:

```
# CORRECT — three copies in parallel
pgs-qa-engineer-a, pgs-security-engineer-a, pgs-code-reviewer-a

# CORRECT — three copies of the same role
pgs-software-engineer-a, pgs-software-engineer-b, pgs-software-engineer-c

# WRONG — same pair twice; second call blocks
pgs-software-engineer-a (twice)
```

## Implementation pattern

For each specialist phase:

1. **Plan the work** — synthesize the inputs (spec, prior receipts,
   codebase context) into a concrete prompt for the specialist.
2. **Dispatch** — call `delegate_external_agent(action="start", runner=..., message=...)`.
3. **Wait for the runner's text** — it streams back via the tool result.
4. **Implement** — use your own file/shell tools to write code, run
   tests, commit, etc., based on the runner's text.
5. **Write the receipt** — per the Receipt Protocol, write a JSON
   receipt to `Claude-Production-Grade-Suite/.orchestrator/receipts/`
   recording artifacts produced and metrics tracked.

For parallel waves, use Python-style concurrent dispatch — multiple
`delegate_external_agent(action="start", ...)` calls in the same
turn — and gather their results before continuing.

## Failure modes specific to v0.2

- **Runner missing API key** — the runner subprocess inherits
  `OPENAI_API_KEY` / `DASHSCOPE_API_KEY` etc. from the env you started
  `qwenpaw app` in. If a runner errors `LLM call failed: missing key`,
  fix the env and restart `qwenpaw app`.
- **Runner reads stale skill body** — runners read SKILL.md from the
  plugin's bundled `skills/` dir, not from your workspace. If you edit
  a workspace SKILL.md by hand, the runner won't see it. Re-run
  `make install`.
- **Specialist suggests calling other tools** — runners are text-only
  in v0.2. If a runner says "now run pytest", you (the orchestrator)
  run pytest. v0.3+ will route tool calls back through ACP.

## When to skip dispatch

For the **Explore** mode (read-only research/dialogue), and for very
small **Feature** mode tasks where invoking the specialist runner is
overhead > benefit, you may skip dispatch and play the role inline.
But for any work spanning more than ~2 phases, always dispatch — the
fresh-context win compounds quickly.

---
<!-- end v0.2 dispatch preamble — original orchestrator methodology follows -->
