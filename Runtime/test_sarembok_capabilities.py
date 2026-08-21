import unittest

from sarembok_capabilities import (
    CapabilityClass,
    CapabilityDescriptor,
    CapabilityPolicy,
    CapabilityRegistry,
    RiskLevel,
)


class CapabilityBoundaryTests(unittest.TestCase):
    def test_permitted_capability_executes(self):
        registry = CapabilityRegistry()
        registry.register(
            CapabilityDescriptor("test.observe", "1", CapabilityClass.OBSERVE, ("camera.read",)),
            lambda value: value,
        )
        policy = CapabilityPolicy(
            allowed_capabilities=frozenset({"test.observe"}),
            approved_permissions=frozenset({"camera.read"}),
        )
        self.assertEqual(registry.invoke("test.observe", policy, value="frame"), "frame")

    def test_missing_permission_denies(self):
        registry = CapabilityRegistry()
        registry.register(
            CapabilityDescriptor("test.execute", "1", CapabilityClass.EXECUTE, ("process.run",)),
            lambda: "ran",
        )
        policy = CapabilityPolicy(allowed_capabilities=frozenset({"test.execute"}))
        with self.assertRaises(PermissionError):
            registry.invoke("test.execute", policy)

    def test_high_risk_requires_explicit_policy(self):
        registry = CapabilityRegistry()
        registry.register(
            CapabilityDescriptor("test.high", "1", CapabilityClass.EXECUTE, risk_level=RiskLevel.HIGH),
            lambda: "ran",
        )
        policy = CapabilityPolicy(allowed_capabilities=frozenset({"test.high"}))
        with self.assertRaises(PermissionError):
            registry.invoke("test.high", policy)


if __name__ == "__main__":
    unittest.main()
