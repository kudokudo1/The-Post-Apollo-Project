# M11U SYNTHETIC HOST ONLY
"""M11w child, disposable sealed-script and sealed-M11l-owner test protocol.

No production source path; cannot open tasks outside an existing private
m11l-tasks-copy/todo-copy.json. No production task writer or FileView.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import secrets
import sys
import types

MAX_MODULE = 131072
SEALS = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW
         | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)


def emit(item):
    sys.stdout.write(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_REQUEST_KEY")
        result[key] = value
    return result


def run():
    if len(sys.argv) != 4 or sys.argv[3] not in ("NEW", "EXISTING"):
        return 2
    folder = Path(sys.argv[1])
    # Refuse arbitrary paths, including any actual TASKS file.
    if (not folder.is_absolute() or folder.name != "m11l-tasks-copy"
            or ".." in folder.parts):
        return 2
    try:
        fd = int(sys.argv[2])
        if fd < 3 or fcntl.fcntl(fd, fcntl.F_GET_SEALS) & SEALS != SEALS:
            return 2
        os.lseek(fd, 0, os.SEEK_SET)
        source = os.read(fd, MAX_MODULE + 1)
        if len(source) < 1024 or len(source) > MAX_MODULE:
            return 2
        owner_module = types.ModuleType("m11w_sealed_disposable_owner")
        # Only the sealed FD supplied by the test launcher can provide code.
        exec(compile(source, "<m11w-sealed-disposable-owner>", "exec"),
             owner_module.__dict__)
        session = secrets.token_hex(24)
        writer = "m11w-" + session
        with owner_module.CandidateOwner(folder, writer,
              bootstrap=(sys.argv[3] == "NEW")) as owner:
            state = owner.state()
            emit({"protocol": 1, "kind": "hello", "sessionId": session,
                  "phase": state["phase"], "epoch": state["epoch"],
                  "status": "SYNTHETIC_OWNER_ATTACHED"})
            previous_request = 0
            while previous_request < 3:
                line = sys.stdin.buffer.readline(4097)
                if not line or len(line) > 4096 or not line.endswith(b"\n"):
                    return 2
                try:
                    request = json.loads(line.decode("utf-8"),
                                         object_pairs_hook=unique)
                    if type(request) is not dict or set(request) != {
                            "protocol", "kind", "sessionId", "requestId",
                            "epoch", "challenge"}:
                        return 2
                    number = request["requestId"]
                    if (request["protocol"] != 1 or type(number) is not int
                            or number != previous_request + 1
                            or type(request["sessionId"]) is not str
                            or not secrets.compare_digest(
                                request["sessionId"], session)
                            or type(request["epoch"]) is not int
                            or request["epoch"] != state["epoch"]
                            or type(request["challenge"]) is not str
                            or len(request["challenge"]) != 48
                            or any(c not in "0123456789abcdef"
                                   for c in request["challenge"])
                            or request["kind"] not in ("status", "reserve")):
                        emit({"protocol": 1, "kind": "refused",
                              "status": "STALE_OR_INVALID_SESSION"})
                        return 2
                    previous_request = number
                    if request["kind"] == "reserve":
                        # Only the deterministic synthetic one-task seed is
                        # eligible. Do not read or mutate any actual tasks.
                        data = owner_module.source_bytes(
                            folder / "todo-copy.json")
                        document = owner_module.parse_task_document(data)
                        if (len(document["tasks"]) != 1
                                or document["tasks"][0]["title"]
                                != "M11W_TEST_0"):
                            return 2
                        document["tasks"][0]["title"] = "M11W_TEST_1"
                        document["tasks"][0]["updatedAtMs"] += 1
                        candidate = (json.dumps(document, indent=2) + "\n"
                                     ).encode("utf-8")
                        stage = "m11w-stage-" + secrets.token_hex(20)
                        try:
                            owner.reserve(stage, candidate)
                        except owner_module.GateError:
                            emit({"protocol": 1, "kind": "refused",
                                  "status": "RECOVERY_REVIEW_REQUIRED",
                                  "sessionId": session,
                                  "requestId": number})
                            continue
                    state = owner.state()
                    emit({"protocol": 1, "kind": "reply",
                          "status": "SYNTHETIC_ONLY", "sessionId": session,
                          "requestId": number, "epoch": state["epoch"],
                          "phase": state["phase"],
                          "pending": state["pending"],
                          "challenge": request["challenge"]})
                except (ValueError, TypeError, KeyError,
                        owner_module.GateError):
                    return 2
            return 0
    except (OSError, ValueError, TypeError, Exception):
        # No source path, data, session or stage leaked in diagnostics.
        return 2


if __name__ == "__main__":
    sys.exit(run())
