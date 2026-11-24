import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
import os
import fcntl
import subprocess
import sys
import time
from types import SimpleNamespace
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


class CrashFenceTests(unittest.TestCase):
    def test_child_inherits_lock_only_inside_operation(self):
        with patch.object(m.subprocess, "run") as run:
            m.run("/usr/bin/true")
            self.assertEqual(run.call_args.kwargs["pass_fds"], ())
            with patch.object(m, "_mutation_fd", 42):
                m.run("/usr/bin/true")
                self.assertEqual(run.call_args.kwargs["pass_fds"], (42,))

    def test_fence_refuses_partial_or_orphan_record(self):
        directory = SimpleNamespace(st_mode=0o40700, st_uid=0)
        for marker in (m.WITHDRAW_MARKER, m.WITHDRAW_MARKER.with_name("withdrawal-result.json"),
                       m.REACTIVATE_MARKER, m.REACTIVATE_RESULT):
            def lstat(path):
                if path == m.EXT_DIRECTORY:
                    return directory
                if path == marker:
                    return SimpleNamespace()
                raise FileNotFoundError(path)
            with patch.object(m, "secure_parent"), patch.object(Path, "lstat", lstat):
                with self.assertRaises(m.ReductionRecovery) as error:
                    m.check_recovery_fence()
                self.assertEqual(str(error.exception), "RECOVERY_REQUIRED")

    def test_fence_absent_and_unsafe_directory(self):
        with patch.object(m, "secure_parent"), patch.object(Path, "lstat", side_effect=FileNotFoundError):
            m.check_recovery_fence()
        with patch.object(m, "secure_parent"), patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=0o120777, st_uid=0)):
            with self.assertRaises(m.ReductionRecovery):
                m.check_recovery_fence()

    def test_fence_io_error_does_not_allow_mutation(self):
        with patch.object(m, "secure_parent"), patch.object(Path, "lstat", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                m.check_recovery_fence()

    def test_every_mutating_entrypoint_uses_fenced_lock(self):
        for args, name in ((["add","16"],"allocate"),(["add-authorized","16"],"allocate"),
                           (["persist-authorized"],"persist_authorized"),(["expand-authorized","24"],"expand_authorized"),
                           (["withdraw-authorized","16"],"withdraw_authorized")):
            with patch.object(m,"mutation_lock",side_effect=m.ReductionRecovery("RECOVERY_REQUIRED")), patch.object(m,name) as mutation:
                self.assertEqual(m.main(args),3)
                mutation.assert_not_called()

    def test_real_child_lock_survives_parent_sigkill(self):
        # Unprivileged Linux process fixture. No swap or systemd commands.
        # The driver uses the production run() function and the same flock
        # description; the child holds it until the fixture releases it.
        driver = """import importlib.machinery, importlib.util, os, fcntl, sys
loader=importlib.machinery.SourceFileLoader('helper',sys.argv[1])
spec=importlib.util.spec_from_loader(loader.name,loader)
m=importlib.util.module_from_spec(spec); loader.exec_module(m)
fd=os.open(sys.argv[2],os.O_RDWR|os.O_CREAT,0o600)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
m._mutation_fd=fd
m.run(sys.executable,'-c',sys.argv[3],sys.argv[4],sys.argv[5])
"""
        child = """import pathlib,sys,time
ready,release=map(pathlib.Path,sys.argv[1:])
ready.write_text('ready')
deadline=time.monotonic()+10
while not release.exists() and time.monotonic()<deadline:
    time.sleep(.02)
"""
        with tempfile.TemporaryDirectory() as tmp:
            lock,ready,release=(Path(tmp)/name for name in ("lock","ready","release"))
            parent=subprocess.Popen([sys.executable,"-c",driver,str(path),str(lock),child,str(ready),str(release)],
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            contender=None
            try:
                deadline=time.monotonic()+5
                while not ready.exists() and time.monotonic()<deadline and parent.poll() is None:
                    time.sleep(.02)
                self.assertTrue(ready.exists(),"fixture child never started")
                parent.kill()
                parent.wait(timeout=5)
                contender=os.open(lock,os.O_RDWR)
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)
                release.touch()
                deadline=time.monotonic()+5
                while True:
                    try:
                        fcntl.flock(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic()>=deadline:
                            self.fail("lock not released after fixture child exit")
                        time.sleep(.02)
            finally:
                release.touch()
                if parent.poll() is None:
                    parent.kill()
                    parent.wait(timeout=5)
                if contender is not None:
                    os.close(contender)


class RecoveryInspectionTests(unittest.TestCase):
    def fixture(self):
        identity = [(1,2,0),(1,3,16*m.GIB),(1,4,0),(1,5,8*m.GIB)]
        intent = {"version":1,"state":"PREPARED","targetGiB":16,"timeNs":100,
                  "identity":[list(row) for row in identity],
                  "evidence":{"targetGiB":16,"baseSizeKiB":16777212,
                              "extensionSizeKiB":8388604,"extensionUsedKiB":0}}
        outcome = {"version":1,"state":"VERIFIED","targetGiB":16,"timeNs":101,
                   "sizeKiB":16777212,"basePriority":10,"extensionActive":False,"fileRetained":True}
        before = ReductionTests().sample()
        after = ReductionTests().sample()
        del after["rows"][str(m.EXT_FILE)]
        return identity,intent,outcome,before,after

    def test_recorded_verified_is_observation_not_authority(self):
        identity,intent,outcome,before,after = self.fixture()
        result = m.classify_recovery(intent,outcome,identity,after)
        self.assertEqual(result["code"],"RECORDED_VERIFIED_INACTIVE")
        self.assertFalse(result["mutationAllowed"])
        self.assertFalse(result["recordCleared"])
        self.assertEqual(m.classify_recovery(intent,outcome,identity,before)["code"],"RESULT_CONTRADICTS_KERNEL")

    def test_missing_intent_or_result_never_invents_success(self):
        identity,intent,outcome,before,after = self.fixture()
        for i,o,s,code in ((None,outcome,after,"ORPHAN_RESULT"),(None,None,after,"RETAINED_UNJOURNALED"),
                           (intent,None,before,"INTENT_ONLY_ACTIVE"),(intent,None,after,"INTENT_ONLY_INACTIVE")):
            self.assertEqual(m.classify_recovery(i,o,identity,s)["code"],code)

    def test_not_started_result(self):
        identity,intent,outcome,before,after = self.fixture()
        stopped = {"state":"NOT_STARTED","code":"EXTENSION_OCCUPIED"}
        self.assertEqual(m.classify_recovery(intent,stopped,identity,before)["code"],"NOT_STARTED_ACTIVE")
        self.assertEqual(m.classify_recovery(intent,stopped,identity,after)["code"],"RESULT_CONTRADICTS_KERNEL")

    def test_invalid_identity_and_records(self):
        identity,intent,outcome,before,after = self.fixture()
        for i,o,code in ((dict(intent,identity=[]),outcome,"FILE_IDENTITY_MISMATCH"),
                         (dict(intent,version=True),outcome,"INVALID_INTENT"),
                         (dict(intent,evidence={}),outcome,"INVALID_INTENT"),
                         (intent,dict(outcome,sizeKiB=0),"INVALID_RESULT"),
                         (intent,dict(outcome,timeNs=99),"INVALID_RESULT"),
                         (intent,dict(outcome,extensionActive=0),"INVALID_RESULT")):
            self.assertEqual(m.classify_recovery(i,o,identity,after)["code"],code)

    def test_kernel_mismatch(self):
        identity,intent,outcome,before,after = self.fixture()
        before["rows"][str(m.EXT_FILE)]["priority"]=10
        self.assertEqual(m.classify_recovery(intent,None,identity,before)["code"],"EXTENSION_MISMATCH")
        after["rows"][str(m.SWAPFILE)]["sizeKiB"]=1
        self.assertEqual(m.classify_recovery(intent,outcome,identity,after)["code"],"BASE_MISMATCH")

    def test_nonroot_cannot_inspect(self):
        with patch.object(m.os,"geteuid",return_value=1000),patch.object(m,"mutation_lock") as lock:
            with self.assertRaises(PermissionError):
                m.inspect_recovery_authorized()
            lock.assert_not_called()

    def test_inspect_never_mutates_and_detects_changed_record(self):
        identity,intent,outcome,before,after = self.fixture()
        with patch.object(m.os,"geteuid",return_value=0),patch.object(m,"mutation_lock",return_value=nullcontext()) as lock,patch.object(m,"secure_parent"),patch.object(m.os.path,"lexists",return_value=True),patch.object(m,"extension_identity",return_value=identity),patch.object(m,"check_extension_boot_policy"),patch.object(m,"read_reduction_snapshot",return_value=after),patch.object(m,"read_protected_record",side_effect=[intent,outcome,intent,None]),patch.object(m,"durable_withdrawal_record") as write,patch("builtins.print") as output:
            m.inspect_recovery_authorized()
            lock.assert_called_once_with(inspection=True)
            write.assert_not_called()
            self.assertIn("INSPECTION_UNVERIFIED",output.call_args.args[1])

    def test_read_rejects_duplicate_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"record"
            self.assertIsNone(m.read_protected_record(p))
            p.write_text('{"state":"A","state":"B"}')
            p.chmod(0o600)
            # Simulate protected owner on an unprivileged CI runner.
            original=os.fstat
            def root_stat(fd):
                s=original(fd)
                return SimpleNamespace(st_mode=s.st_mode,st_uid=0,st_nlink=s.st_nlink,st_size=s.st_size)
            with patch.object(m.os,"fstat",side_effect=root_stat):
                with self.assertRaises(ValueError):
                    m.read_protected_record(p)
                p.write_text('{"state":"PREPARED"}')
                self.assertEqual(m.read_protected_record(p)["state"],"PREPARED")
            link=Path(tmp)/"link"
            link.symlink_to(p)
            with self.assertRaises(OSError):
                m.read_protected_record(link)

    def test_inspection_command_grammar(self):
        with patch.object(m,"inspect_recovery_authorized") as inspect:
            self.assertEqual(m.main(["inspect-recovery-authorized"]),0)
            inspect.assert_called_once_with()


class ReactivationTests(unittest.TestCase):
    def fixture(self):
        return RecoveryInspectionTests().fixture()

    def test_exact_target_and_provenance(self):
        identity,intent,outcome,before,after = self.fixture()
        plan = m.reactivation_plan(24,intent,outcome,identity,after)
        self.assertEqual(plan["targetGiB"],24)
        self.assertEqual(plan["extensionSizeKiB"],8388604)
        for target in (16,20,28,32):
            with self.assertRaises(m.ReductionBlocked):
                m.reactivation_plan(target,intent,outcome,identity,after)
        for i,o,s in ((None,None,after),(intent,None,after),(intent,outcome,before),
                      (intent,dict(outcome,sizeKiB=1),after)):
            with self.assertRaises(m.ReductionRecovery):
                m.reactivation_plan(24,i,o,identity,s)

    def test_new_receipt_requires_exact_kernel_and_predecessor(self):
        identity,intent,outcome,before,after = self.fixture()
        prepared = dict(m.reactivation_plan(24,intent,outcome,identity,after),timeNs=102)
        receipt = dict(prepared,state="VERIFIED",timeNs=103,sizeKiB=25165816,
                       basePriority=10,extensionPriority=9,extensionActive=True,fileRetained=True,temporary=True)
        self.assertEqual(m.classify_reactivation(intent,outcome,prepared,receipt,identity,before)["code"],
                         "REACTIVATION_RECORDED_VERIFIED_ACTIVE")
        self.assertEqual(m.classify_reactivation(intent,outcome,prepared,receipt,identity,after)["code"],
                         "REACTIVATION_RESULT_CONTRADICTS_KERNEL")
        self.assertEqual(m.classify_reactivation(intent,outcome,prepared,None,identity,before)["code"],
                         "REACTIVATION_INTENT_ONLY_ACTIVE")
        self.assertEqual(m.classify_reactivation(intent,outcome,None,receipt,identity,before)["code"],
                         "REACTIVATION_ORPHAN_RESULT")
        self.assertEqual(m.classify_reactivation(intent,outcome,prepared,dict(receipt,withdrawalDigest="other"),identity,before)["code"],
                         "REACTIVATION_INVALID_RESULT")
        self.assertFalse(m.classify_reactivation(intent,outcome,prepared,receipt,identity,before)["mutationAllowed"])

    def test_nonroot_refusal(self):
        with patch.object(m.os,"geteuid",return_value=1000),patch.object(m,"mutation_lock") as lock:
            with self.assertRaises(PermissionError):
                m.reactivate_authorized(24)
            lock.assert_not_called()

    def test_one_fixed_activation_and_durable_receipt(self):
        identity,intent,outcome,before,after = self.fixture()
        records = {m.WITHDRAW_MARKER:intent,m.WITHDRAW_MARKER.with_name("withdrawal-result.json"):outcome}
        def publish(path,data):
            self.assertNotIn(path,records)
            records[path]=data
        with patch.object(m.os,"geteuid",return_value=0),patch.object(m,"mutation_lock",return_value=nullcontext()) as lock,patch.object(m,"extension_identity",return_value=identity),patch.object(m,"check_extension_boot_policy"),patch.object(m,"mount_info",return_value=("/var","btrfs")),patch.object(m,"read_protected_record",side_effect=records.get),patch.object(m,"read_reduction_snapshot",side_effect=[after,after,after,before]),patch.object(m,"write_protected_record",side_effect=publish) as write,patch.object(m,"run",return_value="Total devices 1") as run:
            m.reactivate_authorized(24)
            lock.assert_called_once_with(inspection=True)
            self.assertEqual(run.call_args_list[-1].args,("/usr/sbin/swapon","--priority","9","--",str(m.EXT_FILE)))
            self.assertEqual(run.call_count,3)
            self.assertEqual(write.call_count,2)
            self.assertEqual(records[m.REACTIVATE_MARKER]["state"],"PREPARED")
            self.assertEqual(records[m.REACTIVATE_RESULT]["state"],"VERIFIED")
            self.assertEqual(records[m.WITHDRAW_MARKER],intent)
            self.assertEqual(records[m.WITHDRAW_MARKER.with_name("withdrawal-result.json")],outcome)

    def test_failed_activation_never_replays(self):
        identity,intent,outcome,before,after = self.fixture()
        records = {m.WITHDRAW_MARKER:intent,m.WITHDRAW_MARKER.with_name("withdrawal-result.json"):outcome}
        def command(*argv):
            if argv[0]=="/usr/sbin/swapon":
                raise m.subprocess.CalledProcessError(1,"swapon")
            return "Total devices 1"
        with patch.object(m.os,"geteuid",return_value=0),patch.object(m,"mutation_lock",return_value=nullcontext()),patch.object(m,"extension_identity",return_value=identity),patch.object(m,"check_extension_boot_policy"),patch.object(m,"mount_info",return_value=("/var","btrfs")),patch.object(m,"read_protected_record",side_effect=records.get),patch.object(m,"read_reduction_snapshot",return_value=after),patch.object(m,"write_protected_record",side_effect=records.__setitem__) as write,patch.object(m,"run",side_effect=command) as run:
            with self.assertRaises(m.ReductionRecovery) as error:
                m.reactivate_authorized(24)
            self.assertEqual(str(error.exception),"REACTIVATION_OUTCOME_UNKNOWN")
            self.assertNotIn(m.REACTIVATE_RESULT,records)
            write.assert_called_once()
            run.reset_mock()
            with self.assertRaises(m.ReductionRecovery) as error:
                m.reactivate_authorized(24)
            self.assertEqual(str(error.exception),"REACTIVATION_RECOVERY_REQUIRED")
            run.assert_not_called()

    def test_changed_kernel_after_intent_never_calls_swapon(self):
        identity,intent,outcome,before,after = self.fixture()
        records = {m.WITHDRAW_MARKER:intent,m.WITHDRAW_MARKER.with_name("withdrawal-result.json"):outcome}
        with patch.object(m.os,"geteuid",return_value=0),patch.object(m,"mutation_lock",return_value=nullcontext()),patch.object(m,"extension_identity",return_value=identity),patch.object(m,"check_extension_boot_policy"),patch.object(m,"mount_info",return_value=("/var","btrfs")),patch.object(m,"read_protected_record",side_effect=records.get),patch.object(m,"read_reduction_snapshot",side_effect=[after,after,before]),patch.object(m,"write_protected_record",side_effect=records.__setitem__),patch.object(m,"run",return_value="Total devices 1") as run:
            with self.assertRaises(m.ReductionRecovery):
                m.reactivate_authorized(24)
            self.assertEqual(run.call_count,2)
            self.assertIn(m.REACTIVATE_MARKER,records)
            self.assertNotIn(m.REACTIVATE_RESULT,records)

    def test_wrong_readback_retains_intent_only(self):
        identity,intent,outcome,before,after = self.fixture()
        records = {m.WITHDRAW_MARKER:intent,m.WITHDRAW_MARKER.with_name("withdrawal-result.json"):outcome}
        with patch.object(m.os,"geteuid",return_value=0),patch.object(m,"mutation_lock",return_value=nullcontext()),patch.object(m,"extension_identity",return_value=identity),patch.object(m,"check_extension_boot_policy"),patch.object(m,"mount_info",return_value=("/var","btrfs")),patch.object(m,"read_protected_record",side_effect=records.get),patch.object(m,"read_reduction_snapshot",return_value=after),patch.object(m,"write_protected_record",side_effect=records.__setitem__),patch.object(m,"run",return_value="Total devices 1"):
            with self.assertRaises(m.ReductionRecovery):
                m.reactivate_authorized(24)
            self.assertIn(m.REACTIVATE_MARKER,records)
            self.assertNotIn(m.REACTIVATE_RESULT,records)

    def test_command_grammar(self):
        with patch.object(m,"reactivate_authorized") as reactivate:
            self.assertEqual(m.main(["reactivate-authorized","24"]),0)
            reactivate.assert_called_once_with(24)
            self.assertEqual(m.main(["reactivate-authorized","0"]),1)
            reactivate.assert_called_once()

if __name__ == "__main__":
    unittest.main()
