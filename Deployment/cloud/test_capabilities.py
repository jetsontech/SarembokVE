import unittest

from capabilities import (
    SAREMBOK_CAPABILITIES,
    capability_authority_prompt,
    implemented_capabilities,
    planned_capabilities,
)


class CapabilityAuthorityTests(unittest.TestCase):
    def test_registry_has_only_known_statuses(self):
        allowed = {"implemented", "planned", "experimental"}
        self.assertTrue(SAREMBOK_CAPABILITIES)
        self.assertTrue(all(item.get("status") in allowed for item in SAREMBOK_CAPABILITIES.values()))

    def test_planned_capabilities_are_fail_closed(self):
        implemented = implemented_capabilities()
        planned = planned_capabilities()
        self.assertIn("memory", implemented)
        self.assertIn("live_research", implemented)
        self.assertNotIn("email_delivery", implemented)
        self.assertNotIn("slack_delivery", implemented)
        self.assertNotIn("push_notifications", implemented)
        self.assertIn("email_delivery", planned)
        self.assertIn("slack_delivery", planned)
        self.assertIn("push_notifications", planned)

    def test_capability_authority_prompt_is_explicit(self):
        prompt = capability_authority_prompt().lower()
        self.assertIn("authoritative", prompt)
        self.assertIn("planned", prompt)
        self.assertIn("do not invent", prompt)


if __name__ == "__main__":
    unittest.main()
