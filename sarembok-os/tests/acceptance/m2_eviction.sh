#!/usr/bin/env bash
set -e
python3 - <<'PY'
import sys, os, tempfile
sys.path.insert(0, "sim")
from kernel import Kernel
fd, path = tempfile.mkstemp(suffix=".wal"); os.close(fd); os.remove(path)
k = Kernel(wal_path=path)
aid = k.spawn_agent("packed", [])
k.remember(aid, "core_fact", "never evict me", "CORE")
for i in range(500):
    k.remember(aid, f"working_{i}", f"v{i}", "WORKING")
refs = k.recall(aid, "core_fact")
assert any(e.value == "never evict me" for e in refs), "CORE was evicted under pressure"
os.remove(path)
print("[ok] m2_eviction")
PY
