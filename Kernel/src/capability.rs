use core::fmt;

/// Coarse-grained risk class used by the kernel capability boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
#[repr(u8)]
pub enum RiskLevel {
    ReadOnly = 0,
    Mutating = 1,
    External = 2,
    Destructive = 3,
}

/// Stable kernel capability identifiers.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Capability {
    Observe = 0,
    Reason = 1,
    Create = 2,
    Execute = 3,
    Communicate = 4,
    Remember = 5,
    Device = 6,
    Network = 7,
    Process = 8,
    Storage = 9,
    Compute = 10,
}

impl Capability {
    pub const fn risk(self) -> RiskLevel {
        match self {
            Self::Observe | Self::Reason | Self::Remember => RiskLevel::ReadOnly,
            Self::Create | Self::Communicate | Self::Storage => RiskLevel::Mutating,
            Self::Execute | Self::Device | Self::Network | Self::Process | Self::Compute => RiskLevel::External,
        }
    }

    const fn bit(self) -> u64 {
        1u64 << (self as u8)
    }
}

/// Compact capability set suitable for kernel-space policy checks.
#[derive(Clone, Copy, Default, Eq, PartialEq)]
pub struct CapabilitySet {
    bits: u64,
}

impl CapabilitySet {
    pub const fn empty() -> Self {
        Self { bits: 0 }
    }

    pub const fn all() -> Self {
        Self { bits: (1u64 << 11) - 1 }
    }

    pub const fn grant(mut self, capability: Capability) -> Self {
        self.bits |= capability.bit();
        self
    }

    pub const fn revoke(mut self, capability: Capability) -> Self {
        self.bits &= !capability.bit();
        self
    }

    pub const fn contains(self, capability: Capability) -> bool {
        (self.bits & capability.bit()) != 0
    }

    pub const fn authorize(self, capability: Capability, maximum_risk: RiskLevel) -> bool {
        self.contains(capability) && capability.risk() <= maximum_risk
    }
}

impl fmt::Debug for CapabilitySet {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("CapabilitySet")
            .field("bits", &self.bits)
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capability_grant_and_revoke_are_deterministic() {
        let set = CapabilitySet::empty().grant(Capability::Observe).grant(Capability::Compute);
        assert!(set.contains(Capability::Observe));
        assert!(set.contains(Capability::Compute));
        assert!(!set.contains(Capability::Network));
        assert!(!set.revoke(Capability::Compute).contains(Capability::Compute));
    }

    #[test]
    fn policy_checks_capability_and_risk() {
        let set = CapabilitySet::empty().grant(Capability::Network);
        assert!(set.authorize(Capability::Network, RiskLevel::External));
        assert!(!set.authorize(Capability::Network, RiskLevel::ReadOnly));
    }
}
