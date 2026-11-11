#!/usr/bin/env python3
"""MACHINE // disposable-only ciphertext receiver, never normal Brave.

Native origin argument is NOT local-process authentication. Writes are limited
to an existing, private and separately registered /tmp Brave trial root.
No browser access, URL decoding, passphrase access or restore commands.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveSealedVault as vault

HOST_NAME = "org.postapollo.machine_brave_save_trial"
HOST_FILE = "MachineBraveSaveHost.py"
REQUEST_KIND = "machine-brave-sealed-save-request-v1"
RESPONSE_KIND = "machine-brave-sealed-save-response-v1"
MAX_MESSAGE = 196608
MAX_RESPONSE = 2048
ROOT_RE = re.compile(r"postapollo-machine-brave-trial-[a-zA-Z0-9_-]{6,}\Z")
ORIGIN_RE = re.compile(r"chrome-extension://[a-p]{32}/\Z")

class SaveHostError(ValueError):
    pass

def refuse():
    raise SaveHostError("SEALED SAVE REFUSED")

def _regular(path, maxbytes, mode=0o600):
    if path.is_symlink():
        refuse()
    try:
        info = path.lstat()
    except OSError:
        refuse()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != mode
            or not 0 < info.st_size <= maxbytes):
        refuse()
    try:
        return path.read_bytes()
    except OSError:
        refuse()

def _directory(path):
    if path.is_symlink():
        refuse()
    try:
        info = path.lstat()
    except OSError:
        refuse()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        refuse()

def _trial_root(origin, host_path=None):
    if not isinstance(origin, str) or not ORIGIN_RE.fullmatch(origin):
        refuse()
    host = Path(__file__ if host_path is None else host_path)
    root = host.parent
    if (root.parent != Path("/tmp") or not ROOT_RE.fullmatch(root.name)
            or root.resolve() != root or host.name != HOST_FILE):
        refuse()
    _directory(root)
    _regular(host, 65536, mode=0o700)
    raw = _regular(root / ".postapollo-machine-trial.json", 1024)
    try:
        marker = vault.strict_json(raw)
        if (set(marker) != {"kind", "trial_id"}
                or marker["kind"] != "machine-brave-disposable-trial-v1"
                or str(uuid.UUID(marker["trial_id"])) != marker["trial_id"]):
            refuse()
    except (KeyError, TypeError, ValueError, AttributeError):
        refuse()
    data_home = root / "vault-data"
    _directory(data_home)
    manifest_dir = root / "xdg-config" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts"
    current = root / "xdg-config"
    _directory(current)
    for part in ("BraveSoftware", "Brave-Browser", "NativeMessagingHosts"):
        current = current / part
        _directory(current)
    if current != manifest_dir:
        refuse()
    manifest = vault.strict_json(_regular(manifest_dir / (HOST_NAME + ".json"), 4096))
    if manifest != {
        "name": HOST_NAME,
        "description": "MACHINE disposable encrypted session writer; no restore",
        "path": str(host),
        "type": "stdio",
        "allowed_origins": [origin],
    }:
        refuse()
    return data_home

def _read_exact(pipe, size):
    parts=[]
    while size:
        part=pipe.read(size)
        if not part:
            refuse()
        parts.append(part)
        size-=len(part)
    return b"".join(parts)

def read_request(pipe):
    header=_read_exact(pipe,4)
    length=struct.unpack("=I",header)[0]
    if not 1 <= length <= MAX_MESSAGE:
        refuse()
    return vault.strict_json(_read_exact(pipe,length))

def _uuid(value):
    if not isinstance(value,str):
        refuse()
    try:
        parsed=uuid.UUID(value)
    except (ValueError,AttributeError):
        refuse()
    if parsed.version != 4 or str(parsed) != value:
        refuse()
    return value

def handle(request, *, origin, writer=vault.put, trial_checker=_trial_root):
    if not isinstance(request, dict) or set(request) != {
            "kind","challenge","operator_save_requested","envelope"}:
        refuse()
    if request["kind"] != REQUEST_KIND or request["operator_save_requested"] is not True:
        refuse()
    challenge=_uuid(request["challenge"])
    # Check local trial before ANY writable operation. The supplied origin
    # is an exact-manifest assertion, not proof against same-UID callers.
    data_home=trial_checker(origin)
    validated=vault.validate_envelope(request["envelope"])
    # The vault only accepts the ciphertext envelope. Never forward URL,
    # profile, tab list, window ID, passphrase, or display text.
    os.environ["XDG_DATA_HOME"]=str(data_home)
    outcome=writer({
        "kind":vault.REQUEST_KIND,
        "operator_save_requested":True,
        "envelope":validated,
    })
    if outcome.get("status") != "sealed_record_saved" or outcome.get("restore_allowed") is not False:
        refuse()
    return {
        "kind":RESPONSE_KIND,"status":"sealed_record_saved",
        "challenge":challenge,"record_id":outcome["record_id"],
        "sha256":outcome["sha256"],
        "ciphertext_authentication_verified":False,
        "origin_authenticated":False,
        "persistent_browser_window_binding_verified":False,
        "restore_allowed":False,"safe_actions":[]
    }

def write_response(pipe, response):
    data=json.dumps(response,sort_keys=True,separators=(",",":")).encode("utf-8")
    if len(data) > MAX_RESPONSE:
        refuse()
    pipe.write(struct.pack("=I",len(data)))
    pipe.write(data)
    pipe.flush()

def main(argv=None, inp=None, out=None):
    args=sys.argv[1:] if argv is None else argv
    inp=sys.stdin.buffer if inp is None else inp
    out=sys.stdout.buffer if out is None else out
    if len(args) != 1 or not ORIGIN_RE.fullmatch(args[0]):
        return 1
    try:
        response=handle(read_request(inp),origin=args[0])
    except (SaveHostError,vault.VaultError,OSError,ValueError,TypeError,KeyError):
        response={"kind":RESPONSE_KIND,"status":"request_rejected",
                  "restore_allowed":False,"safe_actions":[]}
    try:
        write_response(out,response)
    except (SaveHostError,OSError):
        return 1
    return 0 if response["status"]=="sealed_record_saved" else 1

if __name__=="__main__":
    sys.exit(main())
