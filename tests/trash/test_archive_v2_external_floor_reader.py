"""V2w signed off-UID release-floor reader, private deny-only fixture tests.

All files are created in a private temporary CI directory owned by the test
user. No real root/system service or ArchiveStore is contacted or changed.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

import test_archive_v2_service_release_history as release_fixture
from scripts.trash.archive_v2_external_floor_reader import (
    FILE_NAME, SCHEMA, ExternalFloorRefused, ReadOnlyExternalFloor,
    canonical_floor,
)
from scripts.trash.archive_v2_service_release_history import canonical_release
from scripts.trash.archive_v2_signed_capture import AUDIENCE, PURPOSE

NOW = 1760000500000


def public_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class ReadOnlyExternalFloorV2wTests(unittest.TestCase):
    def setUp(self):
        self.previous = release_fixture.SignedServiceReleaseV2sTests("runTest")
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.previous.enroll()
        self.directory = self.previous.fixture.root
        self.floor_file = self.directory / FILE_NAME
        self.root_key = Ed25519PrivateKey.generate()
        self.pin = {
            "rootKeyId":"separate-fixture-authority",
            "publicKeyBytes":public_bytes(self.root_key),
            "origin":"EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.floor = {
            "schema":SCHEMA,
            "audience":AUDIENCE,
            "purpose":PURPOSE,
            "policyOrigin":"TEST_FIXTURE_ONLY",
            "rootKeyId":"separate-fixture-authority",
            "ownerId":"demo-scrape",
            "epoch":1,
            "sequence":1,
            "releaseSha256":hashlib.sha256(
                canonical_release(self.previous.release)).hexdigest(),
            "grantSha256":self.previous.grant_sha,
            "issuedAtMs":1760000400000,
            "validFromMs":1760000400000,
            "validUntilMs":1760000600000,
            "revoked":False,
        }
        self.write_floor()

    def write_floor(self, *, floor=None, signer=None):
        if floor is None:
            floor=self.floor
        if signer is None:
            signer=self.root_key
        signed = {
            "floor":floor,
            "signatureB64":base64.b64encode(
                signer.sign(canonical_floor(floor))).decode("ascii"),
        }
        data=json.dumps(signed,sort_keys=True,separators=(",",":"),
                        ensure_ascii=True).encode("ascii")
        self.floor_file.write_bytes(data)
        self.floor_file.chmod(0o600)
        return data

    def reader(self, *, root=None, expected_uid=None, pin=None,
               fixture=True):
        return ReadOnlyExternalFloor(
            self.directory if root is None else root,
            os.geteuid() if expected_uid is None else expected_uid,
            self.pin if pin is None else pin,
            test_fixture_only=fixture,
        )

    def verify(self, reader=None, *, signed_release=None, now_ms=NOW,
               owner_id="demo-scrape", grant_sha256=None):
        if reader is None:
            reader=self.reader()
        return reader.require_current(
            history=self.previous.history,
            signed_release=(
                self.previous.signed() if signed_release is None
                else signed_release),
            release_root=self.previous.fixture.trust_root,
            owner_id=owner_id,
            grant_sha256=(
                self.previous.grant_sha if grant_sha256 is None
                else grant_sha256),
            now_ms=now_ms,
        )

    def test_matching_signed_file_and_local_release_is_deny_only(self):
        verified=self.verify()
        self.assertEqual(verified["state"],
                         "TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY")
        self.assertEqual(verified["ownerId"],"demo-scrape")
        self.assertEqual(verified["sequence"],1)
        self.assertEqual(verified["releaseSha256"],
                         self.floor["releaseSha256"])
        self.assertEqual(len(verified["externalFloorSha256"]),64)
        self.assertTrue(verified["signatureVerified"])
        for flag in (
            "offUidFileObserved",
            "externallyProtectedMonotonicAuthorityVerified",
            "trustedClockVerified","sourceAuthorityVerified",
            "captureAllowed","productionAllowed",
            "restoreAllowed","burnAllowed",
        ):
            self.assertFalse(verified[flag])
        self.assertFalse(
            (self.directory/"trashpp-archive-v2.sqlite3").exists())

    def test_recheck_rejects_same_bytes_new_inode(self):
        reader=self.reader()
        new_file=self.directory/"replacement"
        new_file.write_bytes(self.floor_file.read_bytes())
        new_file.chmod(0o600)
        os.replace(new_file,self.floor_file)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_CHANGED"):
            self.verify(reader)

    def test_recheck_rejects_new_authority_signed_version(self):
        reader=self.reader()
        self.write_floor(floor=dict(self.floor,epoch=2))
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_CHANGED"):
            self.verify(reader)

    def test_file_is_read_only_and_missing_file_refuses(self):
        self.floor_file.unlink()
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_UNAVAILABLE"):
            self.reader()
        self.assertFalse(self.floor_file.exists())

    def test_different_signer_cannot_self_enroll(self):
        wrong=Ed25519PrivateKey.generate()
        self.write_floor(signer=wrong)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_SIGNATURE_REFUSED"):
            self.reader()

    def test_wrong_root_pinning_and_same_root_as_release_rejected(self):
        bad=dict(self.pin,publicKeyBytes=public_bytes(
            Ed25519PrivateKey.generate()))
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_SIGNATURE_REFUSED"):
            self.reader(pin=bad)
        reader=self.reader()
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_ROOT_NOT_DISTINCT"):
            reader.require_current(
                history=self.previous.history,
                signed_release=self.previous.signed(),
                release_root={
                    "publicKeyBytes":self.pin["publicKeyBytes"]},
                owner_id="demo-scrape",
                grant_sha256=self.previous.grant_sha,
                now_ms=NOW)

    def test_fixture_cannot_impersonate_separately_owned_production_floor(self):
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_OWNER_NOT_INDEPENDENT"):
            self.reader(fixture=False, pin=dict(
                self.pin,origin="EXTERNALLY_PINNED_SOURCE_ROOT"))
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_FIXTURE_INVALID"):
            self.reader(expected_uid=os.geteuid()+1)
        self.assertFalse((self.directory/"trashpp-archive-v2.sqlite3").exists())

    def test_root_symlink_file_symlink_and_hardlink_refuse(self):
        link=self.directory/"alias"
        link.symlink_to(self.directory,target_is_directory=True)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_UNAVAILABLE"):
            self.reader(root=link)
        other=self.directory/"original.json"
        self.floor_file.rename(other)
        self.floor_file.symlink_to(other)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_UNAVAILABLE"):
            self.reader()
        self.floor_file.unlink()
        other.rename(self.floor_file)
        extra=self.directory/"extra-hardlink.json"
        os.link(self.floor_file,extra)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_FILE_UNSAFE"):
            self.reader()

    def test_group_or_world_writable_files_and_directory_refuse(self):
        self.floor_file.chmod(0o666)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_FILE_UNSAFE"):
            self.reader()
        self.floor_file.chmod(0o600)
        self.directory.chmod(0o777)
        self.addCleanup(self.directory.chmod,0o700)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_ROOT_UNSAFE"):
            self.reader()
        self.directory.chmod(0o700)

    def test_malformed_duplicate_fields_or_noncanonical_wire_refuse(self):
        original=self.floor_file.read_bytes()
        self.floor_file.write_bytes(b" "+original)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_NONCANONICAL"):
            self.reader()
        malicious=original[:-1]+b',"floor":{}}'
        self.floor_file.write_bytes(malicious)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_DUPLICATE_FIELD"):
            self.reader()

    def test_expired_revoked_wrong_owner_or_grant_refuse(self):
        reader=self.reader()
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_EXPIRED"):
            self.verify(reader,now_ms=1760000600001)
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_BINDING_MISMATCH"):
            self.verify(reader,owner_id="weather-events")
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_BINDING_MISMATCH"):
            self.verify(reader,grant_sha256="f"*64)
        self.write_floor(floor=dict(self.floor,revoked=True))
        reader=self.reader()
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_REVOKED"):
            self.verify(reader)

    def test_release_advances_but_file_floor_stale(self):
        reader=self.reader()
        next_release=self.previous.next_release(self.previous.release)
        self.previous.enroll(self.previous.signed(next_release))
        with self.assertRaisesRegex(ExternalFloorRefused,
                                    "EXTERNAL_FLOOR_STALE_OR_CHANGED"):
            self.verify(reader,signed_release=self.previous.signed(next_release))
        self.assertEqual(self.previous.history.status(
            "demo-scrape")["sequence"],2)

    def test_invalid_floor_schema_and_boolean_confusion(self):
        for changes,code in (
            ({"ownerId":"hospital"},"EXTERNAL_FLOOR_FIELDS_INVALID"),
            ({"purpose":"burn"},"EXTERNAL_FLOOR_SCOPE_INVALID"),
            ({"epoch":True},"EXTERNAL_FLOOR_FIELDS_INVALID"),
            ({"sequence":False},"EXTERNAL_FLOOR_FIELDS_INVALID"),
            ({"revoked":"false"},"EXTERNAL_FLOOR_FIELDS_INVALID"),
            ({"validUntilMs":1760200000000},"EXTERNAL_FLOOR_TIME_INVALID"),
            ({"untrustedField":"grant"},"EXTERNAL_FLOOR_SCHEMA_INVALID"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ExternalFloorRefused,code):
                    canonical_floor(dict(self.floor,**changes))

    def test_no_signer_service_archive_or_trash_mutation_path(self):
        from scripts.trash import archive_v2_external_floor_reader as impl
        source=Path(impl.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey", "ArchiveStore(", "Quickshell.dataDir",
            "os.unlink(", "os.remove(", "os.rename(", "os.replace(",
            "CREATE TABLE", ".bind(", ".listen(",
        ):
            self.assertNotIn(forbidden,source)
        self.assertFalse(hasattr(impl,"main"))
        self.assertFalse(hasattr(impl,"serve_forever"))


if __name__=="__main__":
    unittest.main()
