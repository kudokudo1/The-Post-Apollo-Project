import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/post-apollo-memory-add-swap"
loader = importlib.machinery.SourceFileLoader("memory_add", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

GOOD = {"candidate": True, "maximumGiB": 64, "mountpoint": "/var"}

class SwapAddTests(unittest.TestCase):
    def test_silverblue_mount(self):
        with patch.object(m, "run", return_value='{"filesystems":[{"target":"/var","fstype":"btrfs"}]}') as run:
            self.assertEqual(m.mount_info(), ("/var", "btrfs"))
            run.assert_called_once_with("/usr/bin/findmnt", "--json", "--target", "/var/lib", "--output", "TARGET,FSTYPE")

    def test_unexpected_mount_refused(self):
        for raw in ('{"filesystems":[]}', '{"filesystems":[{"target":"/home","fstype":"btrfs"}]}'):
            with patch.object(m, "run", return_value=raw), self.assertRaises(RuntimeError):
                m.mount_info()

    def test_native_verify_is_read_only(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "active_swap", return_value={"sizeKiB": 16777212, "priority": 10}), patch.object(m, "run") as run:
            m.verify_authorized()
            run.assert_not_called()

    def test_native_verify_requires_root(self):
        with patch.object(m.os, "geteuid", return_value=1000), patch.object(m, "active_swap") as active:
            with self.assertRaises(PermissionError):
                m.verify_authorized()
            active.assert_not_called()

    def test_native_verify_inactive_refuses(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "active_swap", return_value=None):
            with self.assertRaises(RuntimeError):
                m.verify_authorized()

    def test_native_add_nonroot_refuses(self):
        with patch.object(m.os, "geteuid", return_value=1000), patch.object(m, "run") as run:
            with self.assertRaises(PermissionError):
                m.allocate(16, interactive=False)
            run.assert_not_called()

    def test_native_command_grammar(self):
        with patch.object(m, "allocate") as allocate:
            self.assertEqual(m.main(["add-authorized", "16"]), 0)
            allocate.assert_called_once_with(16, interactive=False)

    def test_persist_nonroot_refusal(self):
        with patch.object(m.os, "geteuid", return_value=1000), patch.object(m, "run") as run:
            with self.assertRaises(PermissionError):
                m.persist_authorized()
            run.assert_not_called()

    def test_persist_inactive_refusal(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "trusted_unit_directory"), patch.object(m, "trusted_swap_file"), patch.object(m, "active_swap", return_value=None), patch.object(m, "run") as run:
            with self.assertRaises(RuntimeError):
                m.persist_authorized()
            run.assert_not_called()

    def test_persist_command_grammar(self):
        with patch.object(m, "persist_authorized") as persist:
            self.assertEqual(m.main(["persist-authorized"]), 0)
            persist.assert_called_once_with()

    def test_unit_name_and_policy(self):
        self.assertEqual(m.UNIT_NAME, r"var-lib-post\x2dapollo\x2dmemory\x2dswap-swapfile.swap")
        self.assertIn("Priority=10\n", m.UNIT_CONTENT)
        self.assertIn("WantedBy=swap.target\n", m.UNIT_CONTENT)
        self.assertIn("What=" + str(m.SWAPFILE), m.UNIT_CONTENT)

    def test_size_choices(self):
        for size in range(4, 65, 4):
            self.assertEqual(m.parse_size(str(size)), size)

    def test_invalid_sizes(self):
        for value in ("0", "3", "7", "65", "128", "04", "-4", "4G", "4;id", "4\n", " 4"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.parse_size(value)

    def test_existing_and_insufficient_refuse(self):
        for candidate in ({"candidate": False, "maximumGiB": 64},
                          {"candidate": True, "maximumGiB": 12}):
            with self.assertRaises(RuntimeError):
                m.validate_request(16, candidate)

    def test_nonroot_never_writes(self):
        with patch.object(m.os, "geteuid", return_value=1000), patch.object(m, "run") as run:
            with self.assertRaises(PermissionError):
                m.allocate(16)
            run.assert_not_called()

    def test_noninteractive_refuses(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m.sys.stdin, "isatty", return_value=False), patch.object(m, "run") as run:
            with self.assertRaises(RuntimeError):
                m.allocate(16)
            run.assert_not_called()

    def test_cancel_never_writes(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m.sys.stdin, "isatty", return_value=True), patch.object(m, "status", return_value=GOOD), patch("builtins.input", return_value="cancel"), patch.object(m, "run") as run:
            with self.assertRaises(RuntimeError):
                m.allocate(16)
            run.assert_not_called()

    def test_recheck_refuses_changed_state(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m.sys.stdin, "isatty", return_value=True), patch.object(m, "status", side_effect=[GOOD, {"candidate": False, "maximumGiB": 64}]), patch("builtins.input", return_value="ADD 16"), patch.object(m, "run") as run:
            with self.assertRaises(RuntimeError):
                m.allocate(16)
            run.assert_not_called()

    def test_multidevice_refusal(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m.sys.stdin, "isatty", return_value=True), patch.object(m, "status", return_value=GOOD), patch("builtins.input", return_value="ADD 16"), patch.object(m, "run", return_value="Total devices 2") as run:
            with self.assertRaises(RuntimeError):
                m.allocate(16)
            run.assert_called_once_with("/usr/bin/btrfs", "filesystem", "show", "--raw", "/var")

    def test_positive_exact_argv_and_readback(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m.sys.stdin, "isatty", return_value=True), patch.object(m, "status", return_value=GOOD), patch("builtins.input", return_value="ADD 16"), patch.object(m, "run", return_value="Total devices 1") as run, patch.object(m.os, "umask"), patch.object(Path, "chmod"), patch.object(m, "active_swap", return_value={"sizeKiB": 16 * 1024**2 - 4, "priority": 10}):
            m.allocate(16)
            self.assertEqual(run.call_count, 5)
            self.assertEqual(run.call_args_list[0].args, ("/usr/bin/btrfs", "filesystem", "show", "--raw", "/var"))
            self.assertEqual(run.call_args_list[-1].args, ("/usr/sbin/swapon", "--priority", "10", "--", str(m.SWAPFILE)))

    def test_failed_readback_not_success(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m.sys.stdin, "isatty", return_value=True), patch.object(m, "status", return_value=GOOD), patch("builtins.input", return_value="ADD 16"), patch.object(m, "run", return_value="Total devices 1"), patch.object(m.os, "umask"), patch.object(Path, "chmod"), patch.object(m, "active_swap", return_value=None):
            with self.assertRaises(RuntimeError):
                m.allocate(16)

if __name__ == "__main__":
    unittest.main()
