import unittest

from public_session import COOKIE_NAME, cookie_header, extract_cookie, issue, validate


class PublicSessionTests(unittest.TestCase):
    def test_issue_and_validate(self):
        token = issue("master-secret", now=1000)
        self.assertTrue(validate(token, "master-secret", now=1000))
        self.assertTrue(validate(token, "master-secret", now=1000 + 3600))
        self.assertFalse(validate(token, "wrong-secret", now=1000))

    def test_expiry_and_future_skew(self):
        token = issue("master-secret", now=1000)
        self.assertFalse(validate(token, "master-secret", now=1000 + 86401))
        future = issue("master-secret", now=1100)
        self.assertFalse(validate(future, "master-secret", now=1000))

    def test_cookie_round_trip(self):
        token = issue("master-secret", now=1000)
        header = cookie_header(token)
        self.assertIn(COOKIE_NAME + "=", header)
        self.assertEqual(extract_cookie(header), token)


if __name__ == "__main__":
    unittest.main()
