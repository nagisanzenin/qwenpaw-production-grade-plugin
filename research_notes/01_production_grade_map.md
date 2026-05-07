Now I'll compile the exhaustive architectural inventory:

---

# PRODUCTION-GRADE CLAUDE CODE PLUGIN: COMPLETE ARCHITECTURAL INVENTORY

**Version:** 5.4.0  
**Author:** nagisanzenin  
**License:** MIT  
**Repository:** `/Users/quanduong/Documents/Github/claude-code-production-grade-plugin`

---

## EXECUTIVE SUMMARY

This production-grade plugin transforms Claude Code from a code generator into a **complete autonomous pipeline** that produces enterprise-ready systems. It coordinates **14 specialized AI agents** through **5 pipeline phases** (DEFINE → BUILD → HARDEN → SHIP → SUSTAIN), enforces output via **8 shared protocols**, manages execution through **10+ modes**, and gates critical decisions at **3 approval checkpoints**.

All mechanisms are **Claude-Code-native**—they use skills, hooks, tasks, teams, and native features exclusively. No external dependencies or custom tooling.

---

## 1. PLUGIN MANIFEST & MARKETPLACE METADATA

### `.claude-plugin/plugin.json` (5.4.0)

**File:** `/Users/quanduong/Documents/Github/claude-code-production-grade-plugin/.claude-plugin/plugin.json:1-10`

```json
{
  "name": "production-grade",
  "description": "Enhances Claude Code from producing raw code into delivering production-ready systems. 14 specialized agents handle architecture, tested code, security audit, CI/CD, and documentation. Use for building apps/websites/services, adding features, hardening, deployment, testing, review, or architecture design.",
  "version": "5.4.0",
  "author": {
    "name": "nagisanzenin"
  },
  "license": "MIT",
  "keywords": ["production-grade", "saas", "orchestrator", "full-stack", "meta-skill", "pipeline", "devops", "architecture", "testing", "security", "sre", "ai", "ml", "llm"]
}
```

**Fields used:**
- `name`: Entry point for skill invocation
- `description`: User-facing explanation (activates SessionStart hook context)
- `version`: Manually maintained; bumped in 4 locations (see DEV_PROTOCOL section 4)
- `author.name`: Plugin marketplace identity
- `license`: MIT (permissive)
- `keywords`: Searchability in Claude Code marketplace; includes "orchestrator" (key differentiator)

**Version management locations (must all match):**
1. `.claude-plugin/plugin.json` → `version` field
2. `~/.claude/plugins/installed_plugins.json` → `production-grade@nagisanzenin` entry
3. `~/.claude/plugins/cache/nagisanzenin/production-grade/{version}/` → directory name
4. Marketplace metadata (if available)

---

## 2. SKILL MANIFEST & DEFINITION

### 14 SPECIALIZED AGENTS (Skills)

All implemented as markdown skill files with YAML frontmatter. Each loads **8 shared protocols** at startup via `!`cat`` inline bash.

| # | Skill | File | Purpose | Sole Authority |
|---|-------|------|---------|---|
| 1 | **production-grade** | `skills/production-grade/SKILL.md` | Orchestrator — routes, gates, re-anchoring | Pipeline control |
| 2 | **polymath** | `skills/polymath/SKILL.md` | Thinking partner — research, exploration, ideation | Dialogue & discovery |
| 3 | **product-manager** | `skills/product-manager/SKILL.md` | Requirements → BRD, user stories, acceptance criteria | Requirements |
| 4 | **solution-architect** | `skills/solution-architect/SKILL.md` | System design → ADRs, API contracts, data models | Architecture |
| 5 | **software-engineer** | `skills/software-engineer/SKILL.md` | Backend → handlers, services, repositories, business logic | Implementation (backend) |
| 6 | **frontend-engineer** | `skills/frontend-engineer/SKILL.md` | Web UI → components, pages, design system, accessibility | Implementation (frontend) |
| 7 | **qa-engineer** | `skills/qa-engineer/SKILL.md` | Tests → unit, integration, e2e, performance, contract testing | Quality assurance |
| 8 | **security-engineer** | `skills/security-engineer/SKILL.md` | Security → STRIDE, OWASP Top 10, PII, dependency scan | Security |
| 9 | **code-reviewer** | `skills/code-reviewer/SKILL.md` | Code quality → architecture conformance, anti-patterns, performance (adversarial) | Code quality |
| 10 | **devops** | `skills/devops/SKILL.md` | Infrastructure → Docker, CI/CD, Terraform, monitoring | Infrastructure |
| 11 | **sre** | `skills/sre/SKILL.md` | Reliability → SLOs, chaos engineering, runbooks, capacity | Reliability |
| 12 | **technical-writer** | `skills/technical-writer/SKILL.md` | Docs → API reference, dev guides, architecture overviews | Documentation |
| 13 | **data-scientist** | `skills/data-scientist/SKILL.md` | ML/LLM → optimization, prompt engineering, cost modeling | ML/LLM optimization |
| 14 | **skill-maker** | `skills/skill-maker/SKILL.md` | Creates reusable Claude Code skills from project patterns | Skill authoring |

### SKILL.md FRONTMATTER & STRUCTURE

Every skill follows this YAML + Markdown template:

**Frontmatter (YAML):**
```yaml
---
name: {skill-name}
description: >
  {user-facing description of what the skill does}
---
```

**Key sections in skill body:**

1. **Protocol Loading** (mandatory for all skills except polymath which is dialogue-only)
   ```
   !`cat Claude-Production-Grade-Suite/.protocols/ux-protocol.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/input-validation.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/tool-efficiency.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/visual-identity.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/freshness-protocol.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/receipt-protocol.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/boundary-safety.md 2>/dev/null || true`
   !`cat Claude-Production-Grade-Suite/.protocols/conflict-resolution.md 2>/dev/null || true`
   ```
   **Claude-Code mechanism:** Inline bash backticks load shared protocol markdown files into skill context before execution. Provides universal behavioral rules to all agents without code duplication.

2. **Engagement Mode** (controls decision-surfacing depth)
   ```
   !`cat Claude-Production-Grade-Suite/.orchestrator/settings.md 2>/dev/null || echo "No settings — using Standard"`
   
   | Mode | Behavior | Interaction Depth |
   |------|----------|------------------|
   | Express | Fully autonomous | Zero agent questions, auto-resolve all |
   | Standard | Balanced | 1-2 critical decisions only |
   | Thorough | Deep analysis | All major decisions surfaced |
   | Meticulous | Maximum control | Every decision point reviewed |
   ```
   **Claude-Code mechanism:** Skills read runtime settings via bash/Read and adapt their questioning behavior. Propagates user's single engagement choice to all 14 agents without re-asking.

3. **Progress Output** (visual identity protocol compliance)
   - Skill header: `━━━ {Skill Name} ━━━`
   - Phase progress: `[N/M] {phase} → ✓/⧖/○ status` with concrete counts
   - Completion summary: `✓ {Skill} {N} artifacts, {M} metrics ⏱ Xm Ys`

4. **Input Classification**
   ```
   | Category | Inputs | Behavior if Missing |
   |----------|--------|-------------------|
   | Critical | ... | STOP |
   | Degraded | ... | WARN, continue partial |
   | Optional | ... | Continue, skip silently |
   ```

5. **Phase Index & Dispatch** (for larger skills like Software Engineer with 5 phases)
   - Each phase in separate file: `phases/01-{name}.md`, `phases/02-{name}.md`, etc.
   - Loaded on-demand (never all at once) to minimize token usage
   - Enables phase-by-phase parallelism with independent agents per phase

