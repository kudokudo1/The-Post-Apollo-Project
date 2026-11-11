#!/usr/bin/env python3
"""MACHINE disposable native sealed-save host: end-to-end framed safety."""
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
from MachineBraveDisposableTrial import init_trial,register_trial,TrialError
from MachineBraveFocusTrial import register_focus
from MachineBraveTitleTrial import register as register_title
from MachineBraveSaveTrial import (
    register as register_save,verify as verify_save,HOST_FILE,MANIFEST,MODULES
)
import MachineBraveSaveTrial as installer
from MachineBraveSaveHost import REQUEST_KIND,RESPONSE_KIND,HOST_NAME

EXT="a"*32
ORIGIN="chrome-extension://"+EXT+"/"
created=[]

def new_trial():
    root=Path(init_trial()["trial_root"])
    assert root.parent==Path("/tmp")
    created.append(root)
    register_trial(str(root),EXT)
    register_focus(str(root),EXT)
    register_title(str(root),EXT)
    return root

def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def envelope():
    return {
        "kind":"machine-brave-sealed-session-v1",
        "version":1,"algorithm":"AES-256-GCM",
        "kdf":"PBKDF2-HMAC-SHA256","iterations":600000,
        "salt":b64(b"salt-synthetic!!"),"nonce":b64(b"nonce-12byte"),
        "aad":"machine-brave-sealed-session-v1",
        "ciphertext":b64(b"synthetic ciphertext bytes plus tag"),
    }

def request():
    return {
        "kind":REQUEST_KIND,
        "operator_save_requested":True,
        "challenge":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "envelope":envelope(),
    }

def frame(o):
    raw=json.dumps(o).encode()
    return struct.pack("=I",len(raw))+raw

def send(root,payload,origin=ORIGIN,environment=None):
    env=dict(os.environ)
    env["XDG_DATA_HOME"]="/tmp/THIS-ENV-MUST-BE-IGNORED"
    if environment:env.update(environment)
    proc=subprocess.run(
        [sys.executable,"-B","-I",str(root/HOST_FILE),origin],
        input=payload,capture_output=True,env=env,timeout=10
    )
    assert len(proc.stdout)>=4
    size=struct.unpack("=I",proc.stdout[:4])[0]
    assert len(proc.stdout)-4==size
    assert not proc.stderr
    return proc.returncode,json.loads(proc.stdout[4:])

def refused(fn,*args):
    try:fn(*args)
    except (TrialError,OSError,ValueError):return
    raise AssertionError("UNSAFE REGISTRATION ACCEPTED")

try:
    root=new_trial()
    original_names={
        p.name:p.read_bytes()
        for p in root.iterdir() if p.is_file()
    }
    registration=register_save(str(root),EXT)
    assert registration["status"]=="disposable_sealed_save_registration_verified"
    assert registration["exact_extension_id"]==EXT
    assert registration["restore_allowed"] is False
    assert registration["origin_authenticated"] is False
    assert verify_save(str(root))==registration
    assert stat.S_IMODE((root/"vault-data").stat().st_mode)==0o700
    for name in MODULES:
        file=root/name
        assert stat.S_IMODE(file.stat().st_mode)==(
            0o700 if name==HOST_FILE else 0o600)
    manifest=(root/"xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts"/MANIFEST)
    assert json.loads(manifest.read_text())["allowed_origins"]==[ORIGIN]
    assert stat.S_IMODE(manifest.stat().st_mode)==0o600
    assert {name:(root/name).read_bytes() for name in original_names}==original_names
    refused(register_save,str(root),EXT)
    refused(register_save,str(root),"b"*32)
    refused(register_save,str(Path.home()),EXT)

    data=root/"vault-data/post-apollo"
    # Bad request never reaches even the first subdirectory.
    for payload in [
        dict(request(),url="https://private.example/token"),
        dict(request(),operator_save_requested=False),
        dict(request(),passphrase="NEVER SEND THIS"),
        {**request(),"envelope":{**envelope(),"url":"https://SECRET"}},
        dict(request(),kind="machine-brave-restore-request"),
        dict(request(),challenge="bad"),
    ]:
        code,result=send(root,frame(payload))
        assert code!=0 and result["status"]=="request_rejected"
        assert result["restore_allowed"] is False
        assert not data.exists()
    code,result=send(root,struct.pack("=I",200000))
    assert code!=0 and result["status"]=="request_rejected"
    assert not data.exists()

    code,result=send(root,frame(request()))
    assert code==0 and result["status"]=="sealed_record_saved"
    assert result["challenge"]==request()["challenge"]
    assert result["kind"]==RESPONSE_KIND
    assert result["restore_allowed"] is False
    assert result["origin_authenticated"] is False
    assert result["ciphertext_authentication_verified"] is False
    assert result["safe_actions"]==[]
    records=list((data/"machine/brave-sealed-vault").glob("*.json"))
    assert len(records)==1
    assert records[0].stat().st_mode & 0o777==0o600
    obj=json.loads(records[0].read_text())
    assert obj["envelope"]==envelope()
    assert "passphrase" not in records[0].read_text()
    assert "https://" not in records[0].read_text()
    assert "restore" not in obj
    assert not Path("/tmp/THIS-ENV-MUST-BE-IGNORED").exists()

    # Wrong extension caller argument must not reach disk.
    code,result=send(root,frame(request()),origin="chrome-extension://"+"b"*32+"/")
    assert code!=0 and result["status"]=="request_rejected"
    assert len(list((data/"machine/brave-sealed-vault").glob("*.json")))==1

    # If the host registration manifest is tampered, fail closed.
    before=manifest.read_bytes()
    manifest.write_text("{}")
    code,result=send(root,frame(request()))
    assert code!=0 and result["status"]=="request_rejected"
    manifest.write_bytes(before)

    # New trial: failed manifest write removes only this attempt's new files.
    broken=new_trial()
    orig=installer._write_exclusive
    def fail_manifest(path,content,mode):
        if path.name==MANIFEST:raise OSError("injected failure")
        return orig(path,content,mode)
    try:
        installer._write_exclusive=fail_manifest
        refused(register_save,str(broken),EXT)
    finally:
        installer._write_exclusive=orig
    assert not (broken/HOST_FILE).exists()
    assert not (broken/"MachineBraveSealedVault.py").exists()
    assert not (broken/"vault-data").exists()
    assert not (broken/"xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts"/MANIFEST).exists()

    # Symlink collision cannot overwrite or delete a foreign resource.
    symlink_trial=new_trial()
    link=symlink_trial/HOST_FILE
    link.symlink_to("/etc/passwd")
    refused(register_save,str(symlink_trial),EXT)
    assert link.is_symlink()
    assert not (symlink_trial/"vault-data").exists()
finally:
    for path in created:
        assert path.parent==Path("/tmp")
        assert path.name.startswith("postapollo-machine-brave-trial-")
        shutil.rmtree(path)

print("MACHINE sealed save native trial // exact origin, ciphertext-only, rollback PASS")
