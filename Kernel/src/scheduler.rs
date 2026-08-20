use crate::task::{KernelTask, TaskId, TaskState};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SchedulerError {
    Full,
    DuplicateTask,
    UnknownTask,
}

/// Deterministic fixed-capacity scheduler core.
///
/// This is intentionally heap-free so the same policy engine can later sit
/// beneath the Sarembok OS on a no_std target. Scheduling policy is kept
/// separate from architecture-specific interrupt/context-switch code.
pub struct Scheduler<const N: usize> {
    tasks: [Option<KernelTask>; N],
    len: usize,
}

impl<const N: usize> Scheduler<N> {
    pub const fn new() -> Self {
        Self {
            tasks: [None; N],
            len: 0,
        }
    }

    pub const fn len(&self) -> usize {
        self.len
    }

    pub fn enqueue(&mut self, task: KernelTask) -> Result<(), SchedulerError> {
        if self.tasks.iter().flatten().any(|existing| existing.id == task.id) {
            return Err(SchedulerError::DuplicateTask);
        }

        let slot = self.tasks.iter().position(Option::is_none).ok_or(SchedulerError::Full)?;
        self.tasks[slot] = Some(task);
        self.len += 1;
        Ok(())
    }

    pub fn remove(&mut self, id: TaskId) -> Result<KernelTask, SchedulerError> {
        let slot = self
            .tasks
            .iter()
            .position(|task| task.map(|value| value.id) == Some(id))
            .ok_or(SchedulerError::UnknownTask)?;

        let task = self.tasks[slot].take().ok_or(SchedulerError::UnknownTask)?;
        self.len -= 1;
        Ok(task)
    }

    pub fn get(&self, id: TaskId) -> Result<KernelTask, SchedulerError> {
        self.tasks
            .iter()
            .flatten()
            .find(|task| task.id == id)
            .copied()
            .ok_or(SchedulerError::UnknownTask)
    }

    /// Select the highest-priority Ready task. Ties resolve to the lowest ID,
    /// giving deterministic scheduling independent of allocation order.
    pub fn next_ready(&self) -> Option<KernelTask> {
        self.tasks
            .iter()
            .flatten()
            .filter(|task| task.state == TaskState::Ready)
            .copied()
            .min_by(|a, b| b.priority.cmp(&a.priority).then_with(|| a.id.cmp(&b.id)))
    }

    pub fn set_state(&mut self, id: TaskId, state: TaskState) -> Result<(), SchedulerError> {
        let slot = self
            .tasks
            .iter()
            .position(|task| task.map(|value| value.id) == Some(id))
            .ok_or(SchedulerError::UnknownTask)?;
        if let Some(task) = &mut self.tasks[slot] {
            task.state = state;
        }
        Ok(())
    }
}

impl<const N: usize> Default for Scheduler<N> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capability::{Capability, CapabilitySet};

    fn task(id: TaskId, priority: u8) -> KernelTask {
        KernelTask::new(id, priority, CapabilitySet::empty().grant(Capability::Observe), 100)
    }

    #[test]
    fn scheduler_is_bounded_and_rejects_duplicates() {
        let mut scheduler: Scheduler<2> = Scheduler::new();
        assert!(scheduler.enqueue(task(1, 1)).is_ok());
        assert_eq!(scheduler.enqueue(task(1, 2)), Err(SchedulerError::DuplicateTask));
        assert!(scheduler.enqueue(task(2, 2)).is_ok());
        assert_eq!(scheduler.enqueue(task(3, 3)), Err(SchedulerError::Full));
    }

    #[test]
    fn scheduler_selects_priority_then_id() {
        let mut scheduler: Scheduler<4> = Scheduler::new();
        scheduler.enqueue(task(20, 5)).unwrap();
        scheduler.enqueue(task(10, 5)).unwrap();
        scheduler.enqueue(task(30, 9)).unwrap();
        assert_eq!(scheduler.next_ready().unwrap().id, 30);
        scheduler.set_state(30, TaskState::Blocked).unwrap();
        assert_eq!(scheduler.next_ready().unwrap().id, 10);
    }
}