6. **Common Mistakes** (real patterns from deployments)
   - QA Engineer: "Tests that depend on order", "No idempotency on writes", "Ignoring graceful shutdown"
   - Frontend Engineer: "No loading/error/empty states", "Dead Element Rule (buttons that do nothing)"
   - Security Engineer: "Running audit before code is stable", "Generic OWASP checklist without code analysis"

### SKILL DISCOVERY & ACTIVATION

**Orchestrator skill routing** (`.claude-plugin/plugin.json` implies launch via `Skill` tool):
- User requests flow through `production-grade` orchestrator skill
- Orchestrator classifies intent into one of 10 execution modes
- Calls `Skill(skill="production-grade:<sub-skill-name>", args="{phase/mode context}")` to dispatch sub-skills
- Each sub-skill is invoked via the Skill tool with its full methodology (SKILL.md) loaded

**Example dispatch chain:**
1. User: `"Build me a SaaS"`
2. Orchestrator: Classifies as `Full Build` mode
3. Orchestrator: Invokes `Skill(skill="production-grade:product-manager", args="DEFINE phase BRD")`
4. Product Manager: Loads its full SKILL.md (protocols + phases + context), executes
5. After PM completes: Orchestrator invokes `Skill(skill="production-grade:solution-architect", args="DEFINE phase architecture")`

---

## 3. HOOKS & CROSS-SESSION PERSISTENCE

### `hooks/hooks.json` (Event Binding)

**File:** `/Users/quanduong/Documents/Github/claude-code-production-grade-plugin/hooks/hooks.json:1-17`

```json
{
  "description": "Production-grade plugin hooks for cross-session project enforcement",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "_R=\"${CLAUDE_PLUGIN_ROOT}\"; [ -z \"$_R\" ] && _R=\"$HOME/.claude/plugins/cache/nagisanzenin/production-grade\"; bash \"$_R/hooks/session-guard.sh\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Claude-Code surface used:**
- **Event:** `SessionStart` hook fires when a new Claude Code session starts
- **Matcher:** Pattern `startup|clear|compact` — triggers on natural session reset moments
- **Type:** `command` — runs a bash script (other type: `system-message`, `deny-tools`, etc.)
- **Command:** Reads `CLAUDE_PLUGIN_ROOT` env var (Claude Code provides this) or falls back to cache directory
- **Timeout:** 10 seconds (non-blocking; hook fails gracefully)

**Purpose:** **Cross-session project detection and workflow enforcement.**

### `hooks/session-guard.sh` (Project Detection Logic)

**File:** `/Users/quanduong/Documents/Github/claude-code-production-grade-plugin/hooks/session-guard.sh:1-38`

```bash
#!/usr/bin/env bash
SUITE_DIR="Claude-Production-Grade-Suite"

if [ ! -d "$SUITE_DIR" ]; then
  exit 0
fi

