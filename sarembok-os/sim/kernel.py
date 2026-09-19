"""
Sarembok OS — kernel-model simulation.

This is a RUNNABLE implementation of the Sarembok kernel semantics.
It is NOT an operating system. It models, faithfully:

  - an agent-process table with real lifecycle (NEW/RUNNING/SUSPENDED/DEAD)
  - a kernel-managed persistent memory arena with tiered eviction
    (CORE never evicted; WORKING evicted first; SEMANTIC by LRU+retention;
    SPATIAL last)
  - fault isolation: an agent fault marks it DEAD, retains its arena,
    and leaves other agents + the kernel unaffected
  - a write-ahead log / SQLite-WAL on disk so memory survives process restart
    (this is what stands in for "survives reboot")
  - the agent-native syscall surface from docs/SYSCALLS.md

Antigravity ports this behavior onto seL4 in kernel/. The acceptance
tests in tests/acceptance/ run against THIS module and must pass before
the seL4 port is considered correct.
"""
import json
import os
import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from store_sqlite import SQLiteStore


class AgentState(Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"
    DEAD = "DEAD"


class Tier(Enum):
    CORE = 0        # never evict
    SEMANTIC = 1    # LRU + retention evictable
    WORKING = 2     # session-scoped, evicted first
    SPATIAL = 3     # embodiment-bound, evicted last


CAP_READ = 1 << 0
CAP_WRITE = 1 << 1
CAP_DELEGATE = 1 << 2
CAP_EMBODY = 1 << 3

SEMANTIC_RETENTION_NS = 30 * 24 * 3600 * 1_000_000_000
SEMANTIC_ACCESS_THRESHOLD = 3
ARENA_DEFAULT_CAPACITY = 256 * 1024 * 1024


@dataclass
class MemoryEntry:
    id: int
    owner: int
    key: str
    value: object
    tier: Tier
    created_ns: int
    last_access_ns: int
    access_count: int = 0

    def size_bytes(self) -> int:
        return len(self.key.encode()) + len(json.dumps(self.value).encode()) + 128


@dataclass
class AgentProcess:
    id: int
    name: str
    state: AgentState
    capabilities: dict
    arena_root: int
    created_ns: int
    last_active_ns: int
    cpu_time_ns: int = 0
    cost_consumed: int = 0


class MemoryArena:
    """Kernel-managed persistent memory arena. Eviction policy lives HERE."""

    def __init__(self, owner: int, store: SQLiteStore,
                 capacity_bytes: int = ARENA_DEFAULT_CAPACITY):
        self.owner = owner
        self._store = store
        self.wal = store  # compatibility alias
        self.capacity_bytes = capacity_bytes
        self.used_bytes = 0
        self.entries: dict[int, MemoryEntry] = {}
        self._next_mem_id = (owner << 32)
        self._lock = threading.Lock()

    def store(self, key: str, value, tier: Tier) -> int:
        with self._lock:
            entry = MemoryEntry(
                id=self._next_mem_id + 1,
                owner=self.owner,
                key=key,
                value=value,
                tier=tier,
                created_ns=time.time_ns(),
                last_access_ns=time.time_ns(),
            )
            needed = entry.size_bytes()
            if self.used_bytes + needed > self.capacity_bytes:
                if not self._evict_under_pressure(needed):
                    raise MemoryError("arena capacity exceeded, eviction failed")
            self._next_mem_id += 1
            self.entries[entry.id] = entry
            self.used_bytes += needed
            self._store.append({
                "op": "store", "owner": self.owner, "id": entry.id,
                "key": entry.key, "value": entry.value,
                "tier": entry.tier.name, "created_ns": entry.created_ns,
                "last_access_ns": entry.last_access_ns,
                "access_count": entry.access_count,
            })
            self._store.upsert_memory({
                "id": entry.id, "owner": self.owner, "key": entry.key,
                "value": entry.value, "tier": entry.tier.name,
                "created_ns": entry.created_ns, "last_access_ns": entry.last_access_ns,
                "access_count": entry.access_count,
            })
            return entry.id

    def query(self, query: str, max_results: int = 64) -> list:
        with self._lock:
            out = []
            q = query.lower().strip()
            terms = [t for t in q.split() if len(t) > 2 and t not in ('what', 'is', 'the', 'my', 'about', 'where', 'show', 'tell')]
            for entry in self.entries.values():
                k_lower = entry.key.lower()
                v_str = str(entry.value).lower()
                match = (q in k_lower or q in v_str or k_lower in q)
                if not match and terms:
                    match = any(t in k_lower or t in v_str for t in terms)
                if match:
                    entry.last_access_ns = time.time_ns()
                    entry.access_count += 1
                    self._store.upsert_memory({
                        "id": entry.id, "owner": self.owner, "key": entry.key,
                        "value": entry.value, "tier": entry.tier.name,
                        "created_ns": entry.created_ns, "last_access_ns": entry.last_access_ns,
                        "access_count": entry.access_count,
                    })
                    out.append(entry)
                    if len(out) >= max_results:
                        break
            return out

    def _evict_under_pressure(self, needed_bytes: int) -> bool:
        freed = 0
        now = time.time_ns()
        for target in (Tier.WORKING, Tier.SEMANTIC, Tier.SPATIAL):
            if freed >= needed_bytes:
                break
            candidates = [e for e in self.entries.values() if e.tier == target]
            candidates.sort(key=lambda e: e.last_access_ns)
            for entry in candidates:
                if freed >= needed_bytes:
                    break
                evict = False
                if target == Tier.WORKING:
                    evict = True
                elif target == Tier.SEMANTIC:
                    evict = (entry.access_count < SEMANTIC_ACCESS_THRESHOLD) or \
                            (now - entry.last_access_ns > SEMANTIC_RETENTION_NS)
                elif target == Tier.SPATIAL:
                    evict = True
                if evict:
                    freed += entry.size_bytes()
                    self.used_bytes -= entry.size_bytes()
                    del self.entries[entry.id]
                    self._store.append({
                        "op": "evict", "owner": self.owner, "id": entry.id,
                        "tier": entry.tier.name,
                    })
                    self._store.delete_memory(entry.id)
        return freed >= needed_bytes

    def snapshot_entries(self) -> list:
        return list(self.entries.values())


class Kernel:
    """The Sarembok kernel-model. Owns the agent-process table + arenas."""

    def __init__(self, db_path: str = "sarembok.db", wal_path: str = None):
        if wal_path is not None:
            db_path = wal_path
        self.store = SQLiteStore(db_path)
        self.wal = self.store  # compatibility alias
        self._agents: dict[int, AgentProcess] = {}
        self._arenas: dict[int, MemoryArena] = {}
        self._next_agent_id = 1
        self._lock = threading.RLock()
        self._event_log: list[str] = []
        self._boot_ns = time.time_ns()
        self._replay_wal()

    def close(self) -> None:
        if hasattr(self, 'store') and self.store:
            self.store.close()

    def __del__(self):
        self.close()

    def _log(self, msg: str) -> None:
        ts = time.time_ns()
        self._event_log.append(f"[{ts}] {msg}")

    def _replay_wal(self) -> None:
        """Rebuild state from SQLite-WAL. This is what stands in for reboot."""
        agents = self.store.all_agents()
        for a in agents:
            caps = a["capabilities"]
            if isinstance(caps, list):
                caps = {c: CAP_READ | CAP_WRITE for c in caps}
            self._agents[a["id"]] = AgentProcess(
                id=a["id"], name=a["name"],
                state=AgentState(a["state"]),
                capabilities=caps,
                arena_root=a["id"],
                created_ns=a["created_ns"],
                last_active_ns=a["last_active_ns"],
            )
            if a["id"] >= self._next_agent_id:
                self._next_agent_id = a["id"] + 1

        mems = self.store.all_memories()
        for m in mems:
            arena = self._arenas.get(m["owner"])
            if arena is None:
                arena = MemoryArena(m["owner"], self.store)
                self._arenas[m["owner"]] = arena
            entry = MemoryEntry(
                id=m["id"], owner=m["owner"], key=m["key"],
                value=m["value"], tier=Tier[m["tier"]],
                created_ns=m["created_ns"],
                last_access_ns=m["last_access_ns"],
                access_count=m["access_count"],
            )
            arena.entries[entry.id] = entry
            arena.used_bytes += entry.size_bytes()

        self._log(f"[kernel] boot: restored {len(self._agents)} agents, "
                  f"{len(mems)} memories from SQLite-WAL")

    # ---------- syscalls (docs/SYSCALLS.md) ----------

    def spawn_agent(self, name: str, capabilities: list) -> int:
        with self._lock:
            aid = self._next_agent_id
            self._next_agent_id += 1
            caps = {c: CAP_READ | CAP_WRITE for c in capabilities}
            agent = AgentProcess(
                id=aid, name=name, state=AgentState.RUNNING,
                capabilities=caps, arena_root=aid,
                created_ns=time.time_ns(), last_active_ns=time.time_ns(),
            )
            self._agents[aid] = agent
            self._arenas[aid] = MemoryArena(aid, self.store)
            self.store.append({
                "op": "agent", "id": aid, "name": name,
                "state": AgentState.RUNNING.name,
                "capabilities": capabilities,
                "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })
            self.store.upsert_agent({
                "id": aid, "name": name, "state": AgentState.RUNNING.name,
                "capabilities": caps, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })
            self._log(f"[agent] spawned id={aid} name={name}")
            return aid

    def remember(self, agent_id: int, key: str, value, tier: str = "SEMANTIC") -> int:
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.state == AgentState.DEAD:
                raise ValueError(f"no live agent {agent_id}")
            agent.last_active_ns = time.time_ns()
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": agent.state.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })
            return self._arenas[agent_id].store(key, value, Tier[tier])

    def recall(self, agent_id: int, query: str, max_results: int = 64) -> list:
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.state == AgentState.DEAD:
                raise ValueError(f"no live agent {agent_id}")
            agent.last_active_ns = time.time_ns()
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": agent.state.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })
            return self._arenas[agent_id].query(query, max_results)

    def kill_agent(self, agent_id: int) -> None:
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.state == AgentState.DEAD:
                raise ValueError(f"no live agent {agent_id}")
            agent.state = AgentState.DEAD
            record = {"op": "agent", "id": agent.id, "name": agent.name,
                      "state": AgentState.DEAD.name,
                      "capabilities": list(agent.capabilities.keys()),
                      "created_ns": agent.created_ns,
                      "last_active_ns": agent.last_active_ns}
            self.store.append(record)
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": AgentState.DEAD.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })
            self._log(f"[agent] killed id={agent_id} (arena retained)")

    def restore_agent(self, agent_id: int) -> None:
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.state != AgentState.DEAD:
                raise ValueError(f"agent {agent_id} not restorable")
            agent.state = AgentState.RUNNING
            agent.last_active_ns = time.time_ns()
            record = {"op": "agent", "id": agent.id, "name": agent.name,
                      "state": AgentState.RUNNING.name,
                      "capabilities": list(agent.capabilities.keys()),
                      "created_ns": agent.created_ns,
                      "last_active_ns": agent.last_active_ns}
            self.store.append(record)
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": AgentState.RUNNING.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })
            self._log(f"[agent] restored id={agent_id} name={agent.name}")

    def suspend_agent(self, agent_id: int) -> None:
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.state != AgentState.RUNNING:
                raise ValueError(f"cannot suspend agent {agent_id}")
            agent.state = AgentState.SUSPENDED
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": AgentState.SUSPENDED.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })

    def resume_agent(self, agent_id: int) -> None:
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.state != AgentState.SUSPENDED:
                raise ValueError(f"cannot resume agent {agent_id}")
            agent.state = AgentState.RUNNING
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": AgentState.RUNNING.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })

    def handle_fault(self, agent_id: int, reason: str = "unknown") -> None:
        """Agent fault. Kernel survives. Arena is retained. This is the test."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return
            self._log(f"[agent] fault id={agent_id} reason={reason} "
                      f"arena retained, kernel stable")
            agent.state = AgentState.DEAD
            self.store.upsert_agent({
                "id": agent.id, "name": agent.name, "state": AgentState.DEAD.name,
                "capabilities": agent.capabilities, "created_ns": agent.created_ns,
                "last_active_ns": agent.last_active_ns,
            })

    def list_agents(self) -> list:
        with self._lock:
            return [a for a in self._agents.values() if a.state != AgentState.DEAD]

    def get_runtime_info(self) -> dict:
        live = self.list_agents()
        total_memories = sum(len(a.entries) for a in self._arenas.values())
        return {
            "kernel": "sarembok-sim",
            "version": "0.1.0",
            "uptime_ms": (time.time_ns() - self._boot_ns) // 1_000_000,
            "agents_live": len(live),
            "agents_total": len(self._agents),
            "memories_total": total_memories,
            "wal_path": self.store.path,
        }

    def dmesg(self, n: int = 20) -> list:
        return self._event_log[-n:]
