from dataclasses import replace
from pathlib import Path
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import runtime_membership_i6 as M


class ParserTests(unittest.TestCase):
    def test_pid_bounds_before_io(self):
        with patch.object(M.os, "open") as op:
            for pids in ((), (1,1), (True,), (-1,), (2**31,), [1], tuple(range(1,18))):
                with self.assertRaises(M.MembershipRefusal):
                    M.correlate("/group",pids)
            op.assert_not_called()

    def test_root_refused_before_io(self):
        with patch.object(M.os,"open") as op:
            with self.assertRaises(M.group.CgroupRefusal):
                M.correlate("/",(1,))
            op.assert_not_called()

    def test_membership_components(self):
        self.assertEqual(M._membership(b"0::/group/child\n"),("group","child"))
        self.assertEqual(M._membership(b"0::/\n"),())

    def test_invalid_membership(self):
        for raw in (b"", b"0::/group\n1:name=/other\n", b"0::/group/../x",
                    b"0::relative", b"0::/bad\xff"):
            with self.assertRaises(M.MembershipRefusal):
                M._membership(raw)

    def test_uid_exact_fields(self):
        self.assertEqual(M._uids(b"Name: private\nUid:\t1000\t1000\t1000\t1000\n"),(1000,)*4)

    def test_bad_uid_fields(self):
        for raw in (b"", b"Uid: 1 2 3", b"Uid: -1 1 1 1",
                    b"Uid: 4294967296 1 1 1", b"Uid: 1 1 1 1\nUid: 1 1 1 1"):
            with self.assertRaises(M.MembershipRefusal):
                M._uids(raw)

    def test_fixed_proc_field_allowlist(self):
        with patch.object(M.os,"open") as op:
            for name in ("cmdline","environ","../status","exe"):
                with self.assertRaises(M.MembershipRefusal):
                    M._read(1,name)
            op.assert_not_called()


