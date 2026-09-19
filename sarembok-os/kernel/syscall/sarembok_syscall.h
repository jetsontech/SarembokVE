/* Sarembok OS ? agent-native syscall table (port target).
 * Mirrors docs/SYSCALLS.md. In the seL4 build these are IPC endpoints.
 */
#ifndef SAREMBOK_SYSCALL_H
#define SAREMBOK_SYSCALL_H

#include "../agent_process/agent_process.h"
#include "../memory_arena/memory_arena.h"

#define SAREMBOK_SYS_SPAWN_AGENT     0x100
#define SAREMBOK_SYS_RECALL          0x101
#define SAREMBOK_SYS_REMEMBER        0x102
#define SAREMBOK_SYS_DELEGATE        0x103
#define SAREMBOK_SYS_EMBODY          0x104
#define SAREMBOK_SYS_SUSPEND_AGENT   0x105
#define SAREMBOK_SYS_RESUME_AGENT    0x106
#define SAREMBOK_SYS_KILL_AGENT      0x107
#define SAREMBOK_SYS_SNAPSHOT_AGENT  0x108
#define SAREMBOK_SYS_RESTORE_AGENT   0x109
#define SAREMBOK_SYS_QUERY_CAPABILITY 0x10A
#define SAREMBOK_SYS_LIST_AGENTS     0x10B

typedef struct {
    uint32_t  syscall_num;
    uint64_t  arg0;
    uint64_t  arg1;
    uint64_t  arg2;
    uint64_t  arg3;
} sarembok_syscall_args_t;

typedef struct {
    int64_t   status;   /* 0 = ok, negative = error */
    uint64_t  result;
} sarembok_syscall_reply_t;

/* Kernel-side dispatch. Called by the seL4 IPC handler for the
 * Sarembok kernel component's endpoint capability. */
sarembok_syscall_reply_t sarembok_syscall_dispatch(
    const sarembok_syscall_args_t *args);

#endif /* SAREMBOK_SYSCALL_H */
