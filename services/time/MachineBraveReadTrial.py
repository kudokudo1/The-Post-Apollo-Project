#!/usr/bin/env python3
"""MACHINE // opt-in separate read-only host for a verified disposable trial.

Requires existing sealed save host and all its prior transport/focus/title
dependencies. No global registration, no production vault, no overwrite.
"""
from __future__ import annotations
import json
from pathlib import Path
import stat
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from MachineBraveDisposableTrial import (
    TrialError,_validate_root,_existing_manifest_dir,_read_regular,_write_exclusive
)
from MachineBraveSaveTrial import verify as verify_save
from MachineBraveReadHost import HOST_NAME,HOST_FILE

MANIFEST = HOST_NAME+".json"
MAX_SOURCE = 65536

def _source():
    data = Path(__file__).resolve().with_name(HOST_FILE).read_bytes()
    if not data.startswith(b"#!/usr/bin/env python3\n") or not 1 <= len(data) <= MAX_SOURCE:
        raise TrialError("BAD READ SOURCE")
    return data

def manifest(extension_id,host):
    return {
        "name":HOST_NAME,
        "description":"MACHINE disposable encrypted snapshot read-only review; no restore",
        "path":str(host),"type":"stdio",
        "allowed_origins":["chrome-extension://"+extension_id+"/"]
    }

def verify(root_path):
    root = _validate_root(root_path)
    prior = verify_save(str(root))
    if prior["status"] != "disposable_sealed_save_registration_verified":
        raise TrialError("SAVE HOST NOT VERIFIED")
    host = root/HOST_FILE
    if (_read_regular(host,MAX_SOURCE) != _source()
        or stat.S_IMODE(host.stat().st_mode) != 0o700):
        raise TrialError("READ HOST MISMATCH")
    path = _existing_manifest_dir(root)/MANIFEST
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise TrialError("READ MANIFEST MODE")
    if json.loads(_read_regular(path,4096)) != manifest(
            prior["exact_extension_id"],host):
        raise TrialError("READ MANIFEST MISMATCH")
    return {
        "status":"disposable_sealed_read_registration_verified",
        "trial_root":str(root),
        "exact_extension_id":prior["exact_extension_id"],
        "read_only":True,
        "vault_scoped_to_disposable_trial":True,
        "origin_authenticated":False,
        "ciphertext_authentication_verified":False,
        "restore_allowed":False,"safe_actions":[]
    }

def register(root_path,extension_id):
    root = _validate_root(root_path)
    prior = verify_save(str(root))
    if extension_id != prior["exact_extension_id"]:
        raise TrialError("EXTENSION ID MISMATCH")
    host = root/HOST_FILE
    target = _existing_manifest_dir(root)/MANIFEST
    if host.exists() or host.is_symlink() or target.exists() or target.is_symlink():
        raise TrialError("READ HOST ALREADY REGISTERED")
    created = []
    try:
        _write_exclusive(host,_source(),0o700)
        created.append(host)
        _write_exclusive(
            target,(json.dumps(manifest(extension_id,host),
                               sort_keys=True,indent=2)+"\n").encode(),0o600)
        created.append(target)
        return verify(str(root))
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise

def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 3 and args[0] == "register":
            result = register(args[1],args[2])
        elif len(args) == 2 and args[0] == "verify":
            result = verify(args[1])
        else:
            return 2
    except (TrialError,ValueError,TypeError,OSError):
        print('{"status":"refused","safe_actions":[]}')
        return 1
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
