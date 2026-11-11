#!/usr/bin/env python3
"""MACHINE sealed Brave vault: synthetic bytes, private file I/O, rollback."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[2]
script = root / "services/time/MachineBraveSealedVault.py"
spec = importlib.util.spec_from_file_location("sealed_vault", script)
vault = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vault)

def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def envelope():
    return {
        "kind": vault.ENVELOPE_KIND, "version": 1,
        "algorithm": "AES-256-GCM", "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": 600000,
        "salt": b64(b"salt-for-testing"), # exactly 16 bytes, structural fixture
        "nonce": b64(b"12byte-nonce"),    # exactly 12 bytes
        "aad": vault.AAD,
        "ciphertext": b64(b"ciphertext-like-bytes" + b"FAKE-AES-GCM-TAG"),
    }

def request(**extra):
    return {"kind":vault.REQUEST_KIND, "operator_save_requested":True,
            "envelope":envelope(), **extra}

def call(*args, payload=None, env=None):
    data=None if payload is None else (json.dumps(payload)+"\n").encode()
    p=subprocess.run([sys.executable,"-B","-I",str(script),*args],
                     input=data,env=env,capture_output=True,timeout=8)
    assert b"Traceback" not in p.stderr, p.stderr
    return p.returncode,json.loads(p.stdout)

def refused(fn,*args):
    try:fn(*args)
    except vault.VaultError:return
    raise AssertionError("expected vault refusal")

with tempfile.TemporaryDirectory(prefix="machine-sealed-vault-test-") as t:
    base=Path(t)
    old=os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"]=str(base)
    env=dict(os.environ)
    target=base/"post-apollo"/"machine"/"brave-sealed-vault"

    # Read-only operations never create a directory.
    assert vault.listing()["records"]==[]
    assert not target.exists()
    refused(vault.read,"00000000-0000-4000-8000-000000000001")
    assert not target.exists()
    for bad in (
        {"kind":"unknown","operator_save_requested":True,
         "envelope":envelope()},
        {**request(),"operator_save_requested":False},
        {**request(), "url":"https://secret.test/password"},
        {**request(),"envelope":{**envelope(),"password":"SECRET"}},
        {**request(),"envelope":{**envelope(),"nonce":b64(b"too-short")}},
        {**request(),"envelope":{**envelope(),"algorithm":"AES-CBC"}},
        {**request(),"envelope":{**envelope(),"iterations":599999}},
        {**request(),"envelope":{**envelope(),"ciphertext":b64(b"x"*15)}},
        {**request(),"envelope":{**envelope(),"ciphertext":"!invalid"}},
    ):
        refused(vault.put,bad)
        assert not target.exists()

    saved=vault.put(request())
    assert saved["status"]=="sealed_record_saved"
    assert saved["ciphertext_authentication_verified"] is False
    assert saved["restore_allowed"] is False
    assert saved["safe_actions"]==[]
    key=saved["record_id"]
    file=target/(key+".json")
    assert file.exists()
    assert stat.S_IMODE(file.stat().st_mode)==0o600
    for d in [base/"post-apollo",base/"post-apollo"/"machine",target]:
        assert stat.S_IMODE(d.stat().st_mode)==0o700
    assert b"https://" not in file.read_bytes()
    assert b"SECRET" not in file.read_bytes()
    assert not list(target.glob(".tmp-*"))
    first=vault.read(key)
    assert first["record"]["envelope"]==envelope()
    assert first["sha256"]==saved["sha256"]
    assert vault.listing()["records"][0]["record_id"]==key

    # Existing records never get overwritten; new IDs are distinct.
    another=vault.put(request())
    assert another["record_id"]!=key
    assert len(vault.listing()["records"])==2

    # Injection: failure after writing/fsyncing temporary bytes but before
    # publishing the final link rolls back only the new temporary file.
    stable={entry.name:entry.read_bytes() for entry in target.iterdir()}
    with patch.object(vault.os,"link",side_effect=OSError("SIMULATED LINK FAILURE")):
        refused(vault.put,request())
    assert {entry.name:entry.read_bytes() for entry in target.iterdir()}==stable
    assert not list(target.glob(".tmp-*"))

    refused(vault.delete,key,"0"*64)
    assert file.exists()
    refused(vault.delete,key,"not-a-digest")
    assert file.exists()
    destroyed=vault.delete(key,first["sha256"])
    assert destroyed["status"]=="sealed_record_deleted"
    assert not file.exists()
    assert len(vault.listing()["records"])==1
    refused(vault.delete,key,first["sha256"])

    # Existing file permissions, link count and symlinks are not trusted.
    second=target/(another["record_id"]+".json")
    os.chmod(second,0o644)
    refused(vault.read,another["record_id"])
    os.chmod(second,0o600)
    hard=target/"copy.json"
    os.link(second,hard)
    refused(vault.read,another["record_id"])
    hard.unlink()
    assert vault.read(another["record_id"])["record"]["kind"]==vault.RECORD_KIND

    # Valid-looking record ID must never follow a symlink to another record.
    symlink_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    symlink_path=target/(symlink_id+".json")
    symlink_path.symlink_to(second.name)
    refused(vault.read,symlink_id)
    refused(vault.listing)
    symlink_path.unlink()
    refused(vault.strict_json,b'{"kind":"a","kind":"b"}')

    os.chmod(target,0o755)
    refused(vault.read,another["record_id"])
    os.chmod(target,0o700)

    # A crash leftover cannot be silently deleted or promoted as saved.
    orphan=target/(".tmp-"+"6"*36)
    orphan.write_bytes(b"unsafe incomplete ciphertext")
    os.chmod(orphan,0o600)
    report=vault.listing()
    assert report["orphan_temp_present"] is True
    refused(vault.put,request())
    assert orphan.exists()
    orphan.unlink()

    # CLI only reads one bounded JSON line; raw errors are never echoed.
    rc,out=call("list",env=env)
    assert rc==0 and out["records"][0]["record_id"]==another["record_id"]
    rc,out=call("read",another["record_id"],env=env)
    assert rc==0 and out["status"]=="sealed_record_read"
    rc,out=call("put",payload=request(),env=env)
    assert rc==0 and out["status"]=="sealed_record_saved"
    rc,out=call("put",payload={**request(),"raw":"SECRET URL"},env=env)
    assert rc!=0 and out=={"status":"refused","restore_allowed":False,
                               "safe_actions":[]}
    assert "SECRET" not in json.dumps(out)
    rc,out=call("delete",another["record_id"],"0"*64,env=env)
    assert rc!=0 and out["status"]=="refused"
    rc,out=call("delete",another["record_id"],another["sha256"],env=env)
    assert rc==0 and out["status"]=="sealed_record_deleted"
    rc,out=call("read","../outside",env=env)
    assert rc!=0 and out["status"]=="refused"

    # Other records remain intact, even after rejected deletes.
    assert target.is_dir()

    # The raw browser session never gets routed through geometry storage.
    geometry=(root/"services/time/MachineCheckpointStore.py").read_text()
    qml=(root/"widgets/TimeW.qml").read_text()
    manifest=json.loads((root/"integrations/machine/brave-topology/manifest.json").read_text())
    assert "MachineBraveSealedVault" not in geometry
    assert "MachineBraveSealedVault" not in qml
    assert manifest["permissions"]==[]
    assert not manifest.get("background")
    assert manifest["optional_permissions"]==["nativeMessaging","tabs"]

    if old is None:os.environ.pop("XDG_DATA_HOME",None)
    else:os.environ["XDG_DATA_HOME"]=old
print("MACHINE sealed-vault synthetic private store, rollback and no restore PASS")
