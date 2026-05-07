# qwenpaw-production-grade-plugin — operator shortcuts.
#
# Use `make` for the most common ops without remembering Python module paths.
# Run `make help` to see what's available.

.DEFAULT_GOAL := help
.PHONY: help install verify port port-clean upstream-pull update uninstall clean \
        runner-smoke runner-list dispatch-help

UPSTREAM ?= $(HOME)/Documents/Github/claude-code-production-grade-plugin

help:  ## show this list
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install:  ## install or reinstall the plugin into QwenPaw, then print verification reminder
	qwenpaw plugin install . --force
	qwenpaw plugin list | grep -E '^(production-grade|✓.*production-grade)' || true
	@echo
	@echo "Now restart 'qwenpaw app' (Ctrl-C then run again) so the startup hook fires."
	@echo "After restart: make verify"

verify:  ## sanity-check the install end-to-end
	@bash scripts/verify.sh

port:  ## refresh skills/ and protocols/ from upstream (incremental, keeps removed-upstream files)
	python3 -m production_grade.port_from_upstream

port-clean:  ## refresh skills/ and protocols/ from a clean slate
	python3 -m production_grade.port_from_upstream --clean

upstream-pull:  ## git pull the upstream Claude Code plugin, then re-port
	@if [ -d "$(UPSTREAM)" ]; then \
		echo "→ git pull in $(UPSTREAM)"; \
		git -C "$(UPSTREAM)" pull --ff-only; \
		$(MAKE) port-clean; \
	else \
		echo "Upstream not at $(UPSTREAM). Set UPSTREAM=/abs/path or clone:"; \
		echo "  git clone https://github.com/nagisanzenin/claude-code-production-grade-plugin $(UPSTREAM)"; \
		exit 1; \
	fi

update: upstream-pull install  ## upstream-pull, port, install — full refresh

uninstall:  ## remove the plugin from QwenPaw (keeps your workspace files)
	qwenpaw plugin uninstall production-grade

clean:  ## remove pycache, dist, build, logs (does NOT touch skills/ or protocols/)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info
	rm -rf logs

# ─── v0.2-alpha: specialist ACP runners ─────────────────────────────────────

runner-smoke:  ## load polymath runner, print system-prompt size; verifies bundled skills+protocols + acp SDK
	python3 -m production_grade.specialists --role polymath --smoke

runner-list:  ## list ACP runners registered in default agent's agent.json
	@python3 -c "import json,pathlib; p=pathlib.Path.home()/'.qwenpaw'/'workspaces'/'default'/'agent.json'; \
	d=json.loads(p.read_text()) if p.exists() else {}; \
	acp=(d.get('acp') or {}).get('agents') or {}; \
	pgs=sorted(k for k in acp if k.startswith('pgs-')); \
	print(f'{len(pgs)} pgs-* runners registered:'); [print(f'  {k}') for k in pgs]"

dispatch-help:  ## print example delegate_external_agent calls for testing in chat
	@echo "In QwenPaw chat, run a single specialist directly to verify ACP wiring:"
	@echo
	@echo "  call delegate_external_agent with action=start, runner=pgs-polymath-a,"
	@echo "  message=\"in 3 sentences, what trade-offs matter when choosing FastAPI vs Flask?\""
	@echo
	@echo "If the runner streams text back, your v0.2-alpha install is functional."
	@echo "Set OPENAI_API_KEY in the shell that started qwenpaw app, or via Settings → Models → MCP."
