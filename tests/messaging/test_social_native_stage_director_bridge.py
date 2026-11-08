#!/usr/bin/env python3
"""Social W's compositor-native handoff and exact-identity fallback contract."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"widgets/messanger/DiscordGeometry.py"
spec=importlib.util.spec_from_file_location("social_geometry", SOURCE)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def pair_snapshot(host_id=81, guest_id=92, guest_shell="xdg_shell"):
    return {
        "social": {
            "rect":{"x":120,"y":110,"width":1000,"height":700},
            "focused":False,"visible":True,
            "conId":host_id,"shell":"xdg_shell"},
        "discord": {
            "rect":{"x":231,"y":111,"width":888,"height":698},
            "focused":True,"visible":True,"kind":"main",
            "conId":guest_id,"shell":guest_shell},
    }


class Commands:
    def __init__(self, supported=True):
        self.commands=[]
        self.supported=supported
    def request(self, typ, command=""):
        if typ == g.IPC_COMMAND:
            self.commands.append(command)
            if not self.supported:
                return [{"success":False,"error":"Unknown command"}]
            return [{"success":True}]
        raise AssertionError("unexpected Sway IPC read")
    def close(self):
        pass


class NativePairTests(unittest.TestCase):
    def setUp(self):
        self.bridge=g.Bridge(0.008)
        self.bridge.discord_selected=True
        self.bridge.discord_ready=True
        self.bridge.discord_docked=True
        self.bridge.discord_kind="main"
        self.bridge.native_pair_ipc=Commands()

    def test_admit_once_and_stop_python_follower(self):
        snapshot=pair_snapshot()
        self.assertTrue(self.bridge.update_native_pair(snapshot))
        self.assertEqual(self.bridge.native_pair_key,(81,92,110,1))
        self.assertEqual(self.bridge.native_pair_ipc.commands,
                         ["stage_director_social pair 81 92 110 1"])
        snapshot["nativeStageDirector"]=True
        self.bridge.fast_follow(snapshot)
        self.assertIsNone(snapshot["fastLeader"])
        self.assertIsNone(snapshot["shared"])
        self.assertEqual(self.bridge.pending_sync,{})
        self.assertTrue(self.bridge.update_native_pair(snapshot))
        self.assertEqual(len(self.bridge.native_pair_ipc.commands),1)
        self.bridge.native_pair_probe_at=0
        self.assertTrue(self.bridge.update_native_pair(snapshot))
        self.assertEqual(self.bridge.native_pair_ipc.commands[-1],
                         "stage_director_social status")

    def test_refuse_until_docked_and_exact_geometry(self):
        snapshot=pair_snapshot()
        self.bridge.discord_docked=False
        self.assertFalse(self.bridge.update_native_pair(snapshot))
        self.bridge.discord_docked=True
        snapshot["discord"]["rect"]["x"]+=1
        self.assertFalse(self.bridge.update_native_pair(snapshot))
        snapshot["discord"]["rect"]["x"]-=1
        self.assertTrue(self.bridge.update_native_pair(snapshot))

    def test_splash_xwayland_hidden_and_missing_identity(self):
        for change in ("splash","xwayland","hidden","missing"):
            with self.subTest(change=change):
                b=g.Bridge(0.008)
                b.discord_selected=b.discord_ready=b.discord_docked=True
                b.discord_kind="main"
                b.native_pair_ipc=Commands()
                snap=pair_snapshot()
                if change=="splash": b.discord_kind="splash"
                if change=="xwayland": snap["discord"]["shell"]="xwayland"
                if change=="hidden": snap["discord"]["visible"]=False
                if change=="missing": snap["social"]["conId"]=None
                self.assertFalse(b.update_native_pair(snap))
                self.assertEqual(b.native_pair_ipc.commands,[])

    def test_legacy_fallback_and_identity_replacement(self):
        self.bridge.native_pair_ipc=Commands(supported=False)
        snap=pair_snapshot()
        self.assertFalse(self.bridge.update_native_pair(snap))
        self.assertIsNone(self.bridge.native_pair_key)
        self.assertEqual(len(self.bridge.native_pair_ipc.commands),1)
        # Old SwayPX cannot be spammed at 8ms.
        self.assertFalse(self.bridge.update_native_pair(snap))
        self.assertEqual(len(self.bridge.native_pair_ipc.commands),1)
        self.bridge.native_pair_retry_at=0
        self.bridge.native_pair_ipc=Commands()
        self.assertTrue(self.bridge.update_native_pair(snap))
        changed=pair_snapshot(81,93)
        self.assertTrue(self.bridge.update_native_pair(changed))
        self.assertEqual(self.bridge.native_pair_ipc.commands[-2:],
                         ["stage_director_social clear",
                          "stage_director_social pair 81 93 110 1"])
        self.bridge.discord_docked=False
        self.assertFalse(self.bridge.update_native_pair(changed))
        self.assertEqual(self.bridge.native_pair_ipc.commands[-1],
                         "stage_director_social clear")

    def test_native_status_rejected_recovers_legacy(self):
        snap=pair_snapshot()
        self.assertTrue(self.bridge.update_native_pair(snap))
        self.bridge.native_pair_ipc.supported=False
        self.bridge.native_pair_probe_at=0
        self.assertFalse(self.bridge.update_native_pair(snap))
        self.assertIsNone(self.bridge.native_pair_key)
        snap["nativeStageDirector"]=False
        snap["discord"]["rect"]["x"] += 12
        self.bridge.fast_follow(snap)
        self.assertEqual(snap["fastLeader"],"discord")
        self.assertIn("social",self.bridge.pending_sync)

    def test_helper_exits_after_quickshell_pipe_closes(self):
        # The production Quickshell restart intentionally SIGKILLs the old
        # owner. Its stdin pipe closes even though the child has no signal.
        # Without the EOF -> stop_event fix, Bridge.poll_loop survives
        # indefinitely and each restart leaks another 8ms polling worker.
        for watching in (False, True):
            with self.subTest(watching=watching):
                child = subprocess.Popen(
                    [sys.executable, "-B", str(SOURCE), "--interval-ms", "8"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=ROOT,
                )
                try:
                    self.assertIsNotNone(child.stdin)
                    if watching:
                        child.stdin.write(b'{"op":"watch","enabled":true}\n')
                        child.stdin.flush()
                    time.sleep(0.08)
                    self.assertIsNone(child.poll(), "helper exited before EOF")
                    child.stdin.close()
                    self.assertEqual(
                        child.wait(timeout=3), 0,
                        "helper did not stop after its owner's pipe closed")
                finally:
                    if child.stdin and not child.stdin.closed:
                        child.stdin.close()
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=3)

    def test_social_qml_does_not_reintroduce_polling(self):
        qml=(ROOT/"widgets/messanger/MessagingW.qml").read_text()
        fn=qml.split("function reconcileGroupGeometry(payload)",1)[1]
        self.assertIn("if (payload.nativeStageDirector === true)",fn)
        native=fn.index("if (payload.nativeStageDirector === true)")
        legacy=fn.index("if (socialChanged && discordChanged)",native)
        self.assertLess(native,legacy)
        self.assertIn("adoptSocialGeometry(socialRect)",fn[native:legacy])


if __name__=="__main__":
    unittest.main()
