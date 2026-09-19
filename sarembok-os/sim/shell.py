"""
Sarembok OS ? interactive shell over the kernel-model simulation.
Run: python3 sim/shell.py
"""
import shlex
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from kernel import Kernel, Tier  # noqa: E402

BANNER = """\
[Sarembok OS ? kernel-model simulation]
[Sarembok Kernel: sarembok-sim v0.1.0]
Type 'help' for commands. Type 'exit' to quit.
"""

HELP = """\
Commands:
  SpawnAgent <name> [cap1,cap2]      create an agent-process
  AgentRemember <id> <key> <value> [TIER]
  AgentRecall <id> <query>
  AgentKill <id>
  AgentRestore <id>
  AgentFault <id>                    simulate a fault (kernel must survive)
  ps                                 list live agents
  dmesg [n]                          kernel event log
  GetRuntimeInfo                     runtime status
  help / exit
"""


def main():
    wal = os.environ.get("SAREMBOK_WAL", "sarembok.wal")
    k = Kernel(wal_path=wal)
    print(BANNER)
    for line in k.dmesg(3):
        print(line)
    while True:
        try:
            raw = input("sarembok> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        parts = shlex.split(raw)
        cmd, args = parts[0], parts[1:]
        try:
            if cmd == "exit":
                break
            elif cmd == "help":
                print(HELP)
            elif cmd == "SpawnAgent":
                name = args[0]
                caps = args[1].split(",") if len(args) > 1 else ["recall", "remember"]
                aid = k.spawn_agent(name, caps)
                print(f'{{"agent_id": {aid}, "state": "RUNNING"}}')
            elif cmd == "AgentRemember":
                aid, key, val = int(args[0]), args[1], args[2]
                tier = args[3] if len(args) > 3 else "SEMANTIC"
                mid = k.remember(aid, key, val, tier)
                print(f'{{"mem_id": {mid}}}')
            elif cmd == "AgentRecall":
                aid, query = int(args[0]), args[1]
                results = k.recall(aid, query)
                out = [{"mem_id": e.id, "key": e.key, "value": e.value,
                        "tier": e.tier.name} for e in results]
                print(out)
            elif cmd == "AgentKill":
                k.kill_agent(int(args[0])); print('{"status": "DEAD"}')
            elif cmd == "AgentRestore":
                k.restore_agent(int(args[0])); print('{"status": "RUNNING"}')
            elif cmd == "AgentFault":
                k.handle_fault(int(args[0]), "injected"); print('{"status": "DEAD"}')
            elif cmd == "ps":
                print(f'{"PID":<6}{"NAME":<20}{"STATE":<12}')
                for a in k.list_agents():
                    print(f'{a.id:<6}{a.name:<20}{a.state.name:<12}')
            elif cmd == "dmesg":
                n = int(args[0]) if args else 20
                for line in k.dmesg(n):
                    print(line)
            elif cmd == "GetRuntimeInfo":
                print(k.get_runtime_info())
            else:
                print(f"unknown command: {cmd}")
        except Exception as e:
            print(f"error: {e}")
    print("[Sarembok OS] halted")


if __name__ == "__main__":
    main()
