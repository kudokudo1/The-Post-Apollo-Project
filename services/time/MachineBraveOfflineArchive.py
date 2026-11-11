#!/usr/bin/env python3
"""MACHINE // operator-confirmed offline archive of ALREADY SEALED Brave records.

This is deliberately NOT a native messaging host or a background service.
It never accepts a plaintext URL or passphrase, never launches Brave, and
cannot restore a session. A tty confirmation is an operator workflow gate,
NOT authentication against a malicious same-UID local process.

Only an exact record in a verified disposable trial may be promoted into
the existing ciphertext-only vault at the account's fixed data directory.
No XDG_DATA_HOME override is honored for the destination in the CLI.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import pwd
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveReadTrial import verify as verify_trial_read
from MachineBraveDisposableTrial import TrialError
import MachineBraveSealedVault as vault

MAX_SOURCE_RECORDS = 32
REFUSAL = {"status": "refused", "restore_allowed": False, "safe_actions": []}


class ArchiveError(ValueError):
    pass


def refuse():
    raise ArchiveError("OFFLINE SEALED ARCHIVE REFUSED")


def _owned_directory(path, *, private=False):
    if path.is_symlink():
        refuse()
    try:
        info = path.lstat()
    except OSError:
        refuse()
    if (not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or (info.st_mode & (0o077 if private else 0o022))):
        refuse()


def _account_data_home():
    """Ignore HOME/XDG overrides, do not create or chmod parent folders."""
    try:
        user_home = Path(pwd.getpwuid(os.geteuid()).pw_dir).resolve(strict=True)
    except (KeyError, OSError, RuntimeError):
        refuse()
    _owned_directory(user_home)
    local = user_home / ".local"
    base = local / "share"
    _owned_directory(local)
    _owned_directory(base)
    return base


@contextmanager
def _vault_at(base):
    # This process is single-use CLI. Restore the environment after every
    # call to avoid leaking a temporary trial destination into later actions.
    previous = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = str(base)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = previous


def _sealed_source(trial_root, record_id):
    """Read verified disposable ciphertext by exact UUID, not arbitrary path."""
    if not isinstance(trial_root, str):
        refuse()
    record_id = vault._id(record_id)
    verified = verify_trial_read(trial_root)
    if verified.get("status") != "disposable_sealed_read_registration_verified":
        refuse()
    root = Path(verified["trial_root"])
    data = root / "vault-data"
    source = data / "post-apollo" / "machine" / "brave-sealed-vault"
    for component in (data, data / "post-apollo",
                      data / "post-apollo" / "machine", source):
        _owned_directory(component, private=True)
    names, orphan = vault._files(source)
    if orphan or len(names) > MAX_SOURCE_RECORDS or record_id not in names:
        refuse()
    fd = vault._dir_fd(source)
    try:
        raw = vault._safe_open_file(fd, record_id + ".json")
    finally:
        os.close(fd)
    entry = vault._record(raw, record_id)
    if entry.get("kind") != vault.RECORD_KIND:
        refuse()
    return {
        "record_id": record_id,
        "sha256": vault._digest(raw),
        "envelope": vault.validate_envelope(entry["envelope"]),
        "sealed_bytes": len(raw)
    }


def inspect(trial_root, record_id):
    record = _sealed_source(trial_root, record_id)
    return {
        "status": "offline_archive_preflight",
        "source_record_id": record["record_id"],
        "source_sha256": record["sha256"],
        "sealed_bytes": record["sealed_bytes"],
        "encrypted_only": True,
        "ciphertext_authentication_verified": False,
        "persistent_origin_authenticated": False,
        "archived": False,
        "restore_allowed": False,
        "safe_actions": []
    }


def _tty_confirm(record_id):
    """Manual consent gate. Not a cryptographic client-identity proof."""
    challenge = "ARCHIVE " + record_id
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            tty.write("MACHINE // OFFLINE SEALED ARCHIVE\n")
            tty.write("This copies ciphertext to the account data vault.\n")
            tty.write("It does not verify the password or enable RESTORE.\n")
            tty.write("Type exactly " + challenge + " to authorize once: ")
            tty.flush()
            answer = tty.readline(128)
    except (OSError, UnicodeError):
        return False
    return answer.rstrip("\r\n") == challenge


def archive(trial_root, record_id, expected_sha256, *,
            confirmation=_tty_confirm, destination=None):
    if not isinstance(expected_sha256, str) or not vault.DIGEST_RE.fullmatch(expected_sha256):
        refuse()
    original = _sealed_source(trial_root, record_id)
    if original["sha256"] != expected_sha256:
        refuse()
    # Confirmation happens before ANY destination directory creation.
    if not confirmation(record_id):
        refuse()
    # Re-read after the potentially long human-confirmation window.
    latest = _sealed_source(trial_root, record_id)
    if latest["sha256"] != expected_sha256 or latest["envelope"] != original["envelope"]:
        refuse()
    base = _account_data_home() if destination is None else Path(destination)
    if not base.is_absolute():
        refuse()
    _owned_directory(base)
    # A fixed destination is selected from the current account by the CLI,
    # not from XDG_DATA_HOME, a native-message request, or trial metadata.
    old_mask = os.umask(0o077)
    try:
        with _vault_at(base):
            listing = vault.listing()    # does not create directories
            if listing.get("status") != "listed" or listing.get("orphan_temp_present"):
                refuse()
            for item in listing["records"]:
                existing = vault.read(item["record_id"])
                if existing["record"]["envelope"] == latest["envelope"]:
                    return {
                        "status": "already_archived",
                        "source_record_id": record_id,
                        "archive_record_id": item["record_id"],
                        "ciphertext_authentication_verified": False,
                        "persistent_origin_authenticated": False,
                        "restore_allowed": False,
                        "safe_actions": []
                    }
            saved = vault.put({
                "kind": vault.REQUEST_KIND,
                "operator_save_requested": True,
                "envelope": latest["envelope"]
            })
            # After publication, verify the new exact ID/envelope. Never
            # delete a possible published record on an uncertain read.
            observed = vault.read(saved["record_id"])
            if (observed["status"] != "sealed_record_read"
                    or observed["sha256"] != saved["sha256"]
                    or observed["record"]["envelope"] != latest["envelope"]):
                refuse()
            return {
                "status": "offline_sealed_record_archived",
                "source_record_id": record_id,
                "archive_record_id": saved["record_id"],
                "archive_sha256": saved["sha256"],
                "ciphertext_authentication_verified": False,
                "persistent_origin_authenticated": False,
                "restore_allowed": False,
                "safe_actions": []
            }
    finally:
        os.umask(old_mask)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 3 and args[0] == "inspect":
            result = inspect(args[1], args[2])
        elif len(args) == 4 and args[0] == "archive":
            result = archive(args[1], args[2], args[3])
        else:
            refuse()
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (ArchiveError, TrialError, vault.VaultError,
            ValueError, KeyError, TypeError, OSError, OverflowError):
        # No raw input, URL, ciphertext, passphrase or arbitrary filesystem
        # path in failure responses. A failed archive may be uncertain if
        # the final fsync/read failed; inspect listing before retrying.
        print(json.dumps(REFUSAL, sort_keys=True, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    sys.exit(main())
