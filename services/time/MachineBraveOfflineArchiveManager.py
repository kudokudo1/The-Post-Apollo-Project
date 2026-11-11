#!/usr/bin/env python3
"""MACHINE // offline, metadata-only management of private sealed archives.

This is an operator-invoked CLI, NOT a Brave native host, service, or
RESTORE channel. Its stdout never includes ciphertext, URLs or passphrases.
A typed terminal confirmation and checksum guard are human-workflow safety,
not authentication of processes owned by the same Unix account.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveOfflineArchive as offline
import MachineBraveSealedVault as vault

MAX_RECORDS = vault.MAX_RECORDS
REFUSED = {"status":"refused","restore_allowed":False,"safe_actions":[]}


class ManagerError(ValueError):
    pass


def refuse():
    raise ManagerError("OFFLINE ARCHIVE MANAGEMENT REFUSED")


@contextmanager
def _repository(*, destination=None):
    # Production CLI never accepts a destination argument; tests may use a
    # temporary fixture. The account data home ignores HOME/XDG_DATA_HOME.
    base = offline._account_data_home() if destination is None else Path(destination)
    if not base.is_absolute():
        refuse()
    offline._owned_directory(base)
    with offline._vault_at(base):
        yield


def _metadata(record_id):
    item = vault.read(vault._id(record_id))
    if (item.get("status") != "sealed_record_read"
            or item.get("restore_allowed") is not False
            or item.get("ciphertext_authentication_verified") is not False):
        refuse()
    record = item["record"]
    if record["record_id"] != record_id:
        refuse()
    return {
        "record_id":record_id,
        "created_at_utc":record["created_at_utc"],
        "sealed_bytes":len(
            (json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()
        ),
        "sha256":item["sha256"],
    }


def _inventory():
    result = vault.listing()  # read-only: does not create a vault
    if result.get("status") != "listed" or result.get("restore_allowed") is not False:
        refuse()
    if result.get("orphan_temp_present"):
        refuse()  # do not treat incomplete writes as healthy records
    rows = result["records"]
    if not isinstance(rows,list) or len(rows)>MAX_RECORDS:
        refuse()
    return rows


def listing(*, destination=None):
    with _repository(destination=destination):
        rows = _inventory()
        return {
            "status":"offline_archive_listed",
            "records":rows,
            "record_count":len(rows),
            "ciphertext_authentication_verified":False,
            "persistent_client_authenticated":False,
            "restore_allowed":False,"safe_actions":[]
        }


def inspect(record_id, *, destination=None):
    record_id = vault._id(record_id)
    with _repository(destination=destination):
        names = {item["record_id"] for item in _inventory()}
        if record_id not in names:
            refuse()
        meta = _metadata(record_id)
        return {
            "status":"offline_archive_inspected",
            "record":meta,
            "ciphertext_authentication_verified":False,
            "persistent_client_authenticated":False,
            "restore_allowed":False,"safe_actions":[]
        }


def _confirm_delete(record_id):
    phrase="DELETE "+record_id
    try:
        with open("/dev/tty","r+",encoding="utf-8") as tty:
            tty.write("MACHINE // PERMANENT ENCRYPTED SNAPSHOT DELETION\n")
            tty.write("This deletes ONE sealed archive record. No undo is available.\n")
            tty.write("It does not delete the old /tmp trial copy, if any.\n")
            tty.write("Type exactly "+phrase+" to confirm once: ")
            tty.flush()
            value=tty.readline(128)
    except (OSError,UnicodeError):
        return False
    return value.rstrip("\r\n")==phrase


def delete(record_id, expected_sha256, *,
           confirmation=_confirm_delete, destination=None):
    record_id=vault._id(record_id)
    if not isinstance(expected_sha256,str) or not vault.DIGEST_RE.fullmatch(expected_sha256):
        refuse()
    with _repository(destination=destination):
        names={item["record_id"] for item in _inventory()}
        if record_id not in names:
            refuse()
        observed=_metadata(record_id)
        if observed["sha256"]!=expected_sha256:
            refuse()
        # No deletion operation or directory creation before this operator
        # confirmation. An unattended stdin pipe cannot satisfy /dev/tty.
        if not confirmation(record_id):
            refuse()
        if record_id not in {entry["record_id"] for entry in _inventory()}:
            refuse()
        # Recheck after potentially long user interaction, then rely on the
        # sealed vault's digest-aware unlink. This is an optimistic stale-
        # record guard, NOT an atomic same-UID adversarial deletion lock.
        after=_metadata(record_id)
        if after != observed:
            refuse()
        response=vault.delete(record_id,expected_sha256)
        if (response.get("status")!="sealed_record_deleted"
                or response.get("restore_allowed") is not False):
            refuse()
        return {
            "status":"offline_archive_record_deleted",
            "record_id":record_id,
            "sha256":expected_sha256,
            "persistent_client_authenticated":False,
            "restore_allowed":False,"safe_actions":[]
        }


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        if args==["list"]:
            response=listing()
        elif len(args)==2 and args[0]=="inspect":
            response=inspect(args[1])
        elif len(args)==3 and args[0]=="delete":
            response=delete(args[1],args[2])
        else:
            refuse()
        print(json.dumps(response,sort_keys=True,separators=(",",":")))
        return 0
    except (ManagerError,offline.ArchiveError,vault.VaultError,
            TypeError,ValueError,KeyError,OSError,OverflowError):
        print(json.dumps(REFUSED,sort_keys=True,separators=(",",":")))
        return 1


if __name__=="__main__":
    sys.exit(main())