class MemberTests(unittest.TestCase):
    def setUp(self):
        self.stat = M.proc.ProcessStat(100,20,10,2)
        self.member = M.Member(100,(1,2),(3,4),(1000,)*4,("group","child"))

    def check(self, membership=("group","child"), uids=(1000,)*4,
              stats=None, exe=None, memberships=None):
        with patch.object(M,"_read",return_value=b""), \
             patch.object(M.proc,"_parse_stat",side_effect=stats or [self.stat,self.stat]), \
             patch.object(M,"_uids",return_value=uids), \
             patch.object(M,"_membership",side_effect=memberships or [membership,membership]), \
             patch.object(M,"_exe_reference",side_effect=exe or [(3,4),(3,4)]), \
             patch.object(M.group,"_identity",return_value=(1,2)):
            return M._member(1,123,("group",),1000)

    def test_descendant_member(self):
        self.assertEqual(self.check(),self.member)

    def test_component_prefix_not_string_prefix(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_OUTSIDE_SELECTED_GROUP"):
            self.check(membership=("group-other",))

    def test_other_owner_refused(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_OWNER_SCOPE_MISMATCH"):
            self.check(uids=(1000,1001,1000,1000))

    def test_start_or_tick_change_refused(self):
        for stat in (replace(self.stat,start_ticks=101),replace(self.stat,user_ticks=19)):
            with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_REFERENCE_CHANGED"):
                self.check(stats=[self.stat,stat])

    def test_executable_replacement_refused(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_REFERENCE_CHANGED"):
            self.check(exe=[(3,4),(3,5)])

    def test_migration_refused(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_REFERENCE_CHANGED"):
            self.check(memberships=[("group","child"),("group","other")])


class CorrelationTests(unittest.TestCase):
    def fixture(self, first=None, second=None, boot=None, identity=None):
        a = M.Member(10,(1,2),(3,4),(1000,)*4,("group",))
        b = M.Member(11,(1,3),(3,4),(1000,)*4,("group","child"))
        with patch.object(M,"_boot",side_effect=boot or [b"same",b"same"]), \
             patch.object(M.group,"_mount",return_value=(b"1",b"0:1")), \
             patch.object(M.group,"_open_group",side_effect=[10,20]), \
             patch.object(M.group,"_identity",side_effect=identity or [
                     (1,10),(1,2),(1,2),(1,3),(1,3),(1,10)]), \
             patch.object(M.group,"_read_counter",return_value=b"1024\n"), \
             patch.object(M.os,"open",side_effect=[11,12,21,22]), \
             patch.object(M.os,"close") as close, \
             patch.object(M,"_member",side_effect=(first or [a,b])+(second or [a,b])):
            try:
                return M.correlate("/group",(123,124))
            finally:
                self.assertIn(10,[call.args[0] for call in close.call_args_list])
                self.assertIn(11,[call.args[0] for call in close.call_args_list])

    def test_reference_counts_and_privacy(self):
        r = self.fixture()
        self.assertEqual(r["selected_process_count"],2)
        self.assertEqual(r["direct_member_count"],1)
        self.assertEqual(r["descendant_member_count"],1)
        self.assertEqual(r["distinct_executable_reference_count"],1)
        for key in ("runtime_release_authenticated","model_binding_verified",
                    "complete_group_membership_verified","continuous_membership_verified",
                    "memory_attributed_to_model","resource_reserved","production_authority",
                    "generation_requested","permission_granted"):
            self.assertFalse(r[key])
        self.assertNotIn("group/child",str(r))
        self.assertNotIn("123",str(r))

    def test_observed_reference_change_discards_result(self):
        a = M.Member(10,(1,2),(3,4),(1000,)*4,("group",))
        b = replace(a,start_ticks=11)
        with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_REFERENCE_CHANGED"):
            self.fixture(first=[a,b],second=[b,a])

    def test_boot_change_refused(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"HOST_REFERENCE_CHANGED"):
            self.fixture(boot=[b"a",b"b"])

    def test_path_replacement_refused(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"PROCESS_REFERENCE_CHANGED"):
            self.fixture(identity=[(1,10),(1,99),(1,2)])

    def test_cgroup_replacement_refused(self):
        with self.assertRaisesRegex(M.MembershipRefusal,"CGROUP_REFERENCE_CHANGED"):
            self.fixture(identity=[(1,10),(1,2),(1,2),(1,3),(1,3),(1,99)])

    def test_cli_no_raw_diagnostics(self):
        with patch.object(M,"correlate",side_effect=M.MembershipRefusal("LOCAL_MEMBERSHIP_UNAVAILABLE")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(M.main(["correlate","--cgroup","/private","--pid","123"]),2)
        self.assertNotIn("/private",out.getvalue())
        self.assertEqual(json.loads(out.getvalue())["status"],"UNAVAILABLE")

    @unittest.skipUnless(sys.platform=="linux","Linux only")
    def test_real_self_membership_and_executable_metadata(self):
        fd = os.open("/proc/"+str(os.getpid()),M._DIR_FLAGS)
        try:
            selected = M._membership(M._read(fd,"cgroup"))
            r = M._member(fd,os.getpid(),selected,os.geteuid())
            self.assertEqual(r.membership,selected)
            self.assertGreater(r.start_ticks,0)
            self.assertGreater(r.executable_identity[1],0)
        finally:
            os.close(fd)

    @unittest.skipUnless(sys.platform=="linux","Linux only")
    def test_real_child_same_group(self):
        child = subprocess.Popen([sys.executable,"-I","-B","-c",
                                  "import sys; sys.stdin.read()"],stdin=subprocess.PIPE)
        try:
            fd = os.open("/proc/"+str(child.pid),M._DIR_FLAGS)
            try:
                selected = M._membership(M._read(fd,"cgroup"))
                # Child may still be completing exec; test membership only.
                self.assertEqual(selected,M._membership(Path("/proc/self/cgroup").read_bytes()))
            finally:
                os.close(fd)
        finally:
            child.stdin.close()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)


if __name__=="__main__":
    unittest.main()
