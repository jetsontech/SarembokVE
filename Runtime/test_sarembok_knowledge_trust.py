import unittest

from sarembok_knowledge_trust import (
    KnowledgeEvidence,
    KnowledgeStatus,
    KnowledgeTrustManager,
    TrustedKnowledge,
)


class KnowledgeTrustTests(unittest.TestCase):
    def setUp(self):
        self.manager = KnowledgeTrustManager()

    def test_verified_evidence_can_promote_knowledge(self):
        self.manager.register(
            TrustedKnowledge(
                "k1", "contract tests reduce regressions", 0.8,
                evidence=[KnowledgeEvidence("e1", reproduced=True, verification_score=0.9)],
            )
        )
        result = self.manager.validate("k1")
        self.assertEqual(result.status, KnowledgeStatus.TRUSTED)
        self.assertGreaterEqual(result.confidence, 0.75)

    def test_unverified_knowledge_is_quarantined(self):
        self.manager.register(TrustedKnowledge("k1", "unverified lesson", 0.9))
        result = self.manager.validate("k1")
        self.assertEqual(result.status, KnowledgeStatus.QUARANTINED)

    def test_low_verification_stays_pending(self):
        self.manager.register(
            TrustedKnowledge(
                "k1", "possible lesson", 0.5,
                evidence=[KnowledgeEvidence("e1", reproduced=True, verification_score=0.5)],
            )
        )
        result = self.manager.validate("k1")
        self.assertEqual(result.status, KnowledgeStatus.PENDING)

    def test_knowledge_can_be_expired_or_quarantined(self):
        self.manager.register(TrustedKnowledge("k1", "lesson", 0.8))
        self.assertEqual(self.manager.quarantine("k1").status, KnowledgeStatus.QUARANTINED)
        self.assertEqual(self.manager.expire("k1").status, KnowledgeStatus.EXPIRED)

    def test_invalid_confidence_fails_closed(self):
        with self.assertRaises(ValueError):
            self.manager.register(TrustedKnowledge("k1", "lesson", 1.1))


if __name__ == "__main__":
    unittest.main()
