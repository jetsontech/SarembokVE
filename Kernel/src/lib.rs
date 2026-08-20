#![cfg_attr(not(test), no_std)]

//! Sarembok Kernel Foundation.
//!
//! This crate defines the first native kernel-facing primitives for Sarembok's
//! intelligence-first computing environment. It is deliberately independent
//! of Linux, Windows, Unreal Engine, and any model provider.

pub mod capability;
pub mod scheduler;
pub mod task;

pub use capability::{Capability, CapabilitySet, RiskLevel};
pub use scheduler::{Scheduler, SchedulerError};
pub use task::{TaskId, TaskState, KernelTask};

/// Kernel-wide error surface. The first version is intentionally small and
/// deterministic; platform-specific errors belong in architecture adapters.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KernelError {
    CapabilityDenied,
    InvalidTask,
    SchedulerFull,
}

/// Minimal kernel composition root.
pub struct Kernel<const N: usize> {
    scheduler: Scheduler<N>,
}

impl<const N: usize> Kernel<N> {
    pub const fn new() -> Self {
        Self { scheduler: Scheduler::new() }
    }

    pub fn scheduler(&self) -> &Scheduler<N> {
        &self.scheduler
    }

    pub fn scheduler_mut(&mut self) -> &mut Scheduler<N> {
        &mut self.scheduler
    }
}

impl<const N: usize> Default for Kernel<N> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kernel_starts_empty() {
        let kernel: Kernel<8> = Kernel::new();
        assert_eq!(kernel.scheduler().len(), 0);
    }
}
