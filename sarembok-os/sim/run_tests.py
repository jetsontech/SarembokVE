"""
Sarembok OS ? simulation acceptance suite.
Runs the same acceptance tests that the seL4 port must pass.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from kernel import Kernel, Tier  # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def fresh_kernel():
    fd, path = tempfile.mkstemp(suffix=".wal")
    os.close(fd)
    os.remove(path)
    return Kernel(wal_path=path), path


def test_boot():
    print("M0 ? boot")
    k, path = fresh_kernel()
    info = k.get_runtime_info()
    check("kernel reports runtime info", info["kernel"] == "sarembok-sim")
    check("fresh boot has 0 agents", info["agents_live"] == 0)
    os.remove(path)


def test_agent_lifecycle():
    print("M1 ? agent lifecycle + arena retention across kill/restore")
    k, path = fresh_kernel()
    aid = k.spawn_agent("demo", ["recall", "remember"])
    check("spawn returns id", aid == 1)
    check("agent is live", len(k.list_agents()) == 1)
    k.remember(aid, "deadline", "March 15", "SEMANTIC")
    k.kill_agent(aid)
    check("kill removes from live list", len(k.list_agents()) == 0)
    k.restore_agent(aid)
    check("restore brings agent back", len(k.list_agents()) == 1)
    refs = k.recall(aid, "deadline")
    check("memory retained across kill/restore",
          any(e.value == "March 15" for e in refs))
    os.remove(path)


def test_fault_isolation():
    print("M1 ? fault isolation")
    k, path = fresh_kernel()
    a = k.spawn_agent("crash_test", [])
    b = k.spawn_agent("survivor", [])
    k.remember(b, "important", "stay alive", "CORE")
    k.handle_fault(a, "SIGSEGV")
    live_ids = [x.id for x in k.list_agents()]
    check("faulted agent is DEAD", a not in live_ids)
    check("other agent unaffected", b in live_ids)
    refs = k.recall(b, "important")
    check("survivor memory intact",
          any(e.value == "stay alive" for e in refs))
    os.remove(path)


def test_persistence_across_restart():
    print("M2 ? persistence across kernel restart (WAL replay)")
    k, path = fresh_kernel()
    aid = k.spawn_agent("alice", [])
    k.remember(aid, "project", "Sarembok OS", "CORE")
    k.remember(aid, "mood", "focused", "WORKING")
    del k
    k2 = Kernel(wal_path=path)
    refs = k2.recall(aid, "project")
    check("CORE memory survives restart",
          any(e.value == "Sarembok OS" for e in refs))
    refs_mood = k2.recall(aid, "mood")
    check("agent identity survives restart", len(k2.list_agents()) >= 1)
    os.remove(path)


def test_eviction():
    print("M2 ? tiered kernel eviction")
    k, path = fresh_kernel()
    aid = k.spawn_agent("packed", [])
    k.remember(aid, "core_fact", "never evict me", "CORE")
    for i in range(500):
        k.remember(aid, f"working_{i}", f"v{i}", "WORKING")
    refs = k.recall(aid, "core_fact")
    check("CORE memory survives eviction pressure",
          any(e.value == "never evict me" for e in refs))
    os.remove(path)


def main():
    print("=" * 60)
    print("Sarembok OS ? simulation acceptance suite")
    print("=" * 60)
    test_boot()
    test_agent_lifecycle()
    test_fault_isolation()
    test_persistence_across_restart()
    test_eviction()
    print("=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
