#!/usr/bin/env python3
"""MACHINE offline sealed archive: confirmed, no-host, no-plaintext transfer."""
from contextlib import contextmanager
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineBraveOfflineArchive as archive
import MachineBraveSealedVault as vault
from MachineBraveDisposableTrial import init_trial, register_trial
from MachineBraveFocusTrial import register_focus
from MachineBraveTitleTrial import register as register_title
from MachineBraveSaveTrial import register as register_save
from MachineBraveReadTrial import register as register_read

EXT = "a"*32
created = []

def b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def envelope(tag=b"A"):
    return {
        "kind": vault.ENVELOPE_KIND, "version": 1,
        "algorithm": "AES-256-GCM",
        "kdf": "PBKDF2-HMAC-SHA256", "iterations": 600000,
        "salt": b64(b"random-salt-1234"), "nonce": b64(b"12-byte-nonce"),
        "aad": vault.AAD,
        "ciphertext": b64(b"synthetic ciphertext " + tag + b" fake-gcm-tag"),
    }

@contextmanager
def scoped_home(path):
    before = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = str(path)
    try:
        yield
    finally:
        if before is None: os.environ.pop("XDG_DATA_HOME", None)
        else: os.environ["XDG_DATA_HOME"] = before

def setup():
    root = Path(init_trial()["trial_root"])
    created.append(root)
    assert root.parent == Path("/tmp")
    register_trial(str(root), EXT)
    register_focus(str(root), EXT)
    register_title(str(root), EXT)
    register_save(str(root), EXT)
    register_read(str(root), EXT)
    return root

def refused(call, *args, **kwargs):
    try: call(*args, **kwargs)
    except (archive.ArchiveError, vault.VaultError, ValueError, OSError): return
    raise AssertionError("Expected fail-closed archive refusal")

