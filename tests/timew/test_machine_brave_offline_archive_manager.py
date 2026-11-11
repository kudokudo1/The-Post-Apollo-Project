#!/usr/bin/env python3
"""MACHINE archive manager: metadata-only, explicit delete, fail closed."""
import base64
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveOfflineArchiveManager as manager
import MachineBraveOfflineArchive as offline
import MachineBraveSealedVault as vault


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

def envelope(suffix):
    return {
        "kind":vault.ENVELOPE_KIND,"version":1,"algorithm":"AES-256-GCM",
        "kdf":"PBKDF2-HMAC-SHA256","iterations":600000,
        "salt":b64(b"synthetic-salt16"),
        "nonce":b64(b"12-bytes-abc"),
        "aad":vault.AAD,
        "ciphertext":b64(b"synthetic opaque bytes "+suffix+b" nonce and tag"),
    }

def refused(fn,*args,**kwargs):
    try:fn(*args,**kwargs)
    except (manager.ManagerError,vault.VaultError,offline.ArchiveError,
            OSError,ValueError):
        return
    raise AssertionError("unsafe operation succeeded")

with tempfile.TemporaryDirectory(prefix="machine-archive-manager-test-") as root:
    base=Path(root)
    destination=base/"data"
    destination.mkdir(mode=0o700)
    # LIST must not create a missing archive directory.
    empty=manager.listing(destination=destination)
    assert empty["status"]=="offline_archive_listed"
    assert empty["record_count"]==0
    assert empty["records"]==[]
    assert empty["restore_allowed"] is False
    assert not (destination/"post-apollo").exists()
    refused(manager.inspect,"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            destination=destination)
    refused(manager.delete,"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","a"*64,
            destination=destination,confirmation=lambda _id:True)
    assert not (destination/"post-apollo").exists()

    with offline._vault_at(destination):
        a=vault.put({
            "kind":vault.REQUEST_KIND,
            "operator_save_requested":True,"envelope":envelope(b"A")
        })
        b=vault.put({
            "kind":vault.REQUEST_KIND,
            "operator_save_requested":True,"envelope":envelope(b"B")
        })
    archive_dir=destination/"post-apollo/machine/brave-sealed-vault"
    assert stat.S_IMODE(archive_dir.stat().st_mode)==0o700
    paths={z["record_id"]:archive_dir/(z["record_id"]+".json") for z in (a,b)}
    prior={identifier:path.read_bytes() for identifier,path in paths.items()}
    for path in paths.values():assert stat.S_IMODE(path.stat().st_mode)==0o600

    # All public output is opaque metadata, never ciphertext, passphrases or URLs.
    listing=manager.listing(destination=destination)
    assert listing["record_count"]==2
    assert {x["record_id"] for x in listing["records"]}==set(paths)
    assert listing["ciphertext_authentication_verified"] is False
    assert listing["persistent_client_authenticated"] is False
    for record in (a,b):
        item=manager.inspect(record["record_id"],destination=destination)
        assert item["status"]=="offline_archive_inspected"
        assert item["record"]["record_id"]==record["record_id"]
        assert item["record"]["sha256"]==record["sha256"]
        assert item["record"]["sealed_bytes"]>100
        assert item["restore_allowed"] is False
        assert item["safe_actions"]==[]
    serialized=json.dumps([listing,
        manager.inspect(a["record_id"],destination=destination)])
    for secret in ("ciphertext","nonce","salt","password","https://","URL"):
        assert secret not in serialized

    # Wrong SHA and refusal of typed confirmation never alter the record.
    called=[]
    denied=lambda i:(called.append(i),False)[1]
    refused(manager.delete,a["record_id"],"0"*64,
            destination=destination,confirmation=lambda _id:True)
    assert called==[]
    refused(manager.delete,a["record_id"],a["sha256"],
            destination=destination,confirmation=denied)
    assert called==[a["record_id"]]
    assert {k:p.read_bytes() for k,p in paths.items()}==prior
    refused(manager.delete,"../escape",a["sha256"],
            destination=destination,confirmation=lambda _id:True)
    refused(manager.delete,a["record_id"],"invalid-digest",
            destination=destination,confirmation=lambda _id:True)

    # If record changes during human confirmation, recheck prevents deletion.
    def change_after_preview(_record_id):
        path=paths[a["record_id"]]
        changed=json.loads(path.read_bytes())
        changed["envelope"]["ciphertext"]=envelope(b"C")["ciphertext"]
        path.write_text(json.dumps(changed,sort_keys=True,
                                   separators=(",",":"))+"\n")
        return True
    refused(manager.delete,a["record_id"],a["sha256"],
            destination=destination,confirmation=change_after_preview)
    assert paths[a["record_id"]].exists()
    assert paths[b["record_id"]].read_bytes()==prior[b["record_id"]]
    paths[a["record_id"]].write_bytes(prior[a["record_id"]])
    assert paths[a["record_id"]].read_bytes()==prior[a["record_id"]]

    # Invalid private file permissions, symlinks and incomplete orphan writes
    # block listing and deletions. No silent cleanup.
    os.chmod(paths[a["record_id"]],0o644)
    refused(manager.listing,destination=destination)
    os.chmod(paths[a["record_id"]],0o600)
    symlink=archive_dir/"cccccccc-cccc-4ccc-8ccc-cccccccccccc.json"
    symlink.symlink_to(paths[a["record_id"]].name)
    refused(manager.listing,destination=destination)
    symlink.unlink()
    incomplete=archive_dir/".tmp-unfinished"
    incomplete.write_bytes(b"not a completed snapshot")
    refused(manager.listing,destination=destination)
    refused(manager.delete,a["record_id"],a["sha256"],
            destination=destination,confirmation=lambda _id:True)
    assert incomplete.exists()
    incomplete.unlink()
    os.chmod(archive_dir,0o755)
    refused(manager.listing,destination=destination)
    os.chmod(archive_dir,0o700)

    # Existing files cannot be removed without a confirmation, and exactly
    # the selected record disappears on a fully confirmed digest.
    authorized=[]
    def approve(identifier):
        authorized.append(identifier)
        return identifier==a["record_id"]
    deleted=manager.delete(a["record_id"],a["sha256"],
                           destination=destination,confirmation=approve)
    assert deleted["status"]=="offline_archive_record_deleted"
    assert deleted["record_id"]==a["record_id"]
    assert deleted["restore_allowed"] is False
    assert authorized==[a["record_id"]]
    assert not paths[a["record_id"]].exists()
    assert paths[b["record_id"]].read_bytes()==prior[b["record_id"]]
    assert manager.listing(destination=destination)["record_count"]==1
    refused(manager.delete,a["record_id"],a["sha256"],
            destination=destination,confirmation=approve)

    # No valid controlling terminal: the default delete confirmation
    # must refuse and preserve the remaining record.
    with patch("builtins.open",side_effect=OSError("not a tty")):
        refused(manager.delete,b["record_id"],b["sha256"],
                destination=destination)
    assert paths[b["record_id"]].read_bytes()==prior[b["record_id"]]

    # The normal CLI does not accept arbitrary destination arguments and
    # has generic failures. Tests use fixture injection, not real account data.
    for args in (["delete"],["list","/tmp/evil"],
                 ["inspect","../x"],["delete","../x","0"*64]):
        with patch.object(offline,"_account_data_home",return_value=destination):
            rc=manager.main(args)
            assert rc==1
    assert paths[b["record_id"]].read_bytes()==prior[b["record_id"]]
    assert "chrome." not in (ROOT/"services/time/MachineBraveOfflineArchiveManager.py").read_text()
    assert "swaymsg" not in (ROOT/"services/time/MachineBraveOfflineArchiveManager.py").read_text()

print("MACHINE offline archive manager list/inspect/confirm-delete security regression PASS")
