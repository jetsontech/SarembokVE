# Sarembok Syscall Surface

Agent-native syscalls. In `sim/` these are Python methods on Kernel.
In `kernel/` they are the seL4 IPC surface. Same names, same semantics.

| Syscall | Number | Signature | Returns |
|---|---|---|---|
| spawn_agent | 0x100 | (name, caps) -> agent_id | agent_id |
| recall | 0x101 | (agent_id, query, max) -> refs | count |
| remember | 0x102 | (agent_id, key, value, tier) -> mem_id | mem_id |
| delegate | 0x103 | (from, to, task, deadline, budget) -> task_id | task_id |
| embody | 0x104 | (agent_id, surface) -> session_id | session_id |
| suspend_agent | 0x105 | (agent_id) -> status | status |
| resume_agent | 0x106 | (agent_id) -> status | status |
| kill_agent | 0x107 | (agent_id) -> status | status |
| snapshot_agent | 0x108 | (agent_id) -> status | status |
| restore_agent | 0x109 | (agent_id) -> status | status |
| query_capability | 0x10A | (agent_id, cap) -> perms | perms |
| list_agents | 0x10B | () -> agent_list | count |
