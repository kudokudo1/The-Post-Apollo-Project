"""Clock BG1-B2B16: real native V2 file sync witness via signed AF_UNIX.

Tests use the existing real SO_PEERPIDFD + independently signed Clock
origin harness and isolated source bytes. Not a Quickshell live handoff.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
HARNESS=ROOT/"tests/time/test_clock_bg1_b2b10_native_supervisor.py"
SUPERVISOR=ROOT/"services/time/AlarmNativeClockSupervisor.py"
WITNESS=ROOT/"services/time/AlarmFinalV2SourceWitness.py"


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


Fixture=load(HARNESS,"clock_b2b16_actual_native_socket_fixture")
Server=Fixture.Supervisor
Final=Server.FinalV2


def bytes_of(doc):
    return (json.dumps(doc,indent=2,ensure_ascii=False)+"\n").encode("utf-8")


class ClockB2B16NativeFinalV2Tests(unittest.TestCase):
    def setUp(self):
        self.h=Fixture.ClockNativeSupervisorTests(
            methodName="test_real_af_unix_signed_client_is_only_observed_never_authorized")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.source_dir=self.h.root/Final.DISPOSABLE_PARENT
        self.source_dir.mkdir(mode=0o700)
        self.source=self.source_dir/Final.SOURCE_NAME
        self.raw=bytes_of({"version":2,"nextId":2,"alarms":[{
            "id":1,"name":"SENSITIVE ALARM TITLE DO NOT LOG"}]})
        self.source.write_bytes(self.raw)
        self.source.chmod(0o600)
        self.digest=hashlib.sha256(self.raw).hexdigest()
        self.h.server.pin_synthetic_final_v2(
            source_path=self.source,expected_digest=self.digest,
            expected_uid=os.getuid())

    def exchange(self,action="INSPECT_FINAL_V2",**kwargs):
        return self.h.exchange(Fixture.request(action),**kwargs)

    def refused(self,call,reason,kind=Final.Refused):
        with self.assertRaises(kind) as e:
            call()
        self.assertEqual(str(e.exception),reason)

    def fresh(self,source=None,digest=None,uid=None,synthetic=True):
        return Final.ClockFinalV2SourceWitness(
            source_path=self.source if source is None else source,
            pinned_sha256=self.digest if digest is None else digest,
            expected_uid=os.getuid() if uid is None else uid,
            synthetic_only=synthetic)

    def test_real_signed_kernel_peer_and_file_sync_are_observed_only(self):
        observed=self.exchange()
        self.assertEqual(observed["reason"],
                         "FINAL_V2_SYNC_OBSERVED_ONLY_NOT_AUTHORIZED")
        self.assertTrue(observed["originObserved"])
        self.assertTrue(observed["finalV2RevisionObserved"])
        self.assertTrue(observed["fileSyncObserved"])
        self.assertTrue(observed["parentDirectorySyncObserved"])
        self.assertFalse(observed["sourceExclusive"])
        self.assertFalse(observed["finalRevisionDurablyLocked"])
        for key in ("roleAuthenticated","writerStopped","releaseAcknowledged",
                    "oldWriterRestartPrevented","ownsRealAlarmFile",
                    "canTransferOwnership","canRing","canNotify"):
            self.assertIs(observed[key],False,key)
        packet=json.dumps(observed)
        self.assertNotIn("SENSITIVE ALARM",packet)
        self.assertNotIn(str(self.source),packet)
        self.assertNotIn(self.digest,packet)

    def test_missing_independently_pinned_source_refuses_after_signed_peer(self):
        self.source.unlink()
        denied=self.exchange()
        self.assertTrue(denied["originObserved"])
        self.assertFalse(denied["finalV2RevisionObserved"])
        self.assertEqual(denied["reason"],
                         "NO_TRUSTED_FINAL_V2_SOURCE_WITNESS")

    def test_changed_v2_contents_refuse_without_mutating_file(self):
        self.source.write_bytes(bytes_of({
            "version":2,"nextId":1,"alarms":[]}))
        self.source.chmod(0o600)
        before=self.source.read_bytes()
        denied=self.exchange()
        self.assertTrue(denied["originObserved"])
        self.assertFalse(denied["fileSyncObserved"])
        self.assertEqual(self.source.read_bytes(),before)

    def test_wrong_kernel_signer_and_pid_ticks_refuse_before_source_read(self):
        for kwargs in (
            {"trusted":False},
            {"spawn_kwargs":{"issuer_pin":"f"*64}},
            {"spawn_kwargs":{"peer_ticks_delta":1}},
        ):
            with self.subTest(kwargs=kwargs):
                # A new server is needed per independent process because
                # the B2B11 synthetic ledger denies a different unretired
                # peer, even if the earlier request was refused.
                self.h.server._test_pins.clear()
                response=self.exchange(**kwargs)
                self.assertFalse(response["originObserved"])
                self.assertFalse(response["finalV2RevisionObserved"])
                self.h.stop_child()

    def test_source_symlink_and_hardlink_are_rejected_without_following(self):
        self.source.unlink()
        victim=self.h.root/"outside-target"
        victim.write_text("do not modify")
        self.source.symlink_to(victim)
        self.refused(self.fresh().observe,"FINAL_V2_SYNC_OR_READ_REFUSED")
        self.assertEqual(victim.read_text(),"do not modify")
        self.source.unlink()
        self.source.write_bytes(self.raw)
        self.source.chmod(0o600)
        linked=self.h.root/"second-hardlink"
        os.link(self.source,linked)
        self.refused(self.fresh().observe,"UNSAFE_FINAL_V2_SOURCE")
        self.assertEqual(linked.read_bytes(),self.raw)

    def test_world_writable_file_and_directory_are_not_trusted(self):
        self.source.chmod(0o666)
        self.refused(self.fresh().observe,"UNSAFE_FINAL_V2_SOURCE")
        self.source.chmod(0o600)
        self.source_dir.chmod(0o777)
        # The disposable harness must refuse the unsafe directory at
        # construction, before even attempting the path chain open.
        self.refused(lambda:self.fresh().observe(),
                     "UNSAFE_DISPOSABLE_FINAL_V2_DIRECTORY")
        self.source_dir.chmod(0o700)

    def test_directory_replacement_link_or_foreign_owner_is_rejected(self):
        self.source.unlink()
        self.source_dir.rmdir()
        target=self.h.root/"actual"
        target.mkdir(mode=0o700)
        (target/Final.SOURCE_NAME).write_bytes(self.raw)
        self.source_dir.symlink_to(target)
        self.refused(lambda:self.fresh().observe(),
                     "UNSAFE_DISPOSABLE_FINAL_V2_DIRECTORY")
        self.source_dir.unlink()
        self.source_dir.mkdir(mode=0o700)
        self.source.write_bytes(self.raw)
        self.source.chmod(0o600)
        self.refused(lambda:self.fresh(uid=os.getuid()+1),
                     "DISPOSABLE_FINAL_V2_SOURCE_REQUIRED")

    def test_duplicate_fields_nan_invalid_document_and_oversize_refuse(self):
        for raw in (
            b'{"alarms":[],"nextId":1,"version":2,"version":2}\n',
            b'{"alarms":[],"nextId":NaN,"version":2}\n',
            b'{"alarms":{},"nextId":1,"version":2}\n',
            b'{"alarms":[{"id":1},{"id":1}],"nextId":2,"version":2}\n',
            b'{"alarms":[],"nextId":1,"version":true}\n',
        ):
            with self.subTest(raw=raw[:60]):
                with self.assertRaises(Final.Refused):
                    Final._check_v2(raw)
        self.source.write_bytes(b"X"*(Final.MAX_FILE+1))
        self.refused(self.fresh().observe,"FINAL_V2_SIZE_REFUSED")

    def test_atomic_file_replacement_during_fsync_cannot_claim_stable_revision(self):
        saved_sync=Final.os.fsync
        counter=[0]
        def replace_on_sync(fd):
            saved_sync(fd)
            counter[0]+=1
            if counter[0]==1:
                replacement=self.source_dir/"replacement-v2"
                replacement.write_bytes(self.raw)
                replacement.chmod(0o600)
                os.replace(replacement,self.source)
        with patch.object(Final.os,"fsync",side_effect=replace_on_sync):
            self.refused(self.fresh().observe,
                         "FINAL_V2_CHANGED_DURING_SYNC")
        self.assertEqual(counter[0],2)
        self.assertEqual(self.source.read_bytes(),self.raw)

    def test_mutating_existing_inode_during_fsync_cannot_claim_stable_revision(self):
        saved_sync=Final.os.fsync
        modified=[False]
        def mutate(fd):
            saved_sync(fd)
            if not modified[0]:
                modified[0]=True
                self.source.write_bytes(bytes_of({
                    "version":2,"nextId":1,"alarms":[]}))
        with patch.object(Final.os,"fsync",side_effect=mutate):
            self.refused(self.fresh().observe,
                         "FINAL_V2_CHANGED_DURING_SYNC")
        self.assertTrue(modified[0])

    def test_untrusted_socket_cannot_choose_source_path_or_digest(self):
        for field in ("sourcePath","expectedSha256","source","digest",
                      "canTransferOwnership","lease"):
            data=json.dumps({"v":1,"action":"INSPECT_FINAL_V2",
                             field:"/etc/passwd"},sort_keys=True,
                             separators=(",",":")).encode()+b"\n"
            with self.subTest(field=field):
                with self.assertRaises(Server.Refused):
                    Server._decode_request(data)
        invalid=Fixture.request("TAKE_OWNERSHIP")
        assert invalid
        self.assertIn("INSPECT_FINAL_V2",Server.ACTIONS)

    def test_readonly_installed_source_not_exposed_without_protected_pins(self):
        self.assertIsNone(Server.APPROVED_CLOCK_FINAL_V2_SOURCE_PATH)
        self.assertIsNone(Server.APPROVED_CLOCK_FINAL_V2_SOURCE_DIGEST)
        self.assertIsNone(Server.APPROVED_CLOCK_FINAL_V2_SOURCE_UID)
        self.assertIsNone(Server.APPROVED_CLOCK_RELEASE_ROOT_SHA256)
        self.assertIsNone(Server.APPROVED_CLOCK_RELEASE_FLOOR)
        self.assertFalse(self.h.server._observe_installed(None))
        native=SUPERVISOR.read_text()
        qml=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',qml)
        self.assertIn("nativeWriterDrainBridgeInstalled: false",qml)
        self.assertIn("writerReleaseAcknowledged: false",qml)
        self.assertIn("FinalV2.ClockFinalV2SourceWitness",native)
        for forbidden in ("notify-send","alarmFile.setText","systemctl",
                          "os.replace(", "canRing=True"):
            self.assertNotIn(forbidden,WITNESS.read_text())
        self.assertFalse(Server._final_response("DENY")["canTransferOwnership"])
        self.assertFalse(Server._final_response("DENY")["releaseAcknowledged"])

    def test_synthetic_path_and_pin_cannot_be_used_as_production_source(self):
        self.refused(lambda:self.fresh(synthetic=False).observe(),
                     "UNSAFE_FINAL_V2_DIRECTORY_CHAIN")
        self.refused(lambda:self.fresh(digest="f"*64).observe(),
                     "FINAL_V2_DIGEST_MISMATCH")
        self.refused(lambda:self.fresh(digest="bad"),
                     "INDEPENDENT_FINAL_V2_PIN_REQUIRED")
        self.refused(lambda:self.fresh(source=self.h.root/"not-clock.json"),
                     "FINAL_V2_PATH_NOT_APPROVED")
        self.refused(lambda:self.h.server.pin_synthetic_final_v2(
            source_path=self.source,expected_digest=self.digest,
            expected_uid=os.getuid()),
            "SYNTHETIC_FINAL_V2_ALREADY_PINNED",Server.Refused)
        self.assertTrue(self.h.server.synthetic)

if __name__=="__main__":
    unittest.main()
