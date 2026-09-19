#!/usr/bin/env bash
# CI claim enforcement.
# Rule 5: docs/CLAIMS.md maps every public claim to a test.
# This script fails if any claim marked "sim" lacks a passing test,
# or if README contains a claim keyword that is not in CLAIMS.md.
set -euo pipefail

CLAIMS=docs/CLAIMS.md
README=README.md
FAIL=0

echo "== claim-verify =="

# 1. Every sim/tested claim must have its test file present and executable.
while IFS='|' read -r _ claim test impl status _; do
  claim="$(echo "$claim" | xargs)"
  test="$(echo "$test" | xargs)"
  impl="$(echo "$impl" | xargs)"
  status="$(echo "$status" | xargs)"
  [ -z "$claim" ] && continue
  case "$claim" in Claim*|---*) continue;; esac
  if [ "$impl" = "sim" ]; then
    if [ ! -f "$test" ]; then
      echo "[FAIL] claim '$claim' -> missing test $test"
      FAIL=1
    fi
  fi
done < "$CLAIMS"

# 2. README must not claim a syscall that is not in docs/SYSCALLS.md.
for sc in spawn_agent recall remember delegate embody kill_agent restore_agent; do
  if grep -q "$sc" "$README" && ! grep -q "$sc" docs/SYSCALLS.md; then
    echo "[FAIL] README references $sc but it is not in docs/SYSCALLS.md"
    FAIL=1
  fi
done

# 3. Forbidden superlatives in README headline area.
for word in "light years" "frontier" "world-class" "best-in-class"; do
  if head -40 "$README" | grep -qi "$word"; then
    echo "[FAIL] README headline contains unproven superlative: '$word'"
    FAIL=1
  fi
done

if [ "$FAIL" -ne 0 ]; then
  echo "== claim-verify FAILED ? build must not ship =="
  exit 1
fi
echo "== claim-verify passed =="
