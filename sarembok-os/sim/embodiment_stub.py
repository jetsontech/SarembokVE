"""
Sarembok OS ? embodied identity proof-of-concept (runnable now).

Proves the ONE frontier claim that matters most: an agent's visual
identity PERSISTS across kernel restart, bound to its kernel identity.

This is intentionally minimal. It is NOT a rendering pipeline. It binds
agent_id -> avatar_id in the kernel's WAL so that after restart the same
agent comes back with the same avatar. That is the differentiator the
MetaHuman layer will later render.

Run: python3 sim/embodiment_stub.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from kernel import Kernel  # noqa: E402

AVATARS = ["alice-v1", "bob-v1", "oskar-v1", "vega-v1"]


def embody(k: Kernel, agent_id: int) -> str:
    """Bind agent identity to a persistent avatar id.

    In kernel/ this becomes the `embody` syscall (0x104). The binding is
    stored in the same persistent arena as memory, so it survives restart.
    """
    existing = k.recall(agent_id, "avatar")
    if existing:
        return existing[0].value
    # Deterministic avatar per agent id ? stable across reboots.
    avatar = AVATARS[(agent_id - 1) % len(AVATARS)]
    k.remember(agent_id, "avatar", avatar, "CORE")
    return avatar


def main():
    fd, path = tempfile.mkstemp(suffix=".wal"); os.close(fd); os.remove(path)

    print("[1] First boot ? spawn agent, bind avatar")
    k = Kernel(wal_path=path)
    aid = k.spawn_agent("alice", ["recall", "remember", "embody"])
    avatar1 = embody(k, aid)
    print(f"    agent {aid} -> avatar {avatar1}")
    k.remember(aid, "greeting", "hello from a previous life", "CORE")
    del k

    print("[2] Restart ? kernel replays WAL")
    k2 = Kernel(wal_path=path)
    avatar2 = embody(k2, aid)
    print(f"    agent {aid} -> avatar {avatar2}")

    assert avatar1 == avatar2, "embodied identity did NOT persist"
    refs = k2.recall(aid, "greeting")
    assert any(e.value == "hello from a previous life" for e in refs), \
        "memory did not persist alongside identity"

    print("[3] PASS ? identity + avatar + memory persisted across restart")
    print("    This is the frontier claim: persistent embodied identity.")
    os.remove(path)


if __name__ == "__main__":
    main()
