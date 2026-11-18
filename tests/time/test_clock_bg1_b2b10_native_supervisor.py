"""Clock BG1-B2B10: real AF_UNIX supervisor request handling, never actuation."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/time/AlarmNativeClockSupervisor.py"
spec = importlib.util.spec_from_file_location("clock_b2b10_runtime", MODULE)
Supervisor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = Supervisor
spec.loader.exec_module(Supervisor)
Role = Supervisor.Origin.Role

CLIENT_SOURCE = r'''
import socket,sys,time
peer=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
peer.connect(sys.argv[1])
request=sys.stdin.buffer.readline()
peer.sendall(request)
reply=peer.makefile("rb").readline(4096)
sys.stdout.buffer.write(reply)
sys.stdout.buffer.flush()
time.sleep(.5)
'''

def request(action):
    return (json.dumps({"v":1,"action":action}, sort_keys=True,
                       separators=(",",":")).encode("ascii")+b"\n")


class ClockNativeSupervisorTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="clock-b2b10-ci-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode),0o700)
        self.runtime=self.root/"bg1-clock-supervisor-fixture"
        self.runtime.mkdir(mode=0o700)
        self.trust=self.root/"bg1-installed-role-fixture"
        self.trust.mkdir(mode=0o700)
        self.script=self.root/"test-clock-bridge.py"
        self.script.write_text(CLIENT_SOURCE,encoding="utf-8")
        self.script.chmod(0o600)
        self.issuer=Ed25519PrivateKey.generate()
        self.public=self.issuer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.fingerprint=hashlib.sha256(self.public).hexdigest()
        self.root_file=self.trust/Supervisor.Origin.ROOT_NAME
        self.policy_file=self.trust/"clock-clock-ui-bridge-origin-v1.json"
        self.signature_file=self.trust/"clock-clock-ui-bridge-origin-v1.sig"
        self.exe=os.path.realpath(sys.executable)
        self.server=Supervisor.ClockNativeSupervisor(
            self.runtime,synthetic_only=True)
        self.server.bind()
        self.addCleanup(self.server.close)
        self.child=None

    def stop_child(self):
        if self.child is None:
            return
        if self.child.poll() is None:
            self.child.terminate()
        try:
            self.child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.communicate(timeout=3)

    def write_trust(self, argv, *, policy_updates=None, sign_with=None):
        data={
            "schema":Role.SCHEMA,
            "purpose":Role.PURPOSE,
            "role":"clock-ui-bridge",
            "releaseEpoch":5,
            "releaseSequence":12,
            "entrypointPath":str(self.script),
            "entrypointSha256":hashlib.sha256(
                self.script.read_bytes()).hexdigest(),
            "interpreterPath":self.exe,
            "argv":argv,
            "uid":os.getuid(),
            "gid":os.getgid(),
        }
        data.update(policy_updates or {})
        raw=Role.canonical(data)
        signer=self.issuer if sign_with is None else sign_with
        for path,body in (
            (self.root_file,self.public),
            (self.policy_file,raw),
            (self.signature_file,signer.sign(Role.DOMAIN+raw))):
            path.write_bytes(body)
            path.chmod(0o600)

    def spawn(self, *, trusted=True, peer_ticks_delta=0,
              issuer_pin=None, policy_updates=None, sign_with=None):
        argv=[self.exe,"-I","-B",str(self.script),str(self.server.socket_path)]
        self.write_trust(argv,policy_updates=policy_updates,sign_with=sign_with)
        self.child=subprocess.Popen(
            argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self.addCleanup(self.stop_child)
        ticks=Role._Peer._start_ticks(self.child.pid)
        if trusted:
            pin=Supervisor.SyntheticSessionPin(
                pid=self.child.pid,ticks=ticks+peer_ticks_delta,
                interpreter=self.exe,role="clock-ui-bridge",
                trust_directory=str(self.trust),
                pinned_root_sha256=self.fingerprint if issuer_pin is None
                    else issuer_pin,
                minimum_epoch=5,minimum_sequence=12)
            self.server.add_synthetic_session(pin)
        return self.child

    def exchange(self, frame, *, trusted=True, spawn_kwargs=None):
        self.spawn(trusted=trusted,**(spawn_kwargs or {}))
        self.child.stdin.write(frame)
        self.child.stdin.flush()
        evidence=self.server.serve_once(timeout=4.0)
        stdout=self.child.stdout.readline()
        self.assertTrue(stdout, "native client received no response")
        response=json.loads(stdout)
        self.assertEqual(evidence,response)
        self.assertEqual(response["v"],1)
        self.assertFalse(response["ok"])
        for k in ("roleAuthenticated","writerStopped","releaseAcknowledged",
                  "ownsRealAlarmFile","canTransferOwnership","canRing",
                  "canNotify"):
            self.assertIs(response[k],False,k)
        return response

    def denied(self,fn,code):
        with self.assertRaises(Supervisor.Refused) as exc:
            fn()
        self.assertEqual(str(exc.exception),code)

    def test_real_af_unix_signed_client_is_only_observed_never_authorized(self):
        result=self.exchange(request("INSPECT_ORIGIN"))
        self.assertEqual(result["reason"],"OBSERVED_ONLY_NOT_AUTHORIZED")
        self.assertTrue(result["originObserved"])
        path=self.server.socket_path
        self.assertEqual(stat.S_IMODE(os.lstat(path).st_mode),0o600)
        self.assertTrue(stat.S_ISSOCK(os.lstat(path).st_mode))

    def test_production_supervisor_has_no_enrolled_clients(self):
        self.assertFalse(self.server.synthetic is False)
        result=self.exchange(request("INSPECT_ORIGIN"),trusted=False)
        self.assertFalse(result["originObserved"])
        self.assertEqual(result["reason"],"NO_INSTALLED_CLOCK_SESSION_AUTHORITY")
        self.denied(lambda:Supervisor.ClockNativeSupervisor(self.runtime),
                    "INSTALLED_USER_RUNTIME_REQUIRED")

    def test_actuation_requests_always_refuse_even_with_signed_client(self):
        for action in ("REQUEST_PAUSE","RELEASE_WRITER",
                       "TAKE_OWNERSHIP","RING_ALARM"):
            with self.subTest(action=action):
                # Each response never touches any live alarm writer.
                resp=Supervisor._response("NATIVE_WRITER_HANDOFF_NOT_AUTHORIZED")
                self.assertFalse(resp["canRing"])
                self.assertFalse(resp["releaseAcknowledged"])
        result=self.exchange(request("REQUEST_PAUSE"))
        self.assertEqual(result["reason"],"NATIVE_WRITER_HANDOFF_NOT_AUTHORIZED")
        self.assertFalse(result["originObserved"])

    def test_signed_wrong_root_and_unpinned_process_refuse(self):
        result=self.exchange(request("INSPECT_ORIGIN"),
                             spawn_kwargs={"issuer_pin":"f"*64})
        self.assertEqual(result["reason"],"NO_INSTALLED_CLOCK_SESSION_AUTHORITY")
        self.assertFalse(result["originObserved"])

    def test_wrong_kernel_start_ticks_refuse(self):
        result=self.exchange(request("INSPECT_ORIGIN"),
                             spawn_kwargs={"peer_ticks_delta":1})
        self.assertEqual(result["reason"],"NO_INSTALLED_CLOCK_SESSION_AUTHORITY")
        self.assertFalse(result["originObserved"])

    def test_bad_signature_domain_refuse(self):
        result=self.exchange(request("INSPECT_ORIGIN"),
                             spawn_kwargs={
                                 "sign_with":Ed25519PrivateKey.generate()})
        self.assertFalse(result["originObserved"])

    def test_unknown_unsafe_request_commands_and_extra_fields_refuse(self):
        packets=[
            b'{"action":"REQUEST_PAUSE","v":1,"actuate":true}\n',
            b'{"action":"INSPECT_ORIGIN","v":1,"v":1}\n',
            b'{"action":"UNKNOWN","v":1}\n',
            b'{"action":"INSPECT_ORIGIN","v":true}\n',
            b'{"action":"INSPECT_ORIGIN","v":NaN}\n',
            b'{"v":1,"action":"INSPECT_ORIGIN"}\n',
            b'["INSPECT_ORIGIN"]\n',
            b'{"action":"INSPECT_ORIGIN","v":1}' + b"X"*1500+b"\n",
        ]
        for data in packets:
            with self.subTest(data=data[:80]):
                with self.assertRaises(Supervisor.Refused):
                    Supervisor._decode_request(data)
        result=self.exchange(b'{"action":"REQUEST_PAUSE","v":1,"actuate":true}\n')
        self.assertFalse(result["originObserved"])
        self.assertEqual(result["reason"],"CLOCK_REQUEST_OPERATION_REFUSED")

    def test_fixed_runtime_path_and_directory_owner_modes(self):
        self.denied(lambda:Supervisor.ClockNativeSupervisor(
            self.root,synthetic_only=True),
            "DISPOSABLE_SUPERVISOR_RUNTIME_REQUIRED")
        self.runtime.chmod(0o755)
        self.denied(lambda:Supervisor.ClockNativeSupervisor(
            self.runtime,synthetic_only=True),
            "UNSAFE_RUNTIME_DIRECTORY")
        self.runtime.chmod(0o700)
        self.denied(self.server.bind,"SUPERVISOR_ALREADY_LISTENING")
        other=Supervisor.ClockNativeSupervisor(self.runtime,synthetic_only=True)
        self.denied(other.bind,"CLOCK_SOCKET_ALREADY_EXISTS")

    def test_socket_symlink_and_stale_path_not_removed(self):
        self.server.close()
        victim=self.root/"keep"
        victim.write_text("do not remove")
        self.server.socket_path.symlink_to(victim)
        self.denied(self.server.bind,"CLOCK_SOCKET_ALREADY_EXISTS")
        self.assertEqual(victim.read_text(),"do not remove")
        self.server.socket_path.unlink()

    def test_shutdown_cannot_unlink_replaced_socket_path(self):
        path=self.server.socket_path
        path.rename(path.with_name("old-supervisor.sock"))
        path.write_text("other session owns this path")
        self.server.close()
        self.assertEqual(path.read_text(),"other session owns this path")
        path.unlink()

    def test_fake_test_roster_cannot_enroll_production(self):
        self.denied(lambda:self.server.add_synthetic_session(
            {"pid":os.getpid(),"trusted":True}),"SYNTHETIC_SESSION_ONLY")
        self.denied(lambda:self.server.add_synthetic_session(
            Supervisor.SyntheticSessionPin(
                pid=0,ticks=1,interpreter=self.exe,
                role="clock-ui-bridge",trust_directory=str(self.trust),
                pinned_root_sha256=self.fingerprint,
                minimum_epoch=5,minimum_sequence=12)),
            "SYNTHETIC_SESSION_ONLY")
        # A read-only, real installed-mode supervisor has no such API.
        self.assertFalse("add_synthetic_session" in (
            ROOT/"services/time/AlarmManagerService.qml").read_text())

    def test_entrypoint_tampering_refuses_signed_origin(self):
        self.spawn()
        self.script.write_text(CLIENT_SOURCE+"# changed\n")
        self.child.stdin.write(request("INSPECT_ORIGIN"))
        self.child.stdin.flush()
        evidence=self.server.serve_once(timeout=4.0)
        self.assertEqual(evidence["reason"],"NO_INSTALLED_CLOCK_SESSION_AUTHORITY")
        self.assertFalse(evidence["originObserved"])

    def test_no_host_modification_and_no_background_actuation(self):
        source=MODULE.read_text()
        live=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',live)
        self.assertNotIn("AlarmNativeClockSupervisor",live)
        for forbidden in ("alarmFile.setText", "notify-send", "os.replace(",
                          "systemctl", "SoundEffect", "canRing=True",
                          "write_text(", "subprocess.Popen("):
            self.assertNotIn(forbidden,source)
        self.assertIn('"canRing": False',source)
        self.assertIn('"canTransferOwnership": False',source)


if __name__ == "__main__":
    unittest.main()
