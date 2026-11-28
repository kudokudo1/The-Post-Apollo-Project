#!/usr/bin/env python3
"""K9a tests: real disposable capture/refusal; deterministic mutation contracts."""
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

SOURCE = pathlib.Path(__file__).resolve().parents[2] / "services" / "kill"
sys.path.insert(0, str(SOURCE))
import priority_control as p
from resource_capability_probe import birth_identity


class PriorityControlTest(unittest.TestCase):
    def request(self, **overrides):
        return dict(dict(serial=1, pid=123, startTicks=456, comm="child",
                         operation="apply", original=0, expected=0, target=5,
                         expectedSoft=20), **overrides)

    def simulated(self, snapshots, req=None, write_error=None):
        with mock.patch.object(p.os, "pidfd_open", return_value=41), \
             mock.patch.object(p.os, "close") as close, \
             mock.patch.object(p.select, "poll"), \
             mock.patch.object(p, "snapshot", side_effect=snapshots), \
             mock.patch.object(p.os, "setpriority", side_effect=write_error) as write:
            reply = p.execute(req or self.request())
            close.assert_called_once_with(41)
            return reply, write.call_args_list

    def test_range(self):
        self.assertTrue(p.reversible_range(0, 0, 5, 20))
        self.assertTrue(p.reversible_range(19, 19, 18, 2))
        self.assertFalse(p.reversible_range(0, 0, 5, 0))
        self.assertFalse(p.reversible_range(0, 5, 0, 19))
        self.assertFalse(p.reversible_range(0, 0, -1, 20))
        self.assertFalse(p.reversible_range(True, 0, 1, 40))
        self.assertFalse(p.reversible_range(0, 0, 20, 40))

    def test_apply_and_restore(self):
        before = dict(nice=0, soft=20, hard=20, scheduler=0, uid=1000)
        after = dict(before, nice=5)
        applied, writes = self.simulated([before, before, after])
        self.assertEqual(applied["state"], "applied")
        self.assertEqual(applied["original"], 0)
        self.assertEqual(writes, [mock.call(os.PRIO_PROCESS, 123, 5)])
        restored, writes = self.simulated([after, after, before],
            self.request(operation="restore", expected=5, target=0))
        self.assertEqual(restored["state"], "restored")
        self.assertEqual(writes, [mock.call(os.PRIO_PROCESS, 123, 0)])

    def test_refusal_and_unknown(self):
        before = dict(nice=0, soft=20, hard=20, scheduler=0, uid=1000)
        drift = dict(before, nice=1)
        for snapshots, req in [
            ([before], self.request(target=-1)),
            ([dict(before, soft=0)], self.request(expectedSoft=0)),
            ([drift], self.request()),
            ([before, drift], self.request()),
            ([before], self.request(operation="restore", target=5)),
            ([before], self.request(expectedSoft=21)),
        ]:
            with self.subTest(req=req, snapshots=snapshots):
                reply, writes = self.simulated(snapshots, req)
                self.assertEqual(reply["state"], "refused")
                self.assertFalse(reply["attempted"])
                self.assertEqual(writes, [])
        reply, writes = self.simulated([before, before, drift])
        self.assertEqual(reply["state"], "unknown")
        self.assertTrue(reply["attempted"])
        self.assertEqual(len(writes), 1)
        reply, writes = self.simulated([before, before], write_error=PermissionError("denied"))
        self.assertEqual(reply["state"], "unknown")
        self.assertEqual(len(writes), 1)

    def test_invalid_and_noop(self):
        with mock.patch.object(p.os, "pidfd_open") as openfd:
            self.assertEqual(p.execute(self.request(pid=True))["state"], "refused")
            self.assertEqual(p.execute(self.request(operation="bad"))["state"], "refused")
            openfd.assert_not_called()
        before = dict(nice=0, soft=0, hard=0, scheduler=0, uid=1000)
        reply, writes = self.simulated([before], self.request(target=0, expectedSoft=0))
        self.assertEqual(reply["state"], "unchanged")
        self.assertEqual(writes, [])

    def test_disposable_real_child(self):
        child = subprocess.Popen([sys.executable, "-u", "-c",
            "import time; print('ready'); time.sleep(30)"], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            state, identity = birth_identity(child.pid)
            self.assertEqual(state, "observed")
            name, born = identity
            req = self.request(pid=child.pid, startTicks=born, comm=name, operation="capture")
            def invoke(request):
                cp = subprocess.run([sys.executable, "-B", str(SOURCE / "priority_control.py"),
                    "--request", json.dumps(request)], capture_output=True, text=True, timeout=5, check=True)
                return json.loads(cp.stdout)
            initial = os.getpriority(os.PRIO_PROCESS, child.pid)
            captured = invoke(req)
            if os.geteuid() == 0 or os.getuid() != os.geteuid():
                self.assertEqual(captured["state"], "refused")
                self.assertEqual(os.getpriority(os.PRIO_PROCESS, child.pid), initial)
                return
            self.assertEqual(captured["state"], "observed", captured)
            self.assertEqual(captured["before"]["nice"], initial)
            self.assertEqual(invoke(dict(req, startTicks=born+1))["state"], "refused")
            soft = captured["before"]["soft"]
            apply = dict(req, operation="apply", original=initial, expected=initial,
                         target=initial, expectedSoft=soft)
            self.assertEqual(invoke(apply)["state"], "unchanged")
            candidate = next((n for n in (initial+1, initial-1)
                              if p.reversible_range(initial, initial, n, soft)), None)
            if candidate is not None:
                applied = invoke(dict(apply, target=candidate))
                self.assertEqual(applied["state"], "applied", applied)
                self.assertEqual(os.getpriority(os.PRIO_PROCESS, child.pid), candidate)
                restored = invoke(dict(apply, operation="restore", expected=candidate))
                self.assertEqual(restored["state"], "restored", restored)
                print("KILL_PRIORITY_REAL_ROUNDTRIP")
            else:
                candidate = initial+1 if initial < 19 else initial-1
                refused = invoke(dict(apply, target=candidate))
                self.assertEqual(refused["state"], "refused", refused)
                self.assertFalse(refused["attempted"])
                print("KILL_PRIORITY_REAL_REFUSAL_ONLY: reversible range unavailable")
            self.assertEqual(os.getpriority(os.PRIO_PROCESS, child.pid), initial)
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait(timeout=5)
            child.stdout.close()


if __name__ == "__main__":
    unittest.main()
