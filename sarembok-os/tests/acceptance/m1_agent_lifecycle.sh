#!/usr/bin/env bash
set -e
python3 - <<'PY'
import sys, os, tempfile
sys.path.insert(0, "sim")
from kernel import Kernel
fd, path = tempfile.mkstemp(suffix=".wal"); os.close(fd); os.remove(path)
k = Kernel(wal_path=path)
aid = k.spawn_agent("demo", ["recall","remember"])
assert aid == 1, "spawn failed"
k.remember(aid, "deadline", "March 15", "SEMANTIC")
k.kill_agent(aid)
k.restore_agent(aid)
refs = k.recall(aid, "deadline")
assert any(e.value == "March 15" for e in refs), "memory lost across kill/restore"
os.remove(path)
print("[ok] m1_agent_lifecycle")
PY
