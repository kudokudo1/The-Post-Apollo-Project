import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from contextlib import nullcontext
import tempfile
from unittest.mock import mock_open
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
        with patch.object(m, "mutation_lock", return_value=nullcontext()), patch.object(m, "allocate") as allocate:
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
        with patch.object(m, "mutation_lock", return_value=nullcontext()), patch.object(m, "persist_authorized") as persist:
            self.assertEqual(m.main(["persist-authorized"]), 0)
            persist.assert_called_once_with()

    def test_unit_name_and_policy(self):
        self.assertEqual(m.UNIT_NAME, r"var-lib-post\x2dapollo\x2dmemory\x2dswap-swapfile.swap")
        self.assertIn("Priority=10\n", m.UNIT_CONTENT)
        self.assertIn("WantedBy=swap.target\n", m.UNIT_CONTENT)
        self.assertIn("What=" + str(m.SWAPFILE), m.UNIT_CONTENT)

    def test_persist_publishes_only_boot_policy(self):
        observed = {"sizeKiB": 16777212, "priority": 10}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            unit = directory / m.UNIT_NAME
            def command(*argv):
                if argv[0] == "/usr/bin/systemd-escape":
                    return m.UNIT_NAME
                return ""
            with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "trusted_unit_directory"), patch.object(m, "trusted_swap_file"), patch.object(m, "active_swap", return_value=observed), patch.object(m, "mount_info", return_value=("/var", "btrfs")), patch.object(m, "persistence_state", side_effect=["off", "enabled"]), patch.object(m, "UNIT_DIR", directory), patch.object(m, "UNIT_PATH", unit), patch.object(m, "run", side_effect=command) as run, patch("builtins.open", mock_open(read_data="# empty\\n")):
                m.persist_authorized()
            self.assertEqual(unit.read_text(), m.UNIT_CONTENT)
            self.assertEqual(run.call_args_list[-1].args, ("/usr/bin/systemctl", "enable", m.UNIT_NAME))
            self.assertEqual(run.call_count, 3)
            self.assertEqual(unit.stat().st_mode & 0o777, 0o644)

    def test_persist_existing_fstab_refuses(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "trusted_unit_directory"), patch.object(m, "trusted_swap_file"), patch.object(m, "active_swap", return_value={"sizeKiB": 16777212, "priority": 10}), patch.object(m, "mount_info", return_value=("/var", "btrfs")), patch.object(m, "run", return_value=m.UNIT_NAME) as run, patch("builtins.open", mock_open(read_data=str(m.SWAPFILE) + " none swap defaults 0 0")):
            with self.assertRaises(RuntimeError):
                m.persist_authorized()
            self.assertEqual(run.call_count, 1)

    def test_expansion_delta(self):
        base = {"sizeKiB": 16777212, "priority": 10}
        state = {"expansionCandidate": True, "active": base, "maximumGiB": 32}
        self.assertEqual(m.expansion_delta(24, state), 8)
        for target in (16, 12, 64):
            with self.assertRaises(RuntimeError):
                m.expansion_delta(target, state)
        with self.assertRaises(RuntimeError):
            m.expansion_delta(24, dict(state, expansionCandidate=False))

    def test_expand_nonroot_refuses(self):
        with patch.object(m.os, "geteuid", return_value=1000), patch.object(m, "run") as run:
            with self.assertRaises(PermissionError):
                m.expand_authorized(24)
            run.assert_not_called()

    def test_expand_preserves_base_exact_commands(self):
        base = {"sizeKiB": 16777212, "priority": 10}
        extra = {"sizeKiB": 8388604, "priority": 9}
        state = {"expansionCandidate": True, "active": base, "maximumGiB": 32, "mountpoint": "/var"}
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "trusted_swap_file"), patch.object(m, "status", return_value=state), patch.object(m, "run", return_value="Total devices 1") as run, patch.object(m.os, "umask"), patch.object(Path, "chmod"), patch.object(m, "active_swap", side_effect=[base, extra]):
            m.expand_authorized(24)
            self.assertEqual(run.call_count, 5)
            self.assertEqual(run.call_args_list[-1].args, ("/usr/sbin/swapon", "--priority", "9", "--", str(m.EXT_FILE)))
            self.assertNotIn(str(m.SWAPFILE), [x for call in run.call_args_list for x in call.args])

    def test_expand_changed_base_refuses(self):
        base = {"sizeKiB": 16777212, "priority": 10}
        state = {"expansionCandidate": True, "active": base, "maximumGiB": 32, "mountpoint": "/var"}
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "secure_parent"), patch.object(m, "trusted_swap_file"), patch.object(m, "status", side_effect=[state, dict(state, expansionCandidate=False)]), patch.object(m, "run", return_value="Total devices 1") as run:
            with self.assertRaises(RuntimeError):
                m.expand_authorized(24)
            self.assertEqual(run.call_count, 1)

    def test_expand_command_grammar(self):
        with patch.object(m, "mutation_lock", return_value=nullcontext()), patch.object(m, "expand_authorized") as expand:
            self.assertEqual(m.main(["expand-authorized", "24"]), 0)
            expand.assert_called_once_with(24)

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


