#!/usr/bin/env python3
"""MACHINE // opt-in isolated save host registration for an EXISTING trial.

No global native host, no normal XDG config, no browser launch or profile
edit. Requires already verified disposable transport/focus/title hosts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from MachineBraveDisposableTrial import (
    TrialError,_validate_root,_existing_manifest_dir,_read_regular,
    _write_exclusive,_private_dir
)
from MachineBraveTitleTrial import verify as verify_title
from MachineBraveSaveHost import HOST_NAME,HOST_FILE

MODULES=(HOST_FILE,"MachineBraveSealedVault.py")
MANIFEST=HOST_NAME+".json"
MAX_SOURCE=65536

def manifest(extension_id,host):
    return {
        "name":HOST_NAME,
        "description":"MACHINE disposable encrypted session writer; no restore",
        "path":str(host),"type":"stdio",
        "allowed_origins":["chrome-extension://"+extension_id+"/"]
    }

def _source(module):
    if module not in MODULES:
        raise TrialError("UNKNOWN SOURCE")
    data=Path(__file__).resolve().with_name(module).read_bytes()
    if not data.startswith(b"#!/usr/bin/env python3\n") or len(data)>MAX_SOURCE:
        raise TrialError("BAD SOURCE")
    return data

def verify(root_path):
    root=_validate_root(root_path)
    title=verify_title(str(root))
    if title["status"]!="disposable_title_marker_registration_verified":
        raise TrialError("TITLE HOST UNVERIFIED")
    data_home=root/"vault-data"
    _private_dir(data_home)
    for name in MODULES:
        path=root/name
        data=_read_regular(path,MAX_SOURCE)
        if data!=_source(name) or stat.S_IMODE(path.stat().st_mode)!=(
                0o700 if name==HOST_FILE else 0o600):
            raise TrialError("SAVE SOURCE MISMATCH")
    reg=_existing_manifest_dir(root)/MANIFEST
    if stat.S_IMODE(reg.stat().st_mode)!=0o600:
        raise TrialError("SAVE MANIFEST MODE")
    record=json.loads(_read_regular(reg,4096))
    if record!=manifest(title["exact_extension_id"],root/HOST_FILE):
        raise TrialError("SAVE MANIFEST MISMATCH")
    return {
        "status":"disposable_sealed_save_registration_verified",
        "trial_root":str(root),
        "exact_extension_id":title["exact_extension_id"],
        "vault_scoped_to_disposable_trial":True,
        "origin_authenticated":False,
        "ciphertext_authentication_verified":False,
        "restore_allowed":False,"safe_actions":[]
    }

def register(root_path,extension_id):
    root=_validate_root(root_path)
    title=verify_title(str(root))
    if title["exact_extension_id"]!=extension_id:
        raise TrialError("EXTENSION ID MISMATCH")
    save_manifest=_existing_manifest_dir(root)/MANIFEST
    files={root/name:_source(name) for name in MODULES}
    files[save_manifest]=(json.dumps(
        manifest(extension_id,root/HOST_FILE),
        sort_keys=True,indent=2)+"\n").encode()
    data_home=root/"vault-data"
    if data_home.exists() or data_home.is_symlink():
        raise TrialError("SAVE DATA HOME EXISTS")
    for path in files:
        if path.exists() or path.is_symlink():
            raise TrialError("SAVE REGISTRATION EXISTS")
    created=[]
    dir_created=False
    try:
        data_home.mkdir(mode=0o700)
        dir_created=True
        _private_dir(data_home)
        for path,content in files.items():
            _write_exclusive(path,content,
                            0o700 if path.name==HOST_FILE else 0o600)
            created.append(path)
        return verify(str(root))
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        # Only remove an empty directory created by this invocation.
        if dir_created:
            data_home.rmdir()
        raise

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        if len(args)==3 and args[0]=="register":
            result=register(args[1],args[2])
        elif len(args)==2 and args[0]=="verify":
            result=verify(args[1])
        else:
            return 2
    except (TrialError,OSError,ValueError,TypeError):
        print('{"status":"refused","safe_actions":[]}')
        return 1
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
