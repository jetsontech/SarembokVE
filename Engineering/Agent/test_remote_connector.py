import unittest

from remote_connector import RemoteResult, RemoteServer, RemoteTerminalTool


class FakeTransport:
    def __init__(self):
        self.calls = []

    def run(self, command, *, timeout_seconds):
        self.calls.append((command, timeout_seconds))
        return RemoteResult(command, 0, "ok", "")


class RemoteConnectorTests(unittest.TestCase):
    def test_dry_run_does_not_connect(self):
        transport = FakeTransport()
        tool = RemoteTerminalTool(transport, allowed_commands=("git status",))
        result = tool.invoke({"command": "git status"}, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(transport.calls, [])

    def test_allowlisted_command_uses_transport(self):
        transport = FakeTransport()
        tool = RemoteTerminalTool(transport, allowed_commands=("git status",))
        result = tool.invoke({"command": "git status", "timeout_seconds": 5})
        self.assertTrue(result["ok"])
        self.assertEqual(transport.calls, [("git status", 5.0)])

    def test_unallowlisted_command_is_denied(self):
        transport = FakeTransport()
        tool = RemoteTerminalTool(transport, allowed_commands=("git status",))
        with self.assertRaises(PermissionError):
            tool.invoke({"command": "rm -rf /"})

    def test_server_configuration_is_explicit(self):
        server = RemoteServer("vps", "15.204.173.205", "ubuntu")
        self.assertEqual(server.port, 22)
        self.assertIsNone(server.identity_file)


if __name__ == "__main__":
    unittest.main()

