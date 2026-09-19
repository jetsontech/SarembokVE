/* Sarembok OS ? agent-native syscall dispatch (port target).
 * Maps syscall numbers to the kernel component APIs.
 */
#include "sarembok_syscall.h"
#include <string.h>

sarembok_syscall_reply_t sarembok_syscall_dispatch(
    const sarembok_syscall_args_t *args)
{
    sarembok_syscall_reply_t r = { .status = -1, .result = 0 };
    if (!args) return r;

    switch (args->syscall_num) {
    case SAREMBOK_SYS_SPAWN_AGENT: {
        const char *name = (const char *)args->arg0;
        const capability_t *caps = (const capability_t *)args->arg1;
        uint32_t n = (uint32_t)args->arg2;
        agent_id_t id = agent_spawn(name, caps, n);
        r.status = id ? 0 : -1;
        r.result = id;
        break;
    }
    case SAREMBOK_SYS_REMEMBER: {
        agent_id_t id = (agent_id_t)args->arg0;
        const char *key = (const char *)args->arg1;
        const void *val = (const void *)args->arg2;
        /* arg3 packs tier in low 8 bits, len in upper 32 */
        mem_tier_t tier = (mem_tier_t)(args->arg3 & 0xFF);
        size_t len = (size_t)(args->arg3 >> 8);
        mem_id_t mid = agent_remember(id, key, val, len, tier);
        r.status = mid ? 0 : -1;
        r.result = mid;
        break;
    }
    case SAREMBOK_SYS_RECALL: {
        agent_id_t id = (agent_id_t)args->arg0;
        const char *q = (const char *)args->arg1;
        mem_id_t *out = (mem_id_t *)args->arg2;
        uint32_t max = (uint32_t)args->arg3;
        uint32_t count = 0;
        int rc = agent_recall(id, q, out, max, &count);
        r.status = rc;
        r.result = count;
        break;
    }
    case SAREMBOK_SYS_KILL_AGENT:
        r.status = agent_kill((agent_id_t)args->arg0); break;
    case SAREMBOK_SYS_RESTORE_AGENT:
        r.status = agent_restore((agent_id_t)args->arg0); break;
    case SAREMBOK_SYS_SUSPEND_AGENT:
        r.status = agent_suspend((agent_id_t)args->arg0); break;
    case SAREMBOK_SYS_RESUME_AGENT:
        r.status = agent_resume((agent_id_t)args->arg0); break;
    case SAREMBOK_SYS_SNAPSHOT_AGENT:
        r.status = agent_snapshot((agent_id_t)args->arg0); break;
    case SAREMBOK_SYS_EMBODY:
        r.result = agent_embody((agent_id_t)args->arg0,
                                (const char *)args->arg1);
        r.status = r.result ? 0 : -1;
        break;
    case SAREMBOK_SYS_DELEGATE:
        r.status = agent_delegate((agent_id_t)args->arg0,
                                  (agent_id_t)args->arg1,
                                  (const char *)args->arg2,
                                  args->arg3, 0);
        break;
    case SAREMBOK_SYS_LIST_AGENTS: {
        agent_id_t *out = (agent_id_t *)args->arg0;
        uint32_t max = (uint32_t)args->arg1;
        uint32_t count = 0;
        r.status = agent_list(out, max, &count);
        r.result = count;
        break;
    }
    default:
        r.status = -2; /* ENOSYS */
        break;
    }
    return r;
}