ADR_COUNT=$(find "$SUITE_DIR" -name "ADR-*.md" 2>/dev/null | wc -l | tr -d ' ')
RECEIPT_COUNT=$(find "$SUITE_DIR/.orchestrator/receipts" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
PROTOCOL_COUNT=$(find "$SUITE_DIR/.protocols" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

cat <<GUARD
# Production-Grade Native Project Detected
...
GUARD
```

**Behavior:**
1. Checks if `Claude-Production-Grade-Suite/` directory exists in current project (indicator that project was built with production-grade)
2. If NOT present: exit silently (non-production-grade project)
3. If present: counts artifacts (ADRs, receipts, protocols) and prints a guarded prompt offering 3 choices:
   - "Use production-grade (Recommended)" → invokes `production-grade` skill for the user's next request
   - "Work directly without the plugin" → proceeds normally, no further reminders
   - "Chat about this" → free-form dialogue

**Claude-Code surface:** Hook output is printed to the terminal. The user sees `AskUserQuestion` style options and can respond. Next user message is then routed accordingly (to `/production-grade` or directly to the model).

---

## 4. ACTIVATION RULES & REQUEST CLASSIFICATION

### `skills/production-grade/hooks/activation-rules.json`

**File:** `/Users/quanduong/Documents/Github/claude-code-production-grade-plugin/skills/production-grade/hooks/activation-rules.json:1-112`

**Purpose:** Keyword and intent-pattern matching to auto-recommend skill invocation

```json
{
  "description": "Skill activation rules for UserPromptSubmit hook",
  "rules": [
    {
      "skill": "production-grade",
      "keywords": ["build a saas", "build me a", "build a platform", ...],
      "intent_patterns": [
        "build.*(?:saas|platform|service|app|system|product)",
        "(?:production|prod).*(?:grade|ready|quality)",
        ...
      ],
      "priority": "high",
      "recommendation": "This looks like a production-grade project..."
    }
  ],
  "hook_config": {
    "event": "UserPromptSubmit",
    "matching_strategy": "keyword_then_intent",
    "max_recommendations_per_prompt": 2,
    "session_tracking": true,
    "session_tracking_file": ".orchestrator/activation-log.json"
  }
}
```

**Claude-Code surface:**
- **Event:** `UserPromptSubmit` — fires when user submits a message
- **Matching strategy:** First tries keyword match, then regex intent patterns
- **Recommendation output:** Suggests `/production-grade` skill if patterns match with `high` priority

**Supported skills with activation patterns:**
- production-grade (Full Build, Feature, Harden, Ship, etc.)
- product-manager (BRD, requirements, feature requests)
- solution-architect (design, API design, tech stack)
- software-engineer (implement, build backend, write services)
- frontend-engineer (UI, dashboard, React, web app)
- qa-engineer (test, coverage, e2e)
- security-engineer (security audit, OWASP, threat model)
- devops (CI/CD, terraform, docker, kubernetes, deploy)
- sre (production readiness, SLO, runbook, incident)
- data-scientist (LLM optimization, ML, cost modeling)

---

## 5. EXECUTION PIPELINE: DEFINE → BUILD → HARDEN → SHIP → SUSTAIN

### Overview

The production-grade orchestrator (`skills/production-grade/SKILL.md`) is the single entry point for all requests. It:

1. **Classifies** user request into one of 10 execution modes
2. **Plans** which skills to run (adapts to request scope)
3. **Bootstraps** shared workspace: `Claude-Production-Grade-Suite/` directory structure
4. **Iterates** through pipeline phases
5. **Gates** at 3 approval checkpoints (BRD approval, Architecture approval, Production Readiness approval)
6. **Verifies** receipts at every phase transition
7. **Re-anchors** (re-reads specs from disk) at every phase transition
8. **Cleans up** agents via `TeamDelete` on completion or rejection

### 10 EXECUTION MODES

**Request → Mode routing:**

| Mode | Trigger Signals | Skills | Gates | Use Case |
|------|---|---|---|---|
| **Full Build** | "build a SaaS", "from scratch", "full stack" | All 14 agents, all 5 phases | 3 (BRD, Arch, Prod Ready) | Greenfield system build |
| **Feature** | "add [feature]", "implement [feature]" | PM + Architect + Backend/Frontend + QA | 1 (after PM scope) | Add feature to existing codebase |
| **Harden** | "review", "audit", "secure", "before launch" | Security + QA + Code Reviewer (parallel) + Remediation | 1 (after findings) | Security/quality audit of existing code |
| **Ship** | "deploy", "CI/CD", "containerize" | DevOps + SRE | 1 (infra plan approval) | Set up deployment infrastructure |
| **Test** | "write tests", "test coverage" | QA Engineer only | 0 | Write/run tests on existing code |
| **Review** | "review my code", "code quality" | Code Reviewer only | 0 (read-only) | Architecture conformance & quality review |
| **Architect** | "design", "API design", "tech stack" | Solution Architect only | 1 (architecture approval) | Design or redesign system |
| **Document** | "document", "write docs", "API docs" | Technical Writer only | 0 | Generate documentation |
| **Explore** | "explain", "help me think", "I'm not sure" | Polymath only | 0 (dialogue) | Research, exploration, ideation |
| **Optimize** | "performance", "slow", "scale", "reliability" | Code Reviewer + SRE | 1 (findings approval) | Performance/reliability optimization |

### FULL BUILD PHASE FLOW (All 14 agents)

```
┌─ DEFINE ────────────────────────────────────┐
│  1. Product Manager      → BRD              │
│  2. Solution Architect   → ADRs, contracts  │
│  └─ GATE 1: Requirements Approval ──┐      │
└────────────────────────────────────────┼────┘
                                        │
┌─ BUILD (Wave A: parallel) ──────────┤
│  3. Software Engineer    → services   │
│  4. Frontend Engineer    → components │
│  5. DevOps               → Dockerfiles│
│  6. QA Engineer          → test plan  │
│  7. Security Engineer    → threat model
│  8. Code Reviewer        → checklist  │
│  9. SRE                  → SLOs       │
└─────────────────────────────────────┬─
                                      │
┌─ HARDEN (Wave B: parallel) ────────┤
│  6. QA Engineer          → run tests  │
│  7. Security Engineer    → code audit │
│  8. Code Reviewer        → review     │
│  9. DevOps               → build push │
│  └─ GATE 2: Architecture Review ──┐  │
└────────────────────────────────────┼──┘
                                     │
┌─ SHIP (Wave C: parallel) ─────────┤
│  5. DevOps               → IaC, CICD│
│  10. SRE                 → chaos eng │
│  11. Data Scientist      → cost model
│  └─ GATE 3: Production Readiness ┐ │
└────────────────────────────────────┼┘
                                     │
┌─ SUSTAIN ────────────────────────┤
│  12. Technical Writer   → docs     │
│  13. Skill Maker        → reusable │
│  14. Compound Learning  → insights │
└──────────────────────────────────┘
DONE
```

### PIPELINE RECEIPT ENFORCEMENT

**Before every gate and phase transition, orchestrator:**

1. **Lists expected receipts** for completed tasks
2. **Reads** each receipt file from `.orchestrator/receipts/{task_id}-{agent_name}.json`
3. **Verifies artifacts exist** — for every path in `receipt.artifacts`, confirms file exists
4. **Extracts metrics** — uses verified counts (not agent claims) for gate display
5. **Rejects incomplete** — if receipt missing or artifacts absent, blocks gate and escalates

**Receipt schema:**
```json
{
  "task": "T6b",
  "agent": "code-reviewer",
  "phase": "HARDEN",
  "status": "complete",
  "artifacts": [ "paths/to/files" ],
  "metrics": { "findings_critical": 2, "findings_high": 5 },
  "effort": { "files_read": 47, "files_written": 6, "tool_calls": 83 },
  "verification": "all 4 review phases executed, report written"
}
```

---

## 6. SHARED PROTOCOL STACK (8 Universal Protocols)

All 14 agents load these 8 markdown files at startup via `!`cat`` inline bash. Together they define the system's behavioral foundation.

### Protocol 1: UX Protocol (`skills/_shared/protocols/ux-protocol.md`)

**Core rule:** Zero open-ended questions. All user interactions use `AskUserQuestion` with predefined options.

**6 UX rules:**
1. Never ask "What do you want to do?" — present specific options
2. Recommended option always first
3. "Chat about this" always last (escape hatch for free-form input)
4. Continuous execution (don't wait; do work while asking)
5. Real-time progress (print metrics constantly)
6. Autonomy scales with engagement mode (Express = autonomous, Meticulous = every decision surfaced)

**Claude-Code surface:** `AskUserQuestion` tool with `multiSelect: false`, options array, "Chat about this" option

### Protocol 2: Input Validation (`skills/_shared/protocols/input-validation.md`)

**5-step validation pipeline:**
1. Read config (`.production-grade.yaml`)
2. Probe inputs in parallel (Glob, Read, smart_outline)
3. Classify as Critical (stop if missing), Degraded (warn but continue), Optional (continue silently)
4. Print gap summary
5. Adapt scope based on what's available

**Example:**
- Critical for Software Engineer: `api/openapi/*.yaml`, `schemas/erd.md`, `docs/architecture/tech-stack.md` → STOP if missing
- Degraded: `docs/architecture/ADRs`, migrations → WARN but proceed with defaults
- Optional: branding guidelines → skip silently

### Protocol 3: Tool Efficiency (`skills/_shared/protocols/tool-efficiency.md`)

**Rules for optimal Claude-Code tool use:**
- Use dedicated tools over shell commands (Read over `cat`, Glob over `find`, Grep over `grep`)
- Parallel tool calls for independent operations
- `smart_outline` before full Read on large files
- Config-aware paths (respect `.production-grade.yaml` overrides)

### Protocol 4: Visual Identity (`skills/_shared/protocols/visual-identity.md`)

**Terminal-native design language (no emoji, monospace Unicode):**

- **Container tiers:**
  - Tier 1: Double-line `╔═══╗` for critical moments (gates, final summary)
  - Tier 2: Single-line `┌───┐` for progress updates, data grids
  - Tier 3: Heavy rules `━━━` for section dividers

- **Icon vocabulary:** `◆ ⬥ ● ○ ✓ ✗ ⧖ ⚠ →`
  - `◆` = highlight/attention
  - `●` = active/in progress
  - `○` = pending
  - `✓` = complete
  - `⧖` = working (hourglass)
  - `→` = transition/next

- **Phase progress template:**
  ```
  [1/N] Phase Name
    ✓ metric 1, metric 2
    ⧖ action in progress...
    ○ next action pending
  ```

- **Completion summary format:**
  ```
  ✓ Skill Name    {N} artifacts, {M} issues, {K} lines    ⏱ Xm Ys
  ```

- **Gate ceremony format:**
  ```
  ⬥ GATE N: {Decision Type}
  
  Metrics:
    Key 1: value
    Key 2: value
  
  [Option] [Option] [Option]
  ```

### Protocol 5: Conflict Resolution (`skills/_shared/protocols/conflict-resolution.md`)

**Authority hierarchy (when two skills claim overlapping domains):**

| Level | Authority | Rule |
|-------|-----------|------|
| 1 | Requirements | PM-owned (product-manager has sole authority) |
| 2 | Architecture | Architect-owned (solution-architect has sole authority) |
| 3 | Security | Security Engineer-owned (OWASP, STRIDE, PII) |
| 4 | Code Quality | Code Reviewer-owned (SOLID, DRY, maintainability) |
| Other | Shared | Dedup by file:line, keep highest severity |

**No skill contradicts another's sole-authority domain.**

### Protocol 6: Freshness Protocol (`skills/_shared/protocols/freshness-protocol.md`)

**Temporal awareness for volatile data:**

**Tier 1 — MUST WebSearch (days-weeks decay):**
- LLM model IDs, context windows, pricing (e.g., `claude-sonnet-4-20250514`)
- API pricing and rate limits
- Active CVEs and security advisories
- SDK breaking changes (OpenAI v4→v5, LangChain releases)
- Deprecated features

**Tier 2 — WebSearch when writing config (weeks-months decay):**
- Package versions (npm, pip, cargo)
- Framework APIs (Next.js, React, NestJS major versions)
- Docker base image LTS tags
- Cloud service features, regions, pricing
- Terraform provider schemas
- CLI tool flags and subcommands

**Tier 3 — WebSearch if uncertain (months-quarters):**
- Browser APIs and compatibility
- Crypto algorithms and best practices
- Compliance framework requirements

**Tier 4 — Trust training data (years):**
- Language fundamentals, standard libraries
- Protocols (HTTP, TCP/IP, WebSocket)
- Algorithms and design patterns

**Pattern:** When volatile data detected → `WebSearch` → cite findings with `✓ Verified:` → implement with verified data

### Protocol 7: Receipt Protocol (`skills/_shared/protocols/receipt-protocol.md`)

**Every task must have verifiable proof it ran.**

**Receipt schema:**
```json
{
  "task": "T6b",
  "agent": "security-engineer",
  "phase": "HARDEN",
  "status": "complete",
  "artifacts": ["paths/to/all/created/files"],
  "metrics": { "findings_critical": 2, "findings_high": 5 },
  "effort": { "files_read": 47, "files_written": 6, "tool_calls": 83 },
  "verification": "all 6 phases executed, report written with CriticalHigh findings documented"
}
```

**Remediation chain (for Critical/High findings):**
1. Finding receipt (agent that found issue)
2. Remediation receipt (agent that fixed it)
3. Verification receipt (original finder re-scans, confirms fixed)

All 3 must exist before Gate 3 opens.

### Protocol 8: Boundary Safety (`skills/_shared/protocols/boundary-safety.md`)

**6 structural patterns that cause silent failures at system boundaries. Derived from real PingBase deployment bugs.**

1. **Framework abstractions break at boundaries** — Use platform primitives (raw `<a>`, raw `fetch`, raw redirect) when crossing domains. Next.js `<Link>` silently does client-side navigation for `/api/auth/login` instead of full request.

2. **Delegate to framework control flow** — Don't duplicate middleware logic in UI. Wire to the destination; let middleware redirect.

3. **Self-referencing config = infinite loop** — Config override must point to different implementation than default. `signIn: "/api/auth/signin"` IS the default → infinite redirect.

4. **Global interceptors must be conditional** — Never return hardcoded value. Branch on input; pass through unmatched cases.

5. **Test full user journeys across boundaries** — Unit tests verify hops; integration tests verify endpoints. E2E tests verify the complete journey (user → OAuth → callback → redirect → authenticated page).

6. **Identity must match across systems** — Git email vs GitHub email vs CI/CD email. Test token format consistency at every integration point.

---

## 7. WORKSPACE STRUCTURE & STATE MANAGEMENT

### Bootstrap Directory Structure

Every pipeline run creates this structure at project root:

```
Claude-Production-Grade-Suite/          [Root orchestration directory]
├── .protocols/                          [Shared protocols loaded at startup]
│   ├── ux-protocol.md
│   ├── input-validation.md
│   ├── tool-efficiency.md
│   ├── visual-identity.md
│   ├── freshness-protocol.md
│   ├── receipt-protocol.md
│   ├── boundary-safety.md
│   └── conflict-resolution.md
│
├── .orchestrator/                       [Orchestrator control & receipts]
│   ├── settings.md                      [Engagement mode, parallelism, worktree]
│   ├── receipts/                        [Receipt JSON files per task]
│   │   ├── T1-product-manager.json
│   │   ├── T2-solution-architect.json
│   │   ├── T3a-software-engineer.json
│   │   ├── T3b-frontend-engineer.json
│   │   ├── T6a-security-engineer-verify.json
│   │   └── ...
│   ├── codebase-context.md              [Brownfield context (if existing code)]
│   ├── rework-log.md                    [Self-healing gate rework cycles]
│   ├── activation-log.json              [UserPromptSubmit activation history]
│   └── compound-learnings.md            [Cross-run intelligence]
│
├── product-manager/
│   └── BRD/
│       ├── INDEX.md                     [Table of contents]
│       └── brd.md                       [Feature specifications]
│
├── solution-architect/
│   └── (workspace artifacts)
│       ├── discovery-notes.md           [Interview findings]
│       ├── fitness-analysis.md          [Scale & constraint analysis]
│       ├── tech-stack-evaluation.md
│       └── cost-model.md
│
├── software-engineer/
│   ├── implementation-plan.md
│   └── progress.md
│
├── frontend-engineer/
│   ├── analysis.md
│   ├── design-research.md
│   └── component-plan.md
│
├── qa-engineer/
│   ├── test-plan.md
│   ├── coverage-report.md
│   └── findings.md
│
├── security-engineer/
│   ├── threat-model/
│   ├── code-audit/
│   ├── auth-review/
│   ├── data-security/
│   ├── supply-chain/
│   └── remediation/
│
├── code-reviewer/
│   ├── review-report.md
│   ├── architecture-conformance.md
│   └── findings/
│
├── devops/
│   ├── assessment.md
│   └── deployment-plan.md
│
├── sre/
│   ├── readiness-review.md
│   └── slo-definitions.md
│
├── technical-writer/
│   └── doc-plan.md
│
└── polymath/
    └── handoff/
        └── context-package.md           [Pre-flight findings passed to PM]
```

### Configuration Files

**`.production-grade.yaml`** (optional; user can override default paths):
```yaml
paths:
  brd: Claude-Production-Grade-Suite/product-manager/BRD/
  adrs: docs/architecture/architecture-decision-records/
  api_contracts: api/
  erd: schemas/erd.md
  services: services/
  frontend: frontend/
  tests: tests/
  terraform: infrastructure/terraform/
  ci_cd: .github/workflows/
```

**`Claude-Production-Grade-Suite/.orchestrator/settings.md`** (written at pipeline start, read by all agents):
```markdown
# Pipeline Settings
Engagement: [express|standard|thorough|meticulous]
Parallelism: [maximum|standard|sequential]
Worktrees: [enabled|disabled]
Cloud Provider: [aws|gcp|azure]
```

**`Claude-Production-Grade-Suite/.orchestrator/codebase-context.md`** (brownfield projects only):
```markdown
# Codebase Context
Mode: brownfield
Language: [typescript|python|go|rust|java]
Framework: [next.js|fastapi|gin|actix|spring]
Existing paths: [mapping]

## Rules for all agents
- NEVER overwrite existing files without explicit user approval
- READ existing code patterns before writing anything
- MATCH existing code style and structure
- ADD to existing directories, don't replace them
```

---

## 8. TEAM & TASK COORDINATION

### Teams (`TeamCreate` / `TeamDelete`)

**The orchestrator creates a team for multi-skill modes:**

```python
TeamCreate(
  team_name="production-grade",
  description="Production-grade pipeline execution — 14 agents coordinating through 5 phases"
)
```

**Purpose:** Enables 14 agents to work in parallel without stepping on each other. Each agent gets:
- Task list (via TaskCreate/TaskUpdate)
- Idle notification (when waiting for other agents)
- Message delivery (SendMessage for coordination)

### Tasks (`TaskCreate` / `TaskUpdate`)

**Each agent maps to 1+ tasks:**

```python
TaskCreate(
  subject="Product Manager: Write BRD from user requirements",
  description="Interview user, research domain, write business requirements doc with user stories and acceptance criteria",
  activeForm="Interviewing user and writing BRD"
)
# Returns task_id (e.g., "T1")

TaskUpdate(taskId="T1", status="in_progress")
# ... work ...
TaskUpdate(taskId="T1", status="completed")
```

**Task dependencies (blocks/blockedBy):**
- T2 (Solution Architect) blocked by T1 (Product Manager) — needs BRD first
- T3a (Software Engineer), T3b (Frontend Engineer) blocked by T2 — both need architecture
- T6 (Security Engineer) blocked by T3a, T3b — both need code to audit
- T8 (DevOps) blocked by T6 — needs security findings before deploying

---

## 9. AGENT PARALLELISM & WORKTREES

### Parallel Execution Architecture (2 waves)

**Wave A (BUILD) — Parallel after DEFINE:**
```
Software Engineer ──┐
Frontend Engineer   ├─ parallel (shared arch + API contracts)
DevOps              │
QA Engineer ────────┤
Security Engineer   │
Code Reviewer       │
SRE ────────────────┘
```

All 7 agents read from the same `docs/architecture/` ADRs and API specs. Independent work streams; no file conflicts because they write to separate directories (`services/`, `frontend/`, `infrastructure/`, etc.).

**Wave B (HARDEN) — Parallel after BUILD:**
```
QA Engineer ──────┐
Security Engineer ├─ parallel (all read completed code)
Code Reviewer     │
DevOps ────────────┘
```

### Worktree Isolation (v5.3 feature)

**Problem:** When N agents write to the same git repo simultaneously, file conflicts and race conditions occur.

**Solution:** Each parallel agent gets its own git worktree via `isolation="worktree"`.

```python
Agent(
  prompt="...",
  subagent_type="general-purpose",
  isolation="worktree",  # Creates .claude/worktrees/{random-name}/
  run_in_background=True
)
```

**Flow:**
1. Before parallel wave: Check git state (dirty? commit pending?)
2. For each agent: Create git worktree from current HEAD
3. Run agent in its worktree (zero file conflicts)
4. After all agents complete: Merge worktrees back to main branch
5. If merge conflicts: Escalate to orchestrator (max 1 auto-resolve attempt)

---

## 10. PHASES & DISPATCH PROTOCOLS

### The 5 Pipeline Phases

Each phase has a dispatcher file in `skills/production-grade/phases/`:

| Phase | File | Teams Created | Parallel Waves | Gates |
|-------|------|---|---|---|
| **DEFINE** | `phases/define.md` | PM + Architect | Sequential | Gate 1: Requirements |
| **BUILD** | `phases/build.md` | SWE + FE + DevOps + QA + Sec + Review + SRE | Wave A (7 agents) | None (internal to BUILD) |
| **HARDEN** | `phases/harden.md` | QA + Sec + Review + DevOps | Wave B (4 agents) | Gate 2: Architecture Review |
| **SHIP** | `phases/ship.md` | DevOps + SRE + DataSci | Sequential (after remediation) | Gate 3: Production Readiness |
| **SUSTAIN** | `phases/sustain.md` | TW + SkillMaker | Sequential | None (final) |

### DEFINE Phase (`phases/define.md`)

**Step-by-step:**

1. **Polymath pre-flight check** (if request is vague)
   - Invoke `Skill(skill="production-grade:polymath", args="pre-flight consultation")`
   - Polymath researches domain, surfaces gaps, returns context package to `.orchestrator/polymath/handoff/context-package.md`
   - Only if user needs help clarifying; skipped if request is detailed

2. **Product Manager** (Create T1)
   ```python
   TaskCreate(subject="Product Manager: Write BRD")
   Agent(
     prompt="Use Skill tool: 'production-grade:product-manager'. Read engagement mode from settings.md. Interview user to required depth (Express=2-3 questions, Standard=3-5, Thorough=5-8, Meticulous=8-12). Write BRD to Claude-Production-Grade-Suite/product-manager/BRD/brd.md.",
     subagent_type="general-purpose"
   )
   ```
   - Reads polymath context if available
   - Adapts interview depth to engagement mode
   - Outputs: BRD with user stories, acceptance criteria, business rules
   - Writes receipt to `.orchestrator/receipts/T1-product-manager.json`

3. **Solution Architect** (Create T2, blocked by T1)
   ```python
   TaskCreate(subject="Solution Architect: Design System", addBlockedBy=["T1"])
   Agent(
     prompt="Use Skill tool: 'production-grade:solution-architect'. Read BRD from T1 receipt. Run constraint discovery interview (engagement mode). Generate: ADRs, API contracts (OpenAPI specs), data models (ERD), scaffold.",
     subagent_type="general-purpose"
   )
   ```
   - Reads BRD written by PM
   - Interviews user on scale, constraints, tech preferences (mode-aware depth)
   - Outputs: 5-8 ADRs, OpenAPI specs in `api/`, ERD in `schemas/erd.md`, project scaffold
   - Writes receipt listing all deliverables

4. **Gate 1: Requirements & Architecture Approval**
   ```
   ⬥ GATE 1: Requirements & Architecture Approval
   
   Metrics:
     User Stories: N
     Acceptance Criteria: M
     ADRs: K
     API Endpoints: J
   
   Do you approve? [Yes, proceed to BUILD] [No, rework] [Chat about this]
   ```
   - If rejected: Feed concerns back to relevant agent (PM or Architect), max 2 rework cycles
   - If approved: Proceed to BUILD phase

### BUILD Phase (`phases/build.md`)

**Wave A — 7 agents in parallel after DEFINE:**

**Step 1: Create shared foundations (Software Engineer Phase 1)**
```python
TaskCreate(subject="Software Engineer: Shared Foundations")
Agent(
  prompt="Use Skill tool: 'production-grade:software-engineer'. Read API contracts and ADRs. Run Phase 1 only: establish libs/shared/ with common types, error handlers, middleware, auth patterns, test fixtures.",
  isolation="worktree"
)
```

**Step 2: Parallel agents (after shared foundations)**
```python
# Backend services (phase 2)
Agent(
  prompt="Use Skill tool: 'production-grade:software-engineer'. Implement services using libs/shared/.",
  isolation="worktree",
  run_in_background=True  # Parallel
)

# Frontend (phase 1-4: analysis, design system, components, pages)
Agent(
  prompt="Use Skill tool: 'production-grade:frontend-engineer'. Build frontend using design system primitives first.",
  isolation="worktree",
  run_in_background=True  # Parallel
)

# DevOps (phase 1: assess, then Dockerfiles)
Agent(
  prompt="Use Skill tool: 'production-grade:devops'. Assess infrastructure, generate Dockerfiles.",
  isolation="worktree",
  run_in_background=True  # Parallel
)

# QA (phase 1: test plan)
Agent(
  prompt="Use Skill tool: 'production-grade:qa-engineer'. Read BRD and architecture. Write test plan (test planning phase only).",
  isolation="worktree",
  run_in_background=True  # Parallel
)

# Security (phase 0-1: recon + threat modeling)
Agent(
  prompt="Use Skill tool: 'production-grade:security-engineer'. Reconnaissance and threat modeling (not code audit yet).",
  isolation="worktree",
  run_in_background=True  # Parallel
)

# Code Reviewer (phase 1: prep checklist)
Agent(
  prompt="Use Skill tool: 'production-grade:code-reviewer'. Prepare review checklist from architecture (code not yet written).",
  isolation="worktree",
  run_in_background=True  # Parallel
)

# SRE (phase 1: readiness review)
Agent(
  prompt="Use Skill tool: 'production-grade:sre'. Readiness review — identify reliability concerns from architecture.",
  isolation="worktree",
  run_in_background=True  # Parallel
)
```

Wait for all agents to complete.

**Step 3: Merge worktrees back to main**
```python
# Orchestrator merges all worktree branches back to main
for worktree in all_worktrees:
  git -C {worktree} branch -M feature-{worktree-name}
  git checkout main
  git merge feature-{worktree-name}
  git worktree remove {worktree}
```

### HARDEN Phase (`phases/harden.md`)

**Wave B — 4 agents in parallel:**

After all code is committed to main, parallel agents audit existing code:

```python
Agent(prompt="QA Engineer: run Unit/Integration/E2E/Performance tests", isolation="worktree", run_in_background=True)
Agent(prompt="Security Engineer: Phases 2-5 code audit, auth review, data security, supply chain", isolation="worktree", run_in_background=True)
Agent(prompt="Code Reviewer: Phases 1-4 architecture conformance, code quality, performance, test quality", isolation="worktree", run_in_background=True)
Agent(prompt="DevOps: Build and push Docker containers", isolation="worktree", run_in_background=True)
```

**Findings consolidation:**
1. Collect all findings from QA, Security, Code Reviewer
2. Deduplicate by file:line
3. Sort by severity (Critical → High → Medium → Low)
4. Merge worktrees

**Gate 2: Production Readiness for Architecture**
```
⬥ GATE 2: Code Audit & Test Results

Metrics:
  Tests Passing: N
  Test Coverage: M%
  Security Findings: Critical=K, High=J
  Code Review Findings: Critical=L

[Fix Critical issues → rework] [Accept + proceed to SHIP] [Chat about this]
```

If rejected: Remediaation agent fixes issues, re-scans, re-presents.

### SHIP Phase (`phases/ship.md`)

**Sequential after HARDEN (after remediation):**

```python
# DevOps: IaC, CI/CD pipelines
Agent(prompt="DevOps Phase 2-3: Terraform, CI/CD workflows")

# SRE: Chaos engineering, capacity planning
Agent(prompt="SRE Phase 2-5: SLOs, chaos, incidents, capacity")

# Data Scientist: Cost modeling
Agent(prompt="Data Scientist Phase 6: Cost modeling and optimization")
```

**Gate 3: Production Readiness**
```
⬥ GATE 3: Production Readiness

Metrics:
  Infrastructure validated: yes
  SLOs defined: yes
  Cost estimate: $X/month
  Security findings remaining: 0 Critical

[All good, ship] [Need rework] [Chat about this]
```

### SUSTAIN Phase (`phases/sustain.md`)

**Sequential after SHIP:**

```python
Agent(prompt="Technical Writer: API docs, developer guides")
Agent(prompt="Skill Maker: Create 3-5 reusable project-specific skills")
Agent(prompt="Orchestrator: Write compound learnings from this pipeline run")
```

**Final summary:**
```
╔════════════════════════════════════════╗
║      Production-Grade Pipeline Complete║
╠════════════════════════════════════════╣
║                                        │
│  ✓ DEFINE       Requirements + Arch   │
│  ✓ BUILD        Services + Frontend   │
│  ✓ HARDEN       Tests + Security      │
│  ✓ SHIP         CI/CD + Monitoring    │
│  ✓ SUSTAIN      Docs + Skills         │
│                                        │
│  Files created: N
│  Tests passing: M
│  Security findings: 0 Critical
│  Pipeline time: Xh Ym
│                                        │
└────────────────────────────────────────┘
```

---

## 11. CLAUDE-CODE SURFACE DEPENDENCIES

### Tools Used by Production-Grade Plugin

| Claude-Code Feature | Used By | Purpose |
|---|---|---|
| **Skill tool** | Orchestrator + all phase dispatchers | Dispatch to 14 sub-skills (`production-grade:skill-name`) |
| **Team/TaskCreate** | Orchestrator at phase start | Create team + task list for coordination |
| **TaskUpdate** | All agents on completion | Mark task complete, write receipt |
| **TeamDelete** | Orchestrator at end | Clean up agents after pipeline |
| **AskUserQuestion** | All 14 agents | Engagement-mode-aware decision surfacing |
| **Agent tool** | Phase dispatchers | Spawn parallel agents with `isolation="worktree"` |
| **SessionStart hook** | Plugin system | Detect production-grade projects, offer 3-choice menu |
| **Bash backticks (`!``)** | All 14 skills in SKILL.md | Load 8 protocols + config files at startup |
| **Read tool** | Security, QA, Reviewer, DevOps | Read source code, test files, configs |
| **WebSearch** | Polymath, Freshness protocol | Verify volatile data before implementation |
| **WebFetch** | Polymath, integration checks | Extract details from URLs |
| **Bash (git, find, grep)** | QA for test discovery, DevOps for validation | Read-only filesystem operations |

### Config/Settings Files Read by Agents

| File | Loaded By | Purpose |
|---|---|---|
| `.production-grade.yaml` | All 14 skills at startup | Override default paths for BRD, architecture, services, etc. |
| `Claude-Production-Grade-Suite/.orchestrator/settings.md` | All 14 skills + orchestrator | Engagement mode (Express/Standard/Thorough/Meticulous), parallelism, worktrees |
| `Claude-Production-Grade-Suite/.orchestrator/codebase-context.md` | All skills (brownfield projects) | Existing codebase patterns — don't overwrite, extend instead |
| `Claude-Production-Grade-Suite/polymath/handoff/context-package.md` | PM, Architect (if polymath pre-flight ran) | Domain research, constraints, decisions already made |
| `Claude-Production-Grade-Suite/product-manager/BRD/brd.md` | Architect, SWE, FE, QA, Sec | User stories, acceptance criteria, business rules |
| `docs/architecture/architecture-decision-records/ADR-*.md` | All agents | Architectural decisions, tech stack, API patterns |
| `api/openapi/*.yaml` | SWE, FE, QA, Sec, Review | API contracts (endpoints, request/response schemas) |
| `schemas/erd.md` | SWE, DevOps | Data model, relationships, normalization |
| `docs/architecture/tech-stack.md` | SWE, FE, DevOps, SRE | Technology choices (languages, frameworks, databases) |

---

## 12. VERSION MANAGEMENT & UPDATES

### Version Locations (All 4 must match)

When bumping version (e.g., 5.3.0 → 5.4.0):

1. **`.claude-plugin/plugin.json:4`**
   ```json
   "version": "5.4.0"
   ```

2. **`~/.claude/plugins/installed_plugins.json`**
   ```json
   "production-grade@nagisanzenin": {
     "version": "5.4.0",
     "installPath": "~/.claude/plugins/cache/nagisanzenin/production-grade/5.4.0"
   }
   ```

3. **`~/.claude/plugins/cache/nagisanzenin/production-grade/5.4.0/`** (directory name)

4. **Marketplace metadata** (if available)

### Auto-Update Check (v5.4 feature)

**Orchestrator runs before any execution (all modes):**

1. Read local version from `installed_plugins.json`
2. WebFetch remote `.claude-plugin/plugin.json` from GitHub main
3. Compare versions
4. If remote > local: prompt user with "Update now (Recommended)" / "Skip"
5. If update selected: Clone repo, copy files to cache dir, update installed_plugins.json, restart pipeline
6. If skip or WebFetch fails: continue with current version

---

## 13. KEY ARCHITECTURAL INVARIANTS & CONSTRAINTS

### Non-Negotiable Rules (From VISION.md & DEV_PROTOCOL.md)

| Principle | Enforcement | Violation Behavior |
|-----------|---|---|
| **Superalignment** (Principle I) | All agents read shared artifacts (BRD, ADRs, API specs) before producing output | If agent deviates from artifact, it flags contradiction to user (not silent deviation) |
| **Production Grade** (Principle II) | No TODOs, stubs, or placeholders. All tests pass, all code compiles. | Receipt verification catches incomplete work at phase transition |
| **On Behalf of User** (Principle III) | Do work, don't describe options. Report results, not plans. | Every Agent() prompt includes decision defaults; Express mode auto-resolves |
| **Minimal Interaction** (Principle IV) | 3 pipeline gates max. Agent questions scale with engagement mode (0 in Express → many in Meticulous). | If agent asks a question in Express mode, it's a design bug |
| **Parallelism** (Principle V) | Independent work runs concurrently. Dependent work runs sequentially. | Worktree isolation prevents file conflicts. Task blockedBy enforces ordering. |
| **Dynamic/Adaptive** (Principle VI) | Pipeline skips irrelevant phases. Brownfield mode extends existing code instead of rebuild. | Orchestrator reads codebase, adapts scope; not all requests run all 14 agents |
| **Self-Extension** (Principle VII) | Agents can create new skills/artifacts when domain-specific patterns emerge | Skill Maker runs in SUSTAIN phase; creates project-specific reusable skills |
| **Extreme Ownership** (Principle VIII) | Agent that fails at its task debugs and fixes it (max 3 self-repair attempts before escalation) | Receipt verification blocks gate if task incomplete. Agent must fix own work. |
| **First-Principles Thinking** (Principle IX) | Architecture derives from constraints, not templates. | Architecture selection uses fitness function (scale, team, budget) as input |
| **Mathematical Rigor** (Principle X) | Capacity planning uses queuing theory. Cost modeling uses explicit formulas. | SRE outputs capacity numbers, not "probably enough". DevOps cost estimates have variable breakdown. |
| **Autonomous Resilience** (Principle XI) | Max 2 gate rework cycles per gate. Max 3 agent self-debug attempts. | Beyond limits: escalate to user. Rework logging prevents runaway cost. |

### Constraints (Cannot be relaxed)

**From DEV_PROTOCOL section 9:**

- **No emoji** — Unicode symbols only for monospace terminal alignment
- **No open-ended questions** — Every `AskUserQuestion` has predefined options
- **No config files touched by users** — Settings asked at runtime, not edited in files
- **No templates** — Architecture is derived, not selected
- **Protocols over guidelines** — If it matters, enforce it in a protocol
- **Real over claimed** — Use verified receipts, not agent assertions

---

## 14. DEVELOPMENT WORKFLOW & CHANGE PROTOCOL

### Making Changes to the Plugin

**From DEV_PROTOCOL section 4:**

1. **Understand** — Read existing code before modifying
2. **Check differentiators** — Does change strengthen an existing differentiator or introduce a new one?
3. **Check architecture rules** — Protocols, phase structure, parallelism patterns
4. **Implement** — Modify existing files, don't create unnecessary new ones
5. **Update version** — Bump in all 4 locations
6. **Update CHANGELOG.md** — Document what changed (Added, Changed, Fixed sections)
7. **Update README.md** — If user-visible behavior changed
8. **Test locally** — Install and verify the plugin works
9. **Commit and push** — Git commit with co-authored-by

### When Adding a New Skill

1. Create `skills/{skill-name}/SKILL.md` with YAML frontmatter
2. Add all 8 protocol `!`cat`` loading lines in header
3. Add Engagement Mode section reading from `settings.md`
4. Add Progress Output section following visual identity
5. Add Input Classification table
6. Split into phases if 4+ logical steps
7. Add skill to orchestrator's routing table in `skills/production-grade/SKILL.md`
8. Update README.md crew section and agent count
9. Update plugin.json description if scope changes

### When Adding a New Protocol

**Gate carefully — protocols add to every agent's context.**

Requirement: Must be derived from real failure, not theory. Show the bug, root cause, why it's universal.

1. Create `skills/_shared/protocols/{name}.md`
2. Add `!`cat`` loading line to ALL 14 skill SKILL.md files
3. Add to orchestrator's protocol table
4. Document in CHANGELOG
5. Check against all 11 VISION principles — protocol must not violate any

---

## 15. REAL-WORLD USAGE PATTERNS & EXAMPLES

### Example 1: User says "Build me a SaaS for e-commerce"

```
[User message]
"Build me a SaaS for e-commerce"

[SessionStart hook fires]
→ session-guard.sh runs
→ No production-grade project found → exit silently

[UserPromptSubmit hook fires]
→ activation-rules.json matches "build.*saas"
→ Recommends "Use /production-grade skill for full autonomous pipeline"

[User invokes]
/production-grade

[Orchestrator]
1. Classifies: "Full Build" mode
2. Bootstraps: Creates Claude-Production-Grade-Suite/ directory
3. Writes shared protocols to .protocols/
4. Asks engagement mode (Express/Standard/Thorough/Meticulous)
5. Checks for brownfield (finds nothing)
6. Dashboard: DEFINE pending...

[DEFINE phase]
→ T1 Product Manager: Interviews user (depth based on engagement mode)
  Writes BRD with user stories and acceptance criteria
  Receipt: .orchestrator/receipts/T1-product-manager.json
→ T2 Solution Architect: Reads BRD, interviews user on scale
  Generates 5 ADRs, OpenAPI specs, data model, scaffold
  Receipt: .orchestrator/receipts/T2-solution-architect.json
→ GATE 1: Shows BRD + Architecture, asks for approval

[User approves]

[BUILD phase]
→ Creates 7 parallel agents with worktrees:
  - Software Engineer (services)
  - Frontend Engineer (components, pages)
  - DevOps (Dockerfiles)
  - QA Engineer (test plan)
  - Security Engineer (threat model)
  - Code Reviewer (review checklist)
  - SRE (SLO draft)
→ All agents read shared api/, schemas/, docs/architecture/
→ Wave A completes, worktrees merged back
→ Dashboard: BUILD complete, HARDEN pending...

[HARDEN phase]
→ Creates 4 parallel agents:
  - QA Engineer: Runs tests (unit, integration, e2e, performance)
  - Security Engineer: Code audit, auth review, data security, supply chain
  - Code Reviewer: Architecture conformance, code quality, performance review
  - DevOps: Builds and pushes Docker images
→ Wave B completes, findings consolidated
→ GATE 2: Shows findings severity grid, asks approval to proceed

[User approves]

[SHIP phase]
→ DevOps: Terraform IaC, CI/CD pipelines
→ SRE: Chaos engineering, capacity planning
→ Data Scientist: Cost modeling
→ GATE 3: Production Readiness

[SUSTAIN phase]
→ Technical Writer: API docs, dev guides
→ Skill Maker: 3-5 project-specific reusable skills
→ Compound learnings written to rework-log.md

[Final Summary]
╔════════════════════════════════════════╗
║      Production-Grade Pipeline Complete║
...
```

### Example 2: User returns next session, says "Add Stripe billing"

```
[SessionStart hook fires]
→ session-guard.sh detects Claude-Production-Grade-Suite/ directory
→ Prints: "Production-Grade Native Project Detected. How would you like to work today?"
→ Options: [Use production-grade] [Work directly] [Chat about this]

[User selects "Use production-grade"]

[User message]
"Add Stripe billing to my API"

[Orchestrator]
1. Classifies: "Feature" mode (not Full Build)
2. Presents plan: "PM (scope feature) → Architect (design payment flow) → Software Engineer (implement endpoints) → QA (write tests)"
3. Asks engagement mode (Standard default for Feature mode)

[Mode: Standard]
→ T1 Product Manager: Scopes billing feature (2-3 questions)
  Writes mini-BRD (user stories specific to billing, acceptance criteria)
  GATE 1: Feature scope approval
→ T2 Solution Architect: Designs payment integration (scoped)
  New ADRs only for billing, updates API spec with new endpoints
→ T3 Software Engineer: Implements Stripe endpoints
  Reads existing services/, matches patterns
  Adds payment service alongside existing services
  Implements idempotency, webhook handling, reconciliation
→ T4 QA Engineer: Writes tests for billing endpoints
→ Final summary: "[N] billing endpoints, [M] tests passing"

[Artifacts written to existing project]
services/payment-service/
  handlers/
    webhook.ts
    payment.ts
  services/
    stripe-client.ts
    payment-processor.ts
  ...
```

### Example 3: User says "Review my code"

```
[User message]
"Review my code"

[Orchestrator]
1. Classifies: "Review" mode (single-skill)
2. No engagement mode prompt (single-skill overhead not worth it, uses Standard)
3. Invokes Code Reviewer only

[Code Reviewer]
→ Reads services/, frontend/, docs/architecture/
→ Runs 4-phase review in parallel:
  - Architecture Conformance: ADR compliance check
  - Code Quality: SOLID, DRY, complexity
  - Performance: N+1 queries, bundle size, caching
  - Test Quality: coverage, edge cases
→ Outputs: review-report.md with findings organized by severity
→ Writes receipt
→ Final summary: "[N] findings ([M] Critical, [K] High, [J] Medium)"
```

---

## 16. DIFFERENTIAL FACTORS (What Makes This Unique)

From DEV_PROTOCOL.md section 1.b:

| Differentiator | Implementation | Competitive Context |
|---|---|---|
| **Receipt enforcement** | Every agent writes JSON proof of completion. Orchestrator verifies artifacts exist. No receipt = task blocked. | Most systems rely on LLM self-reporting with no verifiable proof. |
| **Re-anchoring** | Orchestrator re-reads specs FROM DISK at every phase transition. Prevents context drift in long runs. | No adjacent system addresses multi-hour context degradation. |
| **Adversarial code review** | Reviewer assumes code is WRONG until proven right. Scales from Critical-only to hostile break scenarios. | Other review skills are neutral observers, not adversaries. |
| **Freshness protocol** | Agents detect volatile data (model IDs, versions, pricing, CVEs) and WebSearch to verify BEFORE implementing. | Ships training-data-era information; no temporal awareness. |
| **Boundary safety** | 6 structural patterns for system boundary bugs, derived from real PingBase deployment failures. | Novel — not in any other system. |
| **Constraint-driven architecture** | Architecture derived from user's scale, budget, team, compliance — not templates. 100 users → monolith; 10M users → microservices. | Other systems apply one-size-fits-all templates. |
| **Functional completeness** | Dead Element Rule: any UI element that renders but does nothing is Critical bug, not TODO. | No frontend skill enforces functional verification. |
| **Engagement modes** | Express/Standard/Thorough/Meticulous propagated to all 14 agents. User sets depth once at start. | Superpowers has planning mode but no granular per-skill depth control. |
| **Worktree isolation** | Each parallel agent runs in its own git worktree. Zero file race conditions. Auto-detect dirty state, auto-commit or fallback. | Superpowers uses worktrees but without orchestration or merge-back. |
| **Self-healing gates** | Gate rejection loops back to relevant agent for max 2 rework cycles (feed concerns, fix, re-verify). Pipeline never dead-ends. | Gate rejection stops pipeline everywhere else. No rework loop. |
| **Cost dashboard** | Effort tracking in every receipt (`files_read`, `files_written`, `tool_calls`). Pre-pipeline estimate + final aggregated summary. | No adjacent system provides cost visibility. Users fly blind on token spend. |
| **Harmonization protocol** | Recurring discipline to detect & fix conflicts across 14 skills + 8 protocols + 11 principles. Conflict matrix, authority hierarchy. | Multi-agent systems accumulate contradictions silently. No self-consistency mechanism. |

---

## 17. SUMMARY TABLE: EVERY CLAUDE-CODE NATIVE MECHANISM USED

| Claude-Code Feature | Used In | Purpose | Required For |
|---|---|---|---|
| **Skill tool** | orchestrator.py, all phase dispatchers | Dispatch to 14 specialized agents | Architecture routing, ability to invoke sub-skills |
| **SKILL.md frontmatter** | All 14 skill files | Metadata (name, description) | Skill discovery, marketplace listing |
| **Inline bash backticks** | All 14 skill SKILL.md headers | Load 8 protocols + config at startup | Protocol sharing without duplication |
| **AskUserQuestion** | All 14 skills | Mode-aware decision surfacing | Engagement mode system (Express → Meticulous) |
| **Team/TaskCreate** | Orchestrator (phase starts) | Coordinate multi-agent work | Parallel execution with task dependencies |
| **TaskUpdate** | All agents (on completion) | Mark tasks complete + write receipts | Receipt enforcement, task tracking |
| **TeamDelete** | Orchestrator (on end/reject) | Clean up agents | Agent lifecycle management |
| **Agent tool** | Phase dispatchers | Spawn parallel agents with worktrees | Wave-based parallelism, file isolation |
| **SessionStart hook** | Plugin system (`hooks/hooks.json`) | Detect production-grade projects, offer menu | Cross-session workflow persistence |
| **UserPromptSubmit activation** | Plugin system (`activation-rules.json`) | Keyword/intent matching → recommend skills | Auto-route requests to right skills |
| **Read tool** | QA, Security, Review, DevOps | Read source code, test files, configs | Code analysis at scale |
| **Bash read-only** | All skills, orchestrator | `find`, `grep`, `ls`, `git status`, `cat` | File discovery, artifact verification |
| **WebSearch** | Polymath, Freshness protocol | Verify volatile data before implement | Model IDs, versions, pricing, CVEs |
| **WebFetch** | Polymath integration | Extract details from URLs | Research, competitive analysis |
| **Glob** | Security, QA, DevOps | Find files matching patterns | Dependency scanning, artifact location |
| **Write** | All agents | Write deliverable files | Code, docs, configs, tests |
| **smart_outline** | Large file reads | Extract structure without full read | Token efficiency on large codebases |
| **Bash `!` inline** | All SKILL.md headers | Load markdown files inline | Protocol context injection |

---

## 18. NOT USED (To Guide Migration Planning)

The following Claude Code features are **explicitly NOT** used by production-grade:

- **Custom tools** — All work via standard tools (Read, Write, Bash, WebSearch, AskUserQuestion, etc.)
- **Subagent memory** — Agents don't persist memory across sessions; state via files in Claude-Production-Grade-Suite/
- **Custom models** — No specialized model configuration per skill
- **MCP servers** — No external integrations beyond native tools
- **Config files** — No `settings.json` modifications by plugin; user choices persist in `.orchestrator/settings.md`
- **Plugins** — Does not invoke other plugins; self-contained
- **Remote triggers** — No scheduled/triggered agents; all orchestrated synchronously

---

**END OF ARCHITECTURAL INVENTORY**

This inventory is complete and represents **every Claude-Code-native mechanism** the production-grade plugin uses. It is sufficient for planning a port to a different agent runtime: a team can take this document, map each mechanism to equivalent features in the target runtime, and execute a faithful reimplementation.