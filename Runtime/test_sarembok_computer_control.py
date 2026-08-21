import unittest

from sarembok_computer_control import ComputerPolicy, SarembokComputerControl


class ComputerControlTests(unittest.TestCase):
    def test_system_inspection(self):
        control = SarembokComputerControl()
        result = control.inspect_system()
        self.assertIn("platform", result)

    def test_file_read_requires_permission(self):
        control = SarembokComputerControl()
        with self.assertRaises(PermissionError):
            control.read_file("example.txt")

    def test_file_access_is_root_scoped(self):
        control = SarembokComputerControl(
            ComputerPolicy(allow_file_read=True, allowed_roots=("/tmp/sarembok-test",))
        )
        with self.assertRaises(PermissionError):
            control.read_file("/etc/hosts")

    def test_command_requires_allowlist(self):
        control = SarembokComputerControl(
            ComputerPolicy(allow_command_execution=True, allowed_commands=("python",))
        )
        with self.assertRaises(PermissionError):
            control.execute_command(["sh", "-c", "echo unsafe"])


if __name__ == "__main__":
    unittest.main()
