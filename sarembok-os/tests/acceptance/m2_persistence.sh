#!/usr/bin/env bash
set -e
python3 - <<'PY'
import sys, os, tempfile
sys.path.insert(0, "sim")
from kernel import Kernel
fd, path = tempfile.mkstemp(suffix=".wal"); os.close(fd); os.remove(path)
k = Kernel(wal_path=path)
aid = k.spawn_agent("alice", [])
k.remember(aid, "project", "Sarembok OS", "CORE")
k.remember(aid, "mood", "focused", "WORKING")
del k
k2 = Kernel(wal_path=path)
refs = k2.recall(aid, "project")
assert any(e.value == "Sarembok OS" for e in refs), "CORE memory not restored from WAL"
assert len(k2.list_agents()) >= 1, "agent identity not restored"
os.remove(path)
print("[ok] m2_persistence")
PY
