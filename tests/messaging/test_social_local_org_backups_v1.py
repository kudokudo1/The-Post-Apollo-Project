"""Seven owner-local organization labels: secure backup only, no restore."""
from __future__ import annotations
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/social"))
import SocialLocalOrgBackup as backups


class PrivateOrganizationBackups(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fake-org-backup-")
        self.previous = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = self.temp.name

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = self.previous
        self.temp.cleanup()

    def test_create_list_verify_private_and_no_credentials(self):
        self.assertEqual(backups.list_backups()["backups"], [])
        created = backups.make_backup()
        name = created["backup"]
        self.assertRegex(name, backups.FILENAME.pattern)
        self.assertFalse(created["restored"])
        self.assertEqual(len(created["inventory"]), 7)
        self.assertEqual(backups.list_backups()["backups"], [name])
        folder = backups.folder(create=False)
        self.assertIsNotNone(folder)
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
        path = folder / name
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        inspected = backups.verify(name)
        self.assertTrue(inspected["valid"])
        self.assertFalse(inspected["restoreAvailable"])
        self.assertEqual(set(inspected["inventory"]),
                         {key for key, _, _, _ in backups.SOURCES})
        manifest = backups.read_backup(name)
        self.assertEqual(manifest["schema"], backups.SCHEMA)
        self.assertNotIn("identity-account-details-v1", path.read_text())
        self.assertNotIn("accessToken", path.read_text())
        for item in inspected["inventory"].values():
            self.assertEqual(item["revision"], 0)
            self.assertEqual(item["records"], 0)

    def test_bad_filename_tamper_schema_missing_document_duplicate_keys(self):
        name = backups.make_backup()["backup"]
        for attack in ("../" + name, "/etc/passwd", "", "other.json", name + "/x"):
            with self.assertRaises(backups.BackupError):
                backups.verify(attack)
        target = backups.folder(create=False) / name
        original = target.read_bytes()
        bundle = json.loads(original)
        bundle["documents"]["directory"]["revision"] = 1
        target.write_text(json.dumps(bundle))
        with self.assertRaisesRegex(backups.BackupError, "CHECKSUM_MISMATCH"):
            backups.verify(name)
        bundle = json.loads(original)
        bundle["schema"] = "post-apollo.unknown.v99"
        target.write_text(json.dumps(bundle))
        with self.assertRaisesRegex(backups.BackupError, "INVALID_BACKUP"):
            backups.verify(name)
        bundle = json.loads(original)
        del bundle["documents"]["reporting"]
        target.write_text(json.dumps(bundle))
        with self.assertRaisesRegex(backups.BackupError, "INCOMPLETE_BACKUP"):
            backups.verify(name)
        target.write_text('{"schema":1,"schema":2}\n')
        with self.assertRaisesRegex(backups.BackupError, "INVALID_JSON"):
            backups.verify(name)

    def test_symlinks_world_readable_files_and_writer_lock_refused(self):
        name = backups.make_backup()["backup"]
        target = backups.folder(create=False) / name
        os.chmod(target, 0o644)
        with self.assertRaises(Exception):
            backups.verify(name)
        os.chmod(target, 0o600)
        target.unlink()
        target.symlink_to(Path(self.temp.name) / "not-a-backup")
        with self.assertRaises(Exception):
            backups.verify(name)
        root = backups.root_path()
        lock = root / ".local-organizations.lock"
        import fcntl
        fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(backups.BackupError, "STORES_BUSY"):
                backups.make_backup()
        finally:
            os.close(fd)

    def test_no_restore_writer(self):
        source = (ROOT / "services/social/SocialLocalOrgBackup.py").read_text()
        ui = (ROOT / "widgets/messanger/IdentityCenterLocalOrgBackup.qml").read_text()
        self.assertNotIn('args == ["restore"]', source)
        self.assertNotIn("module.save(", source)
        self.assertNotIn("os.replace(", source)
        self.assertIn('label: "RESTORE // LOCKED"', ui)
        self.assertIn("interactive: false", ui.split(
            'label: "RESTORE // LOCKED"')[1][:100])
        for label in ('"BACK UP NOW"', '"LIST BACKUPS"',
                      '"VALIDATE FOR RESTORE"'):
            self.assertIn(label, ui)


if __name__ == "__main__":
    unittest.main()