class ReductionTests(unittest.TestCase):
    def sample(self, used=0, available=9*1024**2, base_used=0, some=0, full=0):
        return {"rows": {
            str(m.SWAPFILE): {"kind":"file", "sizeKiB":16777212, "usedKiB":base_used, "priority":10},
            str(m.EXT_FILE): {"kind":"file", "sizeKiB":8388604, "usedKiB":used, "priority":9}},
            "totalKiB":32*1024**2, "availableKiB":available, "someAvg10":some, "fullAvg10":full}

    def test_advisory_ready_and_blockers(self):
        self.assertEqual(m.reduction_plan(16, self.sample())["extensionUsedKiB"], 0)
        for sample, code in ((self.sample(used=1), "EXTENSION_OCCUPIED"),
                             (self.sample(available=7*1024**2), "RAM_HEADROOM"),
                             (self.sample(base_used=15*1024**2), "BASE_HEADROOM"),
                             (self.sample(some=1.1), "MEMORY_PRESSURE"),
                             (self.sample(full=0.01), "MEMORY_PRESSURE")):
            with self.subTest(code=code), self.assertRaises(m.ReductionBlocked) as error:
                m.reduction_plan(16, sample)
            self.assertEqual(error.exception.code, code)

    def test_target_must_equal_base(self):
        for target in (0, 8, 12, 20, 24):
            with self.assertRaises(m.ReductionBlocked) as error:
                m.reduction_plan(target, self.sample())
            self.assertEqual(error.exception.code, "UNSUPPORTED_TARGET")

    def test_missing_observation_never_ready(self):
        with patch.object(m, "read_reduction_snapshot", side_effect=ValueError("bad read")):
            self.assertEqual(m.reduction_preflight(16)["code"], "OBSERVATION_UNAVAILABLE")

    def test_nonroot_no_mutation(self):
        with patch.object(m.os, "geteuid", return_value=1000), patch.object(m, "run") as run:
            with self.assertRaises(PermissionError):
                m.withdraw_authorized(16)
            run.assert_not_called()

    def test_withdraw_exact_argv_retains_files(self):
        before = self.sample()
        after = self.sample()
        del after["rows"][str(m.EXT_FILE)]
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "extension_identity", return_value=[(1,2,3)]), patch.object(m.os.path, "lexists", return_value=False), patch.object(m, "check_extension_boot_policy"), patch.object(m.time, "sleep"), patch.object(m, "read_reduction_snapshot", side_effect=[before,before,before,after]), patch.object(m, "durable_withdrawal_record") as record, patch.object(m, "run") as run:
            m.withdraw_authorized(16)
            run.assert_called_once_with("/usr/sbin/swapoff", "--", str(m.EXT_FILE))
            self.assertEqual(record.call_args_list[0].args[0]["state"], "PREPARED")
            self.assertEqual(record.call_args_list[1].args[0]["state"], "VERIFIED")
            self.assertTrue(record.call_args_list[1].args[0]["fileRetained"])

    def test_final_spike_blocks_without_swapoff(self):
        before = self.sample()
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "extension_identity", return_value=[(1,2,3)]), patch.object(m.os.path, "lexists", return_value=False), patch.object(m, "check_extension_boot_policy"), patch.object(m.time, "sleep"), patch.object(m, "read_reduction_snapshot", side_effect=[before,before,self.sample(used=1)]), patch.object(m, "durable_withdrawal_record") as record, patch.object(m, "run") as run:
            with self.assertRaises(m.ReductionRecovery) as error:
                m.withdraw_authorized(16)
            self.assertEqual(str(error.exception), "NOT_STARTED_EXTENSION_OCCUPIED")
            run.assert_not_called()
            self.assertEqual(record.call_args_list[1].args[0]["state"], "NOT_STARTED")

    def test_failed_kernel_command_preserves_prepared_record(self):
        before = self.sample()
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "extension_identity", return_value=[(1,2,3)]), patch.object(m.os.path, "lexists", return_value=False), patch.object(m, "check_extension_boot_policy"), patch.object(m.time, "sleep"), patch.object(m, "read_reduction_snapshot", return_value=before), patch.object(m, "durable_withdrawal_record") as record, patch.object(m, "run", side_effect=m.subprocess.CalledProcessError(1,"swapoff")):
            with self.assertRaises(m.ReductionRecovery) as error:
                m.withdraw_authorized(16)
            self.assertEqual(str(error.exception), "WITHDRAWAL_OUTCOME_UNKNOWN")
            record.assert_called_once()
            self.assertEqual(record.call_args.args[0]["state"], "PREPARED")

    def test_prior_intent_blocks_replay(self):
        with patch.object(m.os, "geteuid", return_value=0), patch.object(m, "extension_identity", return_value=[]), patch.object(m.os.path, "lexists", return_value=True), patch.object(m, "run") as run:
            with self.assertRaises(m.ReductionRecovery) as error:
                m.withdraw_authorized(16)
            self.assertEqual(str(error.exception), "RECOVERY_REQUIRED")
            run.assert_not_called()

    def test_marker_is_exclusive_and_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            marker = directory / "withdrawal.json"
            with patch.object(m, "EXT_DIRECTORY", directory), patch.object(m, "WITHDRAW_MARKER", marker):
                m.durable_withdrawal_record({"state":"PREPARED"}, initial=True)
                with self.assertRaises(FileExistsError):
                    m.durable_withdrawal_record({"state":"OTHER"}, initial=True)
                self.assertEqual(m.json.loads(marker.read_text())["state"], "PREPARED")

    def test_withdraw_command_grammar(self):
        with patch.object(m, "mutation_lock", return_value=nullcontext()), patch.object(m, "withdraw_authorized") as withdraw:
            self.assertEqual(m.main(["withdraw-authorized", "16"]), 0)
            withdraw.assert_called_once_with(16)

if __name__ == "__main__":
    unittest.main()
