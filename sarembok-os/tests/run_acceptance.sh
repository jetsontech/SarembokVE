#!/usr/bin/env bash
set -e
echo "== Sarembok acceptance suite =="
python3 sim/run_tests.py
echo "== per-claim acceptance scripts =="
for t in tests/acceptance/m1_agent_lifecycle.sh \
         tests/acceptance/m1_fault_isolation.sh \
         tests/acceptance/m2_persistence.sh \
         tests/acceptance/m2_eviction.sh ; do
  bash "$t"
done
echo "== all acceptance tests passed =="
