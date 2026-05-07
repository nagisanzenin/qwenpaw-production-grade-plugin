#!/usr/bin/env bash
# Post-install verification for qwenpaw-production-grade-plugin.
#
# Run after `qwenpaw plugin install . --force` and a QwenPaw restart.
# Exits 0 if everything checks out, 1 if any required check fails.

set -u
fail=0
warn=0
pass() { echo "  ✓ $*"; }
fail() { echo "  ✗ $*"; fail=$((fail + 1)); }
warn() { echo "  ! $*"; warn=$((warn + 1)); }

echo "=== qwenpaw on PATH ==="
if command -v qwenpaw >/dev/null 2>&1; then
  pass "qwenpaw → $(command -v qwenpaw)"
  qwenpaw_ver=$(qwenpaw --version 2>/dev/null | head -1)
  pass "qwenpaw version: ${qwenpaw_ver:-unknown}"
else
  fail "qwenpaw not on PATH — activate your venv: source ~/Documents/Github/QwenPaw/.venv/bin/activate"
  echo
  echo "Aborting further checks."
  exit 1
fi

echo
echo "=== plugin registered ==="
plugin_list=$(qwenpaw plugin list 2>&1 || true)
if echo "$plugin_list" | grep -q "production-grade"; then
  pass "production-grade plugin is registered"
else
  fail "production-grade plugin not in 'qwenpaw plugin list'"
  echo "    → run: cd $(pwd) && qwenpaw plugin install . --force"
fi

echo
echo "=== bundled artifacts present ==="
n_skills=$(find skills -mindepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
n_protocols=$(find protocols -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "$n_skills" = "14" ]; then
  pass "skills/  ← 14 SKILL.md files"
else
  fail "skills/ has $n_skills SKILL.md files (expected 14)"
  echo "    → run: make port"
fi
if [ "$n_protocols" = "8" ]; then
  pass "protocols/  ← 8 .md files"
else
  fail "protocols/ has $n_protocols .md files (expected 8)"
  echo "    → run: make port"
fi

echo
echo "=== workspace install ==="
ws_root="$HOME/.qwenpaw/workspaces"
if [ ! -d "$ws_root" ]; then
  fail "$ws_root does not exist — run: qwenpaw init --defaults"
else
  for ws in "$ws_root"/*/; do
    [ -d "$ws" ] || continue
    name=$(basename "$ws")
    n_ws_skills=$(find "${ws}skills" -mindepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    n_ws_protocols=$(find "${ws}production-grade-protocols" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$n_ws_skills" -ge 14 ]; then
      pass "$name: $n_ws_skills skills, $n_ws_protocols protocols"
    else
      fail "$name: only $n_ws_skills skills (expected ≥14) — restart \`qwenpaw app\` to fire startup hook"
    fi

    if [ -f "${ws}skill.json" ]; then
      registered=$(python3 -c "
import json, sys
m = json.load(open('${ws}skill.json'))
pg = ['production-grade','polymath','product-manager','solution-architect',
      'software-engineer','frontend-engineer','qa-engineer','security-engineer',
      'code-reviewer','devops','sre','technical-writer','data-scientist','skill-maker']
have = m.get('skills', {})
missing = [s for s in pg if s not in have or not have[s].get('enabled')]
sys.stdout.write(str(14 - len(missing)))
" 2>/dev/null || echo "?")
      if [ "$registered" = "14" ]; then
        pass "$name skill.json: 14/14 production-grade skills enabled"
      else
        warn "$name skill.json: $registered/14 production-grade skills enabled (UI may not show all)"
      fi
    else
      warn "$name skill.json missing — UI Skills tab may be empty"
    fi
  done
fi

echo
echo "=== summary ==="
if [ "$fail" -gt 0 ]; then
  echo "  $fail FAIL, $warn warn"
  exit 1
elif [ "$warn" -gt 0 ]; then
  echo "  0 FAIL, $warn warn — usable, but check the !lines above"
  exit 0
else
  echo "  all checks passed"
  exit 0
fi
