#!/usr/bin/env python3
"""M4t2 disposable persistent bridge; not a production Banking entrypoint."""
import json
import os
from pathlib import Path
import sys
import uuid

import banking_manual_store as manual
import banking_revision_client_candidate as client

PREFIX = "FINANCEW_BANKING_CLIENT "
MAX_FRAME = 530000
MAX_SEQUENCE = 1000000

def emit(stream, value):
    raw = json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    if len(raw) > MAX_FRAME:
        raise manual.Refusal("BRIDGE_OUTPUT_LIMIT")
    stream.write(PREFIX + raw + "\n")
    stream.flush()

def serve(directory, source, sink):
    generation = uuid.uuid4().hex
    with client.revision_client(directory) as live:
        emit(sink, {"kind":"ready","generation":generation,"sequence":0,
                    "document":live.snapshot()})
        sequence = 0
        while True:
            raw = source.readline(MAX_FRAME + 1)
            if not raw:
                return # EOF destroys the client and releases its lease
            if len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
                raise manual.Refusal("BRIDGE_FRAME")
            req = manual.decode(raw)
            if type(req) is not dict:
                raise manual.Refusal("BRIDGE_REQUEST")
            action = req.get("action")
            keys = ("generation","sequence","action","expectedRevision")
            if action == "save":
                keys += ("session","confirm")
            elif action == "clear":
                keys += ("confirm",)
            elif action not in ("refresh","close"):
                raise manual.Refusal("BRIDGE_ACTION")
            if (not manual.exact(req, keys)
                    or req["generation"] != generation
                    or type(req["sequence"]) is not int
                    or req["sequence"] != sequence + 1
                    or req["sequence"] > MAX_SEQUENCE
                    or type(req["expectedRevision"]) is not int
                    or req["expectedRevision"] != live.snapshot()["revision"]):
                raise manual.Refusal("BRIDGE_STALE_REQUEST")
            sequence = req["sequence"]
            reply = {"kind":"result","generation":generation,"sequence":sequence,
                     "action":action}
            if action == "close":
                # No later commands; caller must await actual child exit.
                emit(sink, reply)
                return
            if action == "save":
                doc = live.save(req["expectedRevision"],req["session"],confirm=req["confirm"])
            elif action == "clear":
                doc = live.clear(req["expectedRevision"],confirm=req["confirm"])
            else:
                doc = live.refresh()
            emit(sink, {**reply,"document":doc})

def main():
    # A CI-only entrypoint. The fixture supplies a new isolated XDG root.
    # This marker is an accidental-use guard, not an authenticated boundary.
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("POST_APOLLO_BANKING_M4T2") != "CI_DISPOSABLE_ONLY"):
        raise manual.Refusal("DISPOSABLE_ONLY")
    root = os.environ.get("XDG_DATA_HOME","")
    if not root or not Path(root).is_absolute():
        raise manual.Refusal("DISPOSABLE_ROOT_REQUIRED")
    serve(manual.store_dir(), sys.stdin.buffer, sys.stdout)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # No raw ledger, request, traceback or environment in diagnostics.
        print("FINANCEW_BANKING_CLIENT_REFUSED",file=sys.stderr)
        raise SystemExit(1)
