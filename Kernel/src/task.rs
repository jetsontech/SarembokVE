use crate::capability::CapabilitySet;

pub type TaskId = u64;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum TaskState {
    Ready = 0,
    Running = 1,
    Blocked = 2,
    Completed = 3,
    Failed = 4,
}

/// Kernel task descriptor. Higher layers attach agent/execution identifiers;
/// the kernel only owns scheduling state and capability authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct KernelTask {
    pub id: TaskId,
    pub priority: u8,
    pub state: TaskState,
    pub capabilities: CapabilitySet,
    pub cpu_budget: u32,
}

impl KernelTask {
    pub const fn new(id: TaskId, priority: u8, capabilities: CapabilitySet, cpu_budget: u32) -> Self {
        Self {
            id,
            priority,
            state: TaskState::Ready,
            capabilities,
            cpu_budget,
        }
    }
}
