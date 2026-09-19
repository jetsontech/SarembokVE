/* Sarembok OS ? seL4 root task entry point (port target).
 *
 * In the real build this is the seL4 root task that starts the Sarembok
 * kernel components alongside the Linux VM component. The bodies of the
 * extern helpers declared in agent_process.c and memory_arena.c are
 * provided here as weak stubs for reference; Antigravity replaces them
 * with real seL4 calls (seL4_TCB_Configure, seL4_Untyped_Retype, etc.).
 *
 * DO NOT ship this as-is. It is a structure reference, not a kernel.
 */
#include "agent_process/agent_process.h"
#include "memory_arena/memory_arena.h"
#include <stdio.h>
#include <stdarg.h>

/* ---- stubs: replace with real seL4 calls in the Antigravity build ---- */
uint64_t sel4_now_ns(void) { return 0; }

int sel4_log(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    vfprintf(stderr, fmt, ap); fputc('\n', stderr);
    va_end(ap);
    return 0;
}

int agent_tcb_create(seL4_TCB *t, seL4_CPtr *c, void **v, const char *n) {
    (void)t; (void)c; (void)v; (void)n;
    return -1; /* not implemented ? seL4 integration required */
}
void agent_tcb_destroy(seL4_TCB t, seL4_CPtr c) { (void)t; (void)c; }
void agent_tcb_suspend(seL4_TCB t) { (void)t; }
void agent_tcb_resume(seL4_TCB t) { (void)t; }

int wal_append(agent_id_t o, const memory_entry_t *e) { (void)o; (void)e; return 0; }
int wal_replay(agent_id_t o, memory_entry_t **out, uint32_t *count) {
    (void)o; *out = NULL; *count = 0; return 0;
}

int scheduler_submit(agent_id_t f, agent_id_t t, const char *s,
                     uint64_t d, uint64_t b) {
    (void)f; (void)t; (void)s; (void)d; (void)b; return 0;
}
uint64_t identity_embody(agent_id_t id, const char *s) { (void)id; (void)s; return 0; }

int main(void) {
    printf("[Sarembok Kernel] seL4 port target ? not a runnable OS.\n");
    printf("[Sarembok Kernel] Port sim/ semantics here. See docs/ANTIGRAVITY.md.\n");
    printf("[Sarembok Kernel] Do not ship until tests/acceptance pass against it.\n");
    return 0;
}
