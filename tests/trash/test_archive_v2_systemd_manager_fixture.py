"""V2u deny-only GetUnitByPIDFD manager-reply contract tests.

The fixture NEVER queries systemd, never starts services, and never writes
ArchiveStore. It exercises the V2p kernel pidfd and V2t signed synthetic
broker with a separately supplied strict fake manager response.
"""
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import test_archive_v2_origin_checkpoint as previous
from scripts.trash.archive_v2_fixture_socket import (
    FixtureWireError, encode_fixture_frame,
)
from scripts.trash.archive_v2_systemd_manager_fixture import (
    ManagerOriginError, SyntheticPidfdManager,
)

UNIT = "post-apollo-fixture.service"
OBJECT = "/org/freedesktop/systemd1/unit/post_2dapollo_2dfixture_2eservice"
INVOCATION = "a"*32


class PidfdManagerContractV2uTests(TestCase):
    def setUp(self):
        self.v2t = previous.SourceOriginCheckpointV2tTests("runTest")
        self.v2t.setUp()
        self.addCleanup(self.v2t.doCleanups)
        self.f = self.v2t.f
        self.v2t.pre.enroll()
        group = self.v2t.origin_policy["expectedCgroupV2"]
        self.policy = {
            "origin":"TEST_FIXTURE_ONLY",
            "ownerId":"demo-scrape",
            "expectedUid":os.geteuid(),
            "expectedGid":os.getegid(),
            "expectedUnitId":UNIT,
            "expectedInvocationId":INVOCATION,
            "expectedUnitObjectPath":OBJECT,
            "expectedControlGroup":group,
            "expectedFragmentPath":str(self.f.unit),
            "expectedUnitSha256":self.f.policy["unitSha256"],
        }
        self.reply = {
            "unitId":UNIT,
            "invocationId":INVOCATION,
            "unitObjectPath":OBJECT,
            "controlGroup":group,
            "fragmentPath":str(self.f.unit),
            "loadState":"loaded",
            "activeState":"active",
        }
        self.manager = SyntheticPidfdManager(self.reply)

    def send(self, *, manager=None, policy=None, origin=None):
        if manager is None:
            manager = self.manager
        if policy is None:
            policy = self.policy
        if origin is None:
            origin = self.v2t.origin_policy
        return self.f.send(
            signed_service_grant=self.v2t.pre.grant,
            signed_service_release=self.v2t.pre.signed(),
            service_release_history=self.v2t.pre.history,
            origin_policy=origin,
            signed_checkpoint=self.v2t.signed_checkpoint(),
            checkpoint_root=self.v2t.checkpoint_root,
            manager_fixture=manager, manager_policy=policy,
        )

    def count(self):
        return self.f.ledger.test_copy_status("demo-scrape")

    def test_fixture_manager_query_bind_and_recovery_denies_authority(self):
        response=self.send()
        self.assertTrue(response["ok"], response)
        self.assertTrue(response["managerFixtureMatchedBeforeCommit"])
        self.assertFalse(response["systemdUnitVerified"])
        self.assertEqual(self.manager.calls, 2)
        for key in ("sourceProcessVerified","archiveCopyAuthorized",
                    "productionAllowed","captureAllowed","restoreAllowed",
                    "burnAllowed"):
            self.assertFalse(response[key])
        self.assertEqual(len(response["managerWitnessSha256"]),64)
        stored=self.f.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)
        self.assertEqual(stored["managerWitnessSha256"],
                         response["managerWitnessSha256"])
        self.assertTrue(stored["payloadIntegrityVerified"])
        self.assertEqual((self.count()["testCopies"],
                          self.count()["consumedNonces"]),(1,1))
        self.assertFalse((self.f.root/"trashpp-archive-v2.sqlite3").exists())

    def test_wrong_unit_id_or_invocation_refuses_before_nonce(self):
        for change in (
            {"unitId":"unapproved.service"},
            {"invocationId":"b"*32},
            {"unitObjectPath":"/org/freedesktop/systemd1/unit/evil_2eservice"},
            {"loadState":"not-found"},
            {"activeState":"inactive"},
        ):
            manager=SyntheticPidfdManager(dict(self.reply,**change))
            response=self.send(manager=manager)
            self.assertEqual(response["error"],"MANAGER_UNIT_MISMATCH")
        self.assertEqual(self.count()["consumedNonces"],0)

    def test_cgroup_and_fragment_must_match_observed_origin_and_unit_file(self):
        for change, expected in (
            ({"controlGroup":"/forged.slice"}, "MANAGER_CGROUP_MISMATCH"),
            ({"fragmentPath":"/tmp/other.service"}, "MANAGER_FRAGMENT_MISMATCH"),
        ):
            result=self.send(
                manager=SyntheticPidfdManager(dict(self.reply,**change)))
            self.assertEqual(result["error"],expected)
        self.assertEqual(self.count()["testCopies"],0)

    def test_untrusted_policy_cannot_choose_own_manager_or_unit(self):
        changes=[
            ({"origin":"LIVE_SYSTEMD"}, "MANAGER_POLICY_NOT_PROVISIONED"),
            ({"expectedUnitId":"other.service"},"MANAGER_UNIT_MISMATCH"),
            ({"expectedInvocationId":"c"*32},"MANAGER_UNIT_MISMATCH"),
            ({"expectedUid":os.getuid()+1},"MANAGER_UID_MISMATCH"),
            ({"expectedControlGroup":"/different.slice"},
             "MANAGER_CGROUP_POLICY_INVALID"),
            ({"expectedUnitSha256":"0"*64},
             "MANAGER_UNIT_FILE_POLICY_INVALID"),
            ({"ownerId":"weather-events"},"MANAGER_OWNER_MISMATCH"),
        ]
        for change, expected in changes:
            result=self.send(policy=dict(self.policy,**change))
            self.assertEqual(result["error"],expected)
        self.assertEqual(self.count()["testCopies"],0)

    def test_missing_manager_or_service_origin_components_fails_closed(self):
        args=dict(
            signed_service_grant=self.v2t.pre.grant,
            signed_service_release=self.v2t.pre.signed(),
            service_release_history=self.v2t.pre.history,
            signed_checkpoint=self.v2t.signed_checkpoint(),
            checkpoint_root=self.v2t.checkpoint_root,
        )
        self.assertEqual(self.f.send(
            **args, origin_policy=self.v2t.origin_policy,
            manager_policy=self.policy)["error"],
            "MANAGER_FIXTURE_COMPONENTS_REQUIRED")
        self.assertEqual(self.f.send(
            **args, manager_fixture=self.manager,
            manager_policy=self.policy)["error"],
            "MANAGER_FIXTURE_COMPONENTS_REQUIRED")
        self.assertEqual(self.count()["testCopies"],0)

    def test_fake_manager_reply_rejects_unrecognized_keys_and_wrong_types(self):
        for change in (
            {"untrustedProcess":321},
            {"invocationId":123},
            {"controlGroup":None},
        ):
            if "untrustedProcess" in change:
                with self.assertRaisesRegex(ManagerOriginError,
                                            "MANAGER_RESPONSE_SCHEMA_INVALID"):
                    SyntheticPidfdManager(dict(self.reply,**change))
                continue
            response=self.send(manager=SyntheticPidfdManager(
                dict(self.reply,**change)))
            self.assertEqual(response["error"],"MANAGER_RESPONSE_SCHEMA_INVALID")
        self.assertEqual(self.count()["consumedNonces"],0)

    def test_manager_invocation_changes_at_commit_and_both_rows_rollback(self):
        original=self.manager.get_unit_by_pidfd
        def new_invocation(pidfd):
            reply=original(pidfd)
            if self.manager.calls==2:
                reply["invocationId"]="e"*32
            return reply
        with patch.object(self.manager,"get_unit_by_pidfd",
                          side_effect=new_invocation):
            result=self.send()
        self.assertEqual(result["error"],"MANAGER_UNIT_MISMATCH")
        self.assertEqual(self.manager.calls,2)
        self.assertEqual(self.count()["consumedNonces"],0)
        self.assertEqual(self.count()["testCopies"],0)
        self.assertEqual(self.f.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)["state"],
            "TEST_NOT_ADMITTED")

    def test_manager_unavailable_or_pidfd_invalid_fails_closed(self):
        with patch.object(self.manager,"get_unit_by_pidfd",
                          side_effect=ManagerOriginError(
                              "MANAGER_PIDFD_INVALID")):
            result=self.send()
        self.assertEqual(result["error"],"MANAGER_PIDFD_INVALID")
        with patch("scripts.trash.archive_v2_peer_lifecycle.os.pidfd_open",
                   side_effect=OSError(38,"unavailable")):
            result=self.send()
        self.assertEqual(result["error"],"PEER_PIDFD_UNAVAILABLE")
        self.assertEqual(self.count()["testCopies"],0)

    def test_manager_cannot_be_supplied_by_client_wire_fields(self):
        packet=self.f.packet()
        packet["systemdManagerUnit"]="other.service"
        with self.assertRaisesRegex(FixtureWireError,
                                    "BROKER_REQUEST_SCHEMA_INVALID"):
            encode_fixture_frame(packet)
        self.assertEqual(self.count()["consumedNonces"],0)

    def test_older_v2t_receipt_has_no_manager_attestation(self):
        result=self.v2t.send()
        self.assertTrue(result["ok"],result)
        self.assertEqual(result["managerWitnessSha256"],"")
        self.assertFalse(result["managerFixtureMatchedBeforeCommit"])
        recovered=self.f.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)
        self.assertEqual(recovered["managerWitnessSha256"],"")

    def test_test_manager_never_contacts_dbus_or_archive(self):
        from scripts.trash import archive_v2_systemd_manager_fixture as mod
        source=Path(mod.__file__).read_text("utf-8")
        self.assertNotIn("dbus.SystemBus(",source)
        self.assertNotIn("subprocess.run(",source)
        self.assertNotIn("ArchiveStore(",source)
        self.assertNotIn("Quickshell.dataDir",source)
        self.assertNotIn("Ed25519PrivateKey",source)
        self.assertFalse(hasattr(mod,"main"))
        self.assertFalse(hasattr(mod,"serve_forever"))
