use sarembok_kernel::{Capability, CapabilitySet, Kernel, KernelTask, RiskLevel, TaskState};

#[test]
fn kernel_foundation_executes_real_policy_and_schedule_path() {
    let mut kernel: Kernel<4> = Kernel::new();
    let authority = CapabilitySet::empty()
        .grant(Capability::Observe)
        .grant(Capability::Remember)
        .grant(Capability::Execute);

    assert!(authority.authorize(Capability::Observe, RiskLevel::ReadOnly));
    assert!(authority.authorize(Capability::Execute, RiskLevel::External));
    assert!(!authority.authorize(Capability::Execute, RiskLevel::ReadOnly));

    kernel
        .scheduler_mut()
        .enqueue(KernelTask::new(100, 10, authority, 1000))
        .unwrap();
    kernel
        .scheduler_mut()
        .enqueue(KernelTask::new(101, 20, authority, 1000))
        .unwrap();

    assert_eq!(kernel.scheduler().next_ready().unwrap().id, 101);
    kernel.scheduler_mut().set_state(101, TaskState::Running).unwrap();
    assert_eq!(kernel.scheduler().next_ready().unwrap().id, 100);
}
