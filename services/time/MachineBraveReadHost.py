#!/usr/bin/env python3
"""MACHINE // disposable-only encrypted snapshot read-back native host.

A separate read-only authority from the write host. It never receives a
passphrase or plaintext URL, has no Sway/restore functions and cannot create
vault storage. Chromium's origin argv is NOT authenticated against other
same-UID local processes, so registration remains limited to marked /tmp trials.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveSaveHost as save
import MachineBraveSealedVault as vault

HOST_NAME = "org.postapollo.machine_brave_read_trial"
HOST_FILE = "MachineBraveReadHost.py"
REQUEST_KIND = "machine-brave-sealed-read-request-v1"
RESPONSE_KIND = "machine-brave-sealed-read-response-v1"
MAX_INPUT = 4096
MAX_OUTPUT = 196608

class ReadHostError(ValueError):
    pass

def refuse():
    raise ReadHostError("SEALED READ REFUSED")

def _trial_root(origin):
    root = Path(__file__).parent
    # Reuse all prior disposable trial, source, and exact-origin save-host
    # verification instead of authorizing a new normal profile path.
    data_home = save._trial_root(origin, host_path=str(root / save.HOST_FILE))
    save._regular(root / HOST_FILE, 65536, mode=0o700)
    manifest_dir = root / "xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    target = manifest_dir / (HOST_NAME + ".json")
    manifest = vault.strict_json(save._regular(target, 4096))
    if manifest != {
        "name": HOST_NAME,
        "description": "MACHINE disposable encrypted snapshot read-only review; no restore",
        "path": str(root / HOST_FILE),
        "type": "stdio",
        "allowed_origins": [origin]
    }:
        refuse()
    return data_home

def _read_exact(pipe, count):
    parts = []
    while count:
        part = pipe.read(count)
        if not part:
            refuse()
        parts.append(part)
        count -= len(part)
    return b"".join(parts)

def read_request(pipe):
    (length,) = struct.unpack("=I", _read_exact(pipe, 4))
    if not 1 <= length <= MAX_INPUT:
        refuse()
    return vault.strict_json(_read_exact(pipe, length))

def handle(request, *, origin, checker=_trial_root, reader=vault.read):
    vault.exact_keys(request, ("kind","challenge","record_id","operator_read_requested"))
    if request["kind"] != REQUEST_KIND or request["operator_read_requested"] is not True:
        refuse()
    challenge = save._uuid(request["challenge"])
    record_id = vault._id(request["record_id"])
    # Never use ambient XDG_DATA_HOME or any caller-supplied path.
    data_home = checker(origin)
    os.environ["XDG_DATA_HOME"] = str(data_home)
    observed = reader(record_id)
    if observed.get("status") != "sealed_record_read" or observed.get("restore_allowed") is not False:
        refuse()
    record = observed["record"]
    if record.get("record_id") != record_id:
        refuse()
    envelope = vault.validate_envelope(record["envelope"])
    return {
        "kind":RESPONSE_KIND, "status":"sealed_record_read",
        "challenge":challenge, "record_id":record_id,
        "sha256":observed["sha256"], "envelope":envelope,
        "ciphertext_authentication_verified":False,
        "origin_authenticated":False,
        "persistent_browser_window_binding_verified":False,
        "restore_allowed":False, "safe_actions":[]
    }

def write_response(pipe, value):
    data = json.dumps(value, separators=(",",":"), sort_keys=True).encode("utf-8")
    if not 1 <= len(data) <= MAX_OUTPUT:
        refuse()
    pipe.write(struct.pack("=I",len(data)))
    pipe.write(data)
    pipe.flush()

def main(argv=None, inp=None, out=None):
    args = sys.argv[1:] if argv is None else argv
    inp = sys.stdin.buffer if inp is None else inp
    out = sys.stdout.buffer if out is None else out
    if len(args) != 1 or not save.ORIGIN_RE.fullmatch(args[0]):
        return 1
    try:
        reply = handle(read_request(inp), origin=args[0])
    except (ReadHostError,save.SaveHostError,vault.VaultError,
            TypeError,ValueError,KeyError,OSError):
        reply = {"kind":RESPONSE_KIND,"status":"request_rejected",
                 "restore_allowed":False,"safe_actions":[]}
    try:
        write_response(out,reply)
    except (ReadHostError,OSError):
        return 1
    return 0 if reply.get("status") == "sealed_record_read" else 1

if __name__ == "__main__":
    sys.exit(main())
