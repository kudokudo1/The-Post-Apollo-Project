#!/usr/bin/env python3
"""MACHINE migration preflight: read-only source snapshot, stale digest refusal.

Only isolated temporary ciphertext fixtures; no actual operator archive,
privileged account, ownership migration, listener or browser operations.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveProtectedArchivePreflight as preflight
import MachineBraveOfflineArchive as offline
import MachineBraveOfflineArchiveManager as manager
import MachineBraveSealedVault as vault


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def envelope(mark):
    return {
        "kind":vault.ENVELOPE_KIND,
        "version":1,
        "algorithm":"AES-256-GCM",
        "kdf":"PBKDF2-HMAC-SHA256",
        "iterations":600000,
        "salt":b64(b"0123456789abcdef"),
        "nonce":b64(b"0123456789ab"),
        "aad":vault.AAD,
        "ciphertext":b64(b"opaque synthetic ciphertext "+mark+b" tag bytes"),
    }


def put(base,mark):
    with offline._vault_at(base):
        return vault.put({
            "kind":vault.REQUEST_KIND,
            "operator_save_requested":True,
            "envelope":envelope(mark),
        })


def refused(fn,*args,**kwargs):
    try:
        fn(*args,**kwargs)
    except (preflight.PreflightRefusal,vault.VaultError,
            manager.ManagerError,offline.ArchiveError,ValueError,OSError):
        return
    raise AssertionError("unsafe protected migration plan was accepted")


def verify_output(result):
    assert result["read_only"] is True
    assert result["source_ciphertext_authentication_verified"] is False
    assert result["distinct_service_uid_installed"] is False
    assert result["protected_destination_inspected"] is False
    assert result["independent_backup_verified"] is False
    assert result["client_authenticated"] is False
    assert result["operator_consent_verified"] is False
    assert result["migration_authorized"] is False
    assert result["restore_allowed"] is False
    assert result["safe_actions"]==[]
    output=json.dumps(result)
    for forbidden in ('"ciphertext":','"salt":','"nonce":',
                      '"envelope":','"passphrase":',
                      "https://","opaque synthetic ciphertext"):
        assert forbidden not in output,forbidden


with tempfile.TemporaryDirectory(prefix="machine-protected-migration-preflight-") as root:
    area=Path(root)
    base=area/"data"
    base.mkdir(mode=0o700)

    # A read-only plan must not manufacture a new archive at all.
    before=set(area.iterdir())
    empty=preflight.plan(source_base=base)
    verify_output(empty)
    assert empty["inventory"]["source_state"]=="absent"
    assert empty["inventory"]["record_count"]==0
    assert empty["inventory"]["records"]==[]
    assert empty["inventory"]["total_sealed_bytes"]==0
    assert set(area.iterdir())==before
    assert not (base/"post-apollo").exists()
    assert preflight.recheck(empty["inventory_sha256"],source_base=base)[
        "status"]=="offline_migration_inventory_unchanged"

    first=put(base,b"first")
    second=put(base,b"second")
    root_dir=base/"post-apollo/machine/brave-sealed-vault"
    paths={r["record_id"]:root_dir/(r["record_id"]+".json")
           for r in (first,second)}
    bytes_before={rid:path.read_bytes() for rid,path in paths.items()}
    modes_before={rid:path.stat().st_mode for rid,path in paths.items()}
    dirs_before={p.name for p in root_dir.iterdir()}

    checkpoint=preflight.plan(source_base=base)
    verify_output(checkpoint)
    assert checkpoint["status"]=="offline_migration_inventory_preflight"
    inventory=checkpoint["inventory"]
    assert inventory["kind"]==preflight.PLAN_KIND
    assert inventory["source_state"]=="present"
    assert inventory["record_count"]==2
    assert inventory["total_sealed_bytes"]==sum(
        len(data) for data in bytes_before.values())
    assert [r["record_id"] for r in inventory["records"]]==sorted(paths)
    assert {r["sha256"] for r in inventory["records"]}=={
        first["sha256"],second["sha256"]}
    assert checkpoint["inventory_sha256"]==preflight._fingerprint(inventory)
    unchanged=preflight.recheck(checkpoint["inventory_sha256"],source_base=base)
    assert unchanged["status"]=="offline_migration_inventory_unchanged"
    assert unchanged["inventory_sha256"]==checkpoint["inventory_sha256"]
    assert unchanged["migration_authorized"] is False
    assert preflight.plan(source_base=base)==checkpoint
    assert {rid:path.read_bytes() for rid,path in paths.items()}==bytes_before
    assert {rid:path.stat().st_mode for rid,path in paths.items()}==modes_before
    assert {p.name for p in root_dir.iterdir()}==dirs_before

    # Forged stale/wrong digest or malformed CLI path cannot approve transfer.
    refused(preflight.recheck,"0"*64,source_base=base)
    for invalid in ("INVALID","../x","",None,True,0):
        refused(preflight.recheck,invalid,source_base=base)
    assert preflight.main(["plan",str(base)])==1
    assert preflight.main(["migrate"])==1
    assert preflight.main(["copy","/tmp/source","/tmp/target"])==1
    assert preflight.main(["recheck","0"*64,"/tmp/target"])==1

    # If contents change after planning, require a new plan, not implicit
    # migration. Plan does not remove or change earlier snapshots.
    third=put(base,b"third")
    refused(preflight.recheck,checkpoint["inventory_sha256"],source_base=base)
    assert {rid:path.read_bytes() for rid,path in paths.items()}==bytes_before
    third_path=root_dir/(third["record_id"]+".json")
    third_path.unlink()
    assert preflight.recheck(checkpoint["inventory_sha256"],source_base=base)[
        "status"]=="offline_migration_inventory_unchanged"

    # A malformed/unsafe inventory must fail, never silently skip records.
    sample=paths[first["record_id"]]
    sample.chmod(0o644)
    refused(preflight.plan,source_base=base)
    sample.chmod(0o600)
    assert preflight.plan(source_base=base)==checkpoint
    link=root_dir/"cccccccc-cccc-4ccc-8ccc-cccccccccccc.json"
    link.symlink_to(sample.name)
    refused(preflight.plan,source_base=base)
    assert link.is_symlink()
    link.unlink()
    # A real extra hardlink invalidates nlink==1 on the existing record.
    os.link(sample,link)
    refused(preflight.plan,source_base=base)
    link.unlink()
    orphan=root_dir/".tmp-incomplete"
    orphan.write_bytes(b"partial")
    refused(preflight.plan,source_base=base)
    assert orphan.exists()
    orphan.unlink()
    root_dir.chmod(0o755)
    refused(preflight.plan,source_base=base)
    root_dir.chmod(0o700)
    assert preflight.plan(source_base=base)==checkpoint

    # Repeated inventory reads must agree: a moving source cannot be
    # accepted as a stable checkpoint. No filesystem mutation required.
    good_rows=inventory["records"]
    with patch.object(manager,"_inventory",side_effect=[
            good_rows,good_rows[:-1]]):
        refused(preflight.plan,source_base=base)

    # Normal operator CLI uses passwd effective-account home, not HOME or
    # XDG_DATA_HOME, even if a malicious process supplies those variables.
    account=area/"account"
    account.mkdir(mode=0o700)
    (account/".local").mkdir(mode=0o700)
    share=account/".local"/"share"
    share.mkdir(mode=0o700)
    account_first=put(share,b"account")
    with patch.object(offline.pwd,"getpwuid",
                      return_value=SimpleNamespace(pw_dir=str(account))):
        with patch.dict(os.environ,{
            "HOME":"/tmp/MACHINE-UNTRUSTED-HOME",
            "XDG_DATA_HOME":"/tmp/MACHINE-UNTRUSTED-DATA"
        }):
            from_cli=preflight.plan()
            assert from_cli["inventory"]["record_count"]==1
            assert from_cli["inventory"]["records"][0]["record_id"]==account_first["record_id"]
            assert preflight.recheck(from_cli["inventory_sha256"])[
                "status"]=="offline_migration_inventory_unchanged"
    assert not Path("/tmp/MACHINE-UNTRUSTED-DATA").exists()
    assert not Path("/tmp/MACHINE-UNTRUSTED-HOME").exists()

    # A read-only snapshot is not privileged deployment or evidence of
    # authentication, consent, off-machine backup or installed protected UID.
    source=(ROOT/"services/time/MachineBraveProtectedArchivePreflight.py").read_text()
    assert "vault.put(" not in source
    assert "vault.delete(" not in source
    assert "os.chown(" not in source
    assert "subprocess." not in source
    assert "migration_authorized" in source
    assert "False" in source

print("MACHINE protected archive migration preflight: stable read-only inventory, source drift, unsafe files and no migration PASS")