try:
    trial = setup()
    with tempfile.TemporaryDirectory(prefix="machine-archive-durable-fixture-") as temporary:
        base = Path(temporary)
        original_xdg = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = "/tmp/UNTRUSTED-ATTACKER-DATA"
        source_base = trial / "vault-data"
        with scoped_home(source_base):
            source_saved = vault.put({
                "kind": vault.REQUEST_KIND,
                "operator_save_requested": True,
                "envelope": envelope(),
            })
        key = source_saved["record_id"]
        expected = source_saved["sha256"]
        source_path = source_base / "post-apollo/machine/brave-sealed-vault" / (key + ".json")
        source_before = source_path.read_bytes()
        assert source_path.stat().st_mode & 0o777 == 0o600

        preview = archive.inspect(str(trial), key)
        assert preview["status"] == "offline_archive_preflight"
        assert preview["source_sha256"] == expected
        assert preview["encrypted_only"] is True
        assert preview["archived"] is False
        assert preview["restore_allowed"] is False
        assert preview["safe_actions"] == []
        assert base.iterdir() is not None
        assert not (base / "post-apollo").exists()
        assert not Path("/tmp/UNTRUSTED-ATTACKER-DATA").exists()

        # Refused consent, wrong digest and unknown records must NOT write.
        called = []
        def deny(record_id):
            called.append(record_id)
            return False
        refused(archive.archive,str(trial),key,expected,
                confirmation=deny,destination=base)
        assert called == [key]
        refused(archive.archive,str(trial),key,"0"*64,
                confirmation=lambda _id: True,destination=base)
        refused(archive.archive,str(trial),"../escape",expected,
                confirmation=lambda _id: True,destination=base)
        refused(archive.archive,str(trial),
                "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",expected,
                confirmation=lambda _id: True,destination=base)
        assert not (base / "post-apollo").exists()

        # First explicit consent atomically publishes ONE ciphertext record.
        recorded = []
        def approve(record_id):
            recorded.append(record_id)
            return record_id == key
        first = archive.archive(str(trial),key,expected,
                                confirmation=approve,destination=base)
        assert first["status"] == "offline_sealed_record_archived"
        assert recorded == [key]
        assert first["archive_record_id"] != key
        assert first["restore_allowed"] is False
        assert first["ciphertext_authentication_verified"] is False
        assert first["persistent_origin_authenticated"] is False
        archive_root = base / "post-apollo/machine/brave-sealed-vault"
        entries = list(archive_root.glob("*.json"))
        assert len(entries) == 1
        assert entries[0].name == first["archive_record_id"] + ".json"
        for folder in [base/"post-apollo",base/"post-apollo"/"machine",archive_root]:
            assert stat.S_IMODE(folder.stat().st_mode)==0o700
        assert stat.S_IMODE(entries[0].stat().st_mode)==0o600
        text = entries[0].read_text()
        assert "https://" not in text
        assert "passphrase" not in text
        assert "restore_allowed" not in text
        assert json.loads(text)["envelope"] == envelope()
        assert source_path.read_bytes() == source_before
        assert os.environ.get("XDG_DATA_HOME") == "/tmp/UNTRUSTED-ATTACKER-DATA"

        # Exact same cipher envelope must not create a duplicate record.
        again = archive.archive(str(trial),key,expected,
                                confirmation=approve,destination=base)
        assert again["status"] == "already_archived"
        assert again["archive_record_id"] == first["archive_record_id"]
        assert len(list(archive_root.glob("*.json"))) == 1

        # Refuse an unsafe destination mode without chmod or overwrite.
        os.chmod(archive_root, 0o755)
        original_file = entries[0].read_bytes()
        refused(archive.archive,str(trial),key,expected,
                confirmation=approve,destination=base)
        assert entries[0].read_bytes() == original_file
        os.chmod(archive_root, 0o700)

        # An interrupted publish never removes existing ciphertext.
        with scoped_home(source_base):
            second = vault.put({
                "kind": vault.REQUEST_KIND,
                "operator_save_requested": True,
                "envelope": envelope(tag=b"B"),
            })
        with patch.object(vault.os, "link", side_effect=OSError("injected link failure")):
            refused(archive.archive,str(trial),second["record_id"],
                    second["sha256"],confirmation=lambda _id: True,destination=base)
        assert entries[0].read_bytes() == original_file
        assert not list(archive_root.glob(".tmp-*"))

        # A source file symlink or hardlink is refused.
        source_two = source_path.parent / (second["record_id"] + ".json")
        before_two = source_two.read_bytes()
        source_two.unlink()
        source_two.symlink_to(source_path.name)
        refused(archive.inspect,str(trial),second["record_id"])
        source_two.unlink()
        source_two.write_bytes(before_two)
        os.chmod(source_two,0o600)
        hard = source_path.parent / "hard.json"
        os.link(source_two,hard)
        refused(archive.inspect,str(trial),second["record_id"])
        hard.unlink()

        # Simulated incomplete source write blocks import. Never auto-clean it.
        orphan = source_path.parent / ".tmp-unfinished"
        orphan.write_bytes(b"unfinished")
        refused(archive.inspect,str(trial),key)
        assert orphan.exists()
        orphan.unlink()

        # Importing source with different content but stale digest is refused.
        with scoped_home(source_base):
            third = vault.put({
                "kind": vault.REQUEST_KIND, "operator_save_requested":True,
                "envelope":envelope(tag=b"C")
            })
        refused(archive.archive,str(trial),third["record_id"],expected,
                confirmation=approve,destination=base)
        assert len(list(archive_root.glob("*.json"))) == 1

        # No browser/native host imports or any new global host registration.
        source = (ROOT / "services/time/MachineBraveOfflineArchive.py").read_text()
        assert "chrome." not in source
        assert "swaymsg" not in source
        assert "MachineBraveReadTrial" in source
        assert "/dev/tty" in source
        assert 'if not confirmation(record_id):' in source
        assert "os.environ[\"XDG_DATA_HOME\"]" in source
        assert os.environ.get("XDG_DATA_HOME")=="/tmp/UNTRUSTED-ATTACKER-DATA"
        if original_xdg is None: os.environ.pop("XDG_DATA_HOME", None)
        else: os.environ["XDG_DATA_HOME"] = original_xdg
finally:
    for directory in created:
        assert directory.parent == Path("/tmp")
        assert directory.name.startswith("postapollo-machine-brave-trial-")
        shutil.rmtree(directory)

print("MACHINE offline encrypted archive: consent, integrity, dedup, isolation, rollback PASS")
