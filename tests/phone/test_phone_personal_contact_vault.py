"""P35: isolated synthetic AES-GCM Personal contact vault security and restart tests.

Never touches ~/.local, the host keyring, Quickshell, iPhone, real contacts,
system D-Bus, CALLS or MESSAGES. Keys exist only in test process memory.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalContactIdentity as identity
import PhonePersonalContactVault as vault

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER_PROFILE = "223e4567-e89b-42d3-a456-426614174000"
MASTER = b"\x01" * 32
WRONG = b"\x02" * 32


def card():
    return {
        "id": PROFILE + ":read-epoch:legacy-row-3",
        "serviceId": "blueferry",
        "deviceProfileId": PROFILE,
        "displayNameInProfile": "Synthetic Only",
        "hasAddressDetails": True,
        "phoneNumbers": ["+15550001001", "+15550001002"],
        "emailAddresses": ["fake@example.invalid"],
        "phoneCount": 2,
        "emailCount": 1,
    }


def seeded_document():
    sample = card()
    linked = identity.link(
        identity.empty_document(), sample, [sample], PROFILE,
        vault.contact_matching_key(MASTER),
        user_confirmed=True, create_id=lambda: uuid.UUID(int=1)
    )
    if linked.get("ok") is not True:
        raise AssertionError("Synthetic link setup failed")
    favorite = identity.edit(linked["document"], linked["localId"], 1,
                             favorite=True, note="TEST PRIVATE NOTE",
                             user_confirmed=True)
    if favorite.get("ok") is not True:
        raise AssertionError("Synthetic note setup failed")
    return favorite["document"]


class PersonalVaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="p35-synthetic-")
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.root = self.parent / vault.ROOT_NAME
        self.first = seeded_document()
        self.assertEqual(self.first["revision"], 2)
        self.assertTrue(identity.valid_document(self.first))

    def write_initial(self):
        linked = deepcopy(self.first)
        linked["revision"] = 1
        return vault.commit(MASTER, PROFILE, self.root, linked,
                            expected_revision=0)

    def write_second(self):
        return vault.commit(MASTER, PROFILE, self.root, self.first,
                            expected_revision=1)

    def sealed_path(self):
        return self.root / vault._filename(MASTER, PROFILE)

    def test_import_and_read_do_not_create_any_directory(self):
        self.assertFalse(self.root.exists())
        self.assertEqual(vault.read(MASTER, PROFILE, self.root),
                         identity.empty_document())
        self.assertFalse(self.root.exists())
        self.assertFalse((self.parent / "appcontrol-favorites.json").exists())

    def test_first_explicit_write_creates_only_ciphertext_and_private_files(self):
        status = self.write_initial()
        self.assertEqual(status, {"ok": True, "status": "SEALED", "revision": 1})
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         sorted([vault.LOCK_NAME, self.sealed_path().name]))
        self.assertEqual(stat.S_IMODE(self.sealed_path().stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.root / vault.LOCK_NAME).stat().st_mode),
                         0o600)
        raw = self.sealed_path().read_bytes()
        self.assertNotIn(b"Synthetic Only", raw)
        self.assertNotIn(b"fake@example.invalid", raw)
        self.assertNotIn(b"+15550001001", raw)
        self.assertNotIn(PROFILE.encode(), raw)
        self.assertNotIn(b"matchProof", raw)
        self.assertNotIn(b"localId", raw)
        parsed = json.loads(raw)
        self.assertEqual(set(parsed), {
            "schema", "version", "algorithm", "nonce", "ciphertext"
        })
        self.assertEqual(parsed["algorithm"], "AES-256-GCM")
        self.assertEqual(len(vault._unbase64(parsed["nonce"], 12, 12)), 12)
        self.assertEqual(vault.read(MASTER, PROFILE, self.root)["revision"], 1)

    def test_restart_recovers_original_note_from_new_python_process_via_stdin_key(self):
        self.write_initial()
        self.write_second()
        test_program = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import PhonePersonalContactVault as v
key = sys.stdin.buffer.read(32)
data = v.read(key, sys.argv[2], Path(sys.argv[3]))
assert data['revision'] == 2
assert data['entries'][0]['note'] == 'TEST PRIVATE NOTE'
assert data['entries'][0]['favorite'] is True
sys.stdout.write('RESTART_RECOVERY_PASS')
"""
        result = subprocess.run(
            [sys.executable, "-c", test_program,
             str(ROOT / "services" / "phone"), PROFILE, str(self.root)],
            input=MASTER, capture_output=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr[:400])
        self.assertEqual(result.stdout, b"RESTART_RECOVERY_PASS")
        self.assertNotIn(b"TEST PRIVATE NOTE", result.stdout)
        self.assertNotIn(MASTER, result.stdout)

    def test_matching_key_is_distinct_and_remains_stable_across_restarts(self):
        match = vault.contact_matching_key(MASTER)
        self.assertEqual(len(match), 32)
        self.assertNotEqual(match, MASTER)
        self.assertNotEqual(match, vault._derive(MASTER, b"aes-gcm"))
        self.assertNotEqual(match, vault._derive(MASTER, b"filename"))
        self.assertEqual(identity.assess(card(), [card()], PROFILE, match)["ok"], True)
        self.assertNotEqual(match, vault.contact_matching_key(WRONG))

    def test_second_write_has_fresh_nonce_and_revision_conflict_fails_closed(self):
        self.write_initial()
        first_raw = self.sealed_path().read_bytes()
        saved = self.write_second()
        self.assertEqual(saved["revision"], 2)
        second_raw = self.sealed_path().read_bytes()
        self.assertNotEqual(json.loads(first_raw)["nonce"],
                            json.loads(second_raw)["nonce"])
        self.assertNotEqual(first_raw, second_raw)
        self.assertEqual(vault.read(MASTER, PROFILE, self.root), self.first)
        with self.assertRaises(vault.VaultRefused):
            vault.commit(MASTER, PROFILE, self.root, self.first,
                         expected_revision=0)
        self.assertEqual(self.sealed_path().read_bytes(), second_raw)

    def test_wrong_key_and_profile_cannot_silently_create_shadow_vault(self):
        self.write_initial()
        existing = self.sealed_path().read_bytes()
        with self.assertRaises(vault.VaultRefused):
            vault.unseal(WRONG, PROFILE, existing)
        with self.assertRaises(vault.VaultRefused):
            vault.unseal(MASTER, OTHER_PROFILE, existing)
        with self.assertRaises(vault.VaultRefused):
            vault.read(WRONG, PROFILE, self.root)
        with self.assertRaises(vault.VaultRefused):
            vault.read(MASTER, OTHER_PROFILE, self.root)
        different = deepcopy(self.first)
        for row in different["entries"]:
            row["profileId"] = OTHER_PROFILE
        different["revision"] = 1
        with self.assertRaises(vault.VaultRefused):
            vault.commit(MASTER, OTHER_PROFILE, self.root, different,
                         expected_revision=0)
        self.assertEqual(self.sealed_path().read_bytes(), existing)

    def test_tamper_and_duplicate_envelope_fields_are_rejected(self):
        self.write_initial()
        raw = self.sealed_path().read_bytes()
        source = json.loads(raw)
        altered = deepcopy(source)
        cipher = altered["ciphertext"]
        altered["ciphertext"] = ("A" if cipher[0] != "A" else "B") + cipher[1:]
        for payload in (
            json.dumps(altered).encode(),
            raw.replace(b'"algorithm":', b'"algorithm":"AES-256-GCM","algorithm":'),
            b'{"schema":"fake","notes":"PLAINTEXT PRIVATE NOTE"}',
            b"",
            b"test raw contact",
        ):
            with self.subTest(payload_type=payload[:12]):
                with self.assertRaises(vault.VaultRefused):
                    vault.unseal(MASTER, PROFILE, payload)
        self.assertEqual(vault.unseal(MASTER, PROFILE, raw)["revision"], 1)

    def test_corrupt_file_cannot_be_overwritten_by_recovery_attempt(self):
        self.write_initial()
        self.sealed_path().write_bytes(b'{"plaintext":"danger"}')
        original = self.sealed_path().read_bytes()
        with self.assertRaises(vault.VaultRefused):
            vault.read(MASTER, PROFILE, self.root)
        with self.assertRaises(vault.VaultRefused):
            self.write_second()
        self.assertEqual(self.sealed_path().read_bytes(), original)

    def test_missing_crypto_library_fails_before_any_write(self):
        with patch.object(vault, "_cryptography",
                          side_effect=vault.VaultRefused("PERSONAL_CONTACT_VAULT_REFUSED")):
            with self.assertRaises(vault.VaultRefused):
                self.write_initial()
        self.assertFalse(self.root.exists())

    def test_failed_atomic_replace_keeps_existing_sealed_file_no_plaintext_temp(self):
        self.write_initial()
        previous = self.sealed_path().read_bytes()
        with patch.object(vault.os, "replace", side_effect=OSError("simulated")):
            with self.assertRaises(vault.VaultRefused):
                self.write_second()
        self.assertEqual(self.sealed_path().read_bytes(), previous)
        self.assertEqual(set(p.name for p in self.root.iterdir()),
                         {self.sealed_path().name, vault.LOCK_NAME})
        self.assertNotIn(b"TEST PRIVATE NOTE", previous)

    def test_symlink_bad_permissions_and_hardlinks_are_refused(self):
        real_root = self.parent / "actual"
        real_root.mkdir(mode=0o700)
        self.root.symlink_to(real_root, target_is_directory=True)
        with self.assertRaises(vault.VaultRefused):
            self.write_initial()
        self.root.unlink()
        self.root.mkdir(mode=0o755)
        with self.assertRaises(vault.VaultRefused):
            self.write_initial()
        self.root.chmod(0o700)
        self.write_initial()
        other = self.parent / "hard-link"
        os.link(self.sealed_path(), other)
        with self.assertRaises(vault.VaultRefused):
            vault.read(MASTER, PROFILE, self.root)
        with self.assertRaises(vault.VaultRefused):
            self.write_second()

    def test_unexpected_orphan_file_fails_closed_without_cleanup(self):
        self.write_initial()
        stray = self.root / ".tmp-preserved-for-manual-recovery"
        stray.write_bytes(b"opaque synthetic artifact")
        with self.assertRaises(vault.VaultRefused):
            vault.read(MASTER, PROFILE, self.root)
        with self.assertRaises(vault.VaultRefused):
            self.write_second()
        self.assertTrue(stray.exists())

    def test_explicit_profile_erase_is_revision_guarded(self):
        self.write_initial()
        with self.assertRaises(vault.VaultRefused):
            vault.erase(MASTER, PROFILE, self.root, expected_revision=1,
                        user_confirmed=False)
        with self.assertRaises(vault.VaultRefused):
            vault.erase(MASTER, PROFILE, self.root, expected_revision=0,
                        user_confirmed=True)
        self.assertTrue(self.sealed_path().exists())
        result = vault.erase(MASTER, PROFILE, self.root, expected_revision=1,
                             user_confirmed=True)
        self.assertEqual(result, {"ok": True, "status": "ERASED"})
        self.assertFalse(self.sealed_path().exists())
        self.assertEqual(vault.read(MASTER, PROFILE, self.root),
                         identity.empty_document())

    def test_invalid_profile_key_or_cross_profile_document_never_write(self):
        for key in ("secret", b"short", bytearray(MASTER), b"\x00" * 31):
            with self.subTest(k=type(key).__name__):
                with self.assertRaises(vault.VaultRefused):
                    vault.commit(key, PROFILE, self.root, deepcopy(self.first),
                                 expected_revision=1)
        invalid = deepcopy(self.first)
        invalid["entries"][0]["profileId"] = OTHER_PROFILE
        invalid["revision"] = 1
        with self.assertRaises(vault.VaultRefused):
            vault.commit(MASTER, PROFILE, self.root, invalid,
                         expected_revision=0)
        self.assertFalse(self.root.exists())

    def test_no_production_keyring_host_or_public_cli_wired(self):
        source = (ROOT / "services/phone/PhonePersonalContactVault.py").read_text()
        for forbidden in (
            "if __name__ ==", "def main(", "subprocess", "secret-tool",
            "keyring.get_password", "os.environ", "DBus", "Quickshell",
            "PhoneContactDetail", "PhonePane", "FileView", "Qt.openUrlExternally",
            "os.system(", "print(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("AESGCM(", source)
        self.assertIn("os.fsync(", source)
        self.assertIn("os.replace(", source)
        self.assertIn("fcntl.flock(", source)


if __name__ == "__main__":
    unittest.main()
