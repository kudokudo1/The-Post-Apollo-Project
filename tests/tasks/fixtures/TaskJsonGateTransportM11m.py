#!/usr/bin/env python3
"""M11m isolated JSON-lines host for a disposable TASKS copy.

NOT A PRODUCTION WRITER. No default directory, task file bootstrap, app
registration, network, external commands, migration or production authority.
The existing M11l OS-owning test fixture validates the directory and source.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import secrets
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HOST_FILE = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
spec = importlib.util.spec_from_file_location("task_gate_candidate_m11l", HOST_FILE)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)

MAX_REQUESTS = 50
MAX_LINE = candidate.MAX_BYTES * 3 + 4096
MAX_CANDIDATE = candidate.MAX_BYTES


def unique(pairs):
    obj = {}
    for name, value in pairs:
        if name in obj:
            raise ValueError("DUPLICATE_REQUEST_KEY")
        obj[name] = value
    return obj


def response(rid, kind, ok, status, owner=None, *, stage=None, session_id=None):
    snap = owner.state() if owner is not None else None
    return {
        "protocol": 1, "requestId": rid, "kind": kind,
        "sessionId": session_id,
        "ok": bool(ok), "status": status,
        "phase": snap["phase"] if snap else "UNVERIFIED",
        "epoch": snap["epoch"] if snap else None,
        "pending": snap["pending"] if snap else False,
        "stageId": stage,
        "liveWriterAuthorized": False, "sqliteWriteAuthorized": False,
        "migrationAuthorized": False, "remoteWriteAuthorized": False
    }


def emit(stream, item):
    stream.write(json.dumps(item, separators=(",", ":"), ensure_ascii=True) + "\n")
    stream.flush()


def serve(directory: Path, writer_id: str, *, bootstrap=False, incoming=None,
          outgoing=None):
    source = incoming if incoming is not None else sys.stdin.buffer
    sink = outgoing if outgoing is not None else sys.stdout
    try:
        with candidate.CandidateOwner(directory, writer_id, bootstrap=bootstrap) as owner:
            session_id = secrets.token_hex(24)
            def reply(rid, kind, ok, status, *, stage=None):
                return response(rid, kind, ok, status, owner, stage=stage,
                                session_id=session_id)
            emit(sink, reply(0, "hello", True, "TEST_OWNER_ATTACHED"))
            last_request = 0
            active = None
            for _ in range(MAX_REQUESTS):
                line = source.readline(MAX_LINE + 1)
                if not line:
                    return 0
                if len(line) > MAX_LINE or not line.endswith(b"\n"):
                    emit(sink, reply(None, "protocol", False,
                                     "INVALID_REQUEST_FRAME"))
                    return 2
                try:
                    req = json.loads(line.decode("utf-8"), object_pairs_hook=unique)
                    if type(req) is not dict:
                        raise ValueError("NOT_OBJECT")
                    rid, kind = req.get("requestId"), req.get("kind")
                    if (type(rid) is not int or rid <= last_request
                            or rid > MAX_REQUESTS or type(kind) is not str):
                        raise ValueError("REPLAY_OR_INVALID_REQUEST")
                    shapes = {
                        "status": {"requestId", "kind"},
                        "reserve": {"requestId", "kind", "stageId", "candidateText"},
                        "verify": {"requestId", "kind", "stageId", "expectedEpoch"},
                        "fail": {"requestId", "kind", "stageId"},
                        "freeze": {"requestId", "kind", "expectedEpoch"}
                    }
                    if kind not in shapes or set(req) != shapes[kind] | {"sessionId"}:
                        raise ValueError("UNSUPPORTED_REQUEST")
                    if (type(req["sessionId"]) is not str or
                            not secrets.compare_digest(req["sessionId"], session_id)):
                        raise ValueError("STALE_OR_INVALID_SESSION")
                    last_request = rid
                    stage = None
                    if kind == "reserve":
                        if active is not None:
                            raise ValueError("PENDING_STAGE")
                        text = req["candidateText"]
                        if (type(text) is not str or not text or
                                len(text.encode("utf-8")) > MAX_CANDIDATE):
                            raise ValueError("INVALID_CANDIDATE_TEXT")
                        data = text.encode("utf-8")
                        candidate.parse_task_document(data)
                        reservation = owner.reserve(req["stageId"], data)
                        active = {
                            "id": req["stageId"],
                            "epoch": reservation["epoch"],
                            "hash": hashlib.sha256(data).hexdigest()
                        }
                        stage = active["id"]
                    elif kind == "verify":
                        if (active is None or req["stageId"] != active["id"]
                                or type(req["expectedEpoch"]) is not int
                                or req["expectedEpoch"] != active["epoch"]):
                            raise ValueError("STALE_STAGE")
                        owner.verify(active["id"], active["epoch"])
                        stage = active["id"]
                        active = None
                    elif kind == "fail":
                        if active is None or req["stageId"] != active["id"]:
                            raise ValueError("STALE_STAGE")
                        # No pretend settlement after a failed FileView save:
                        # persist pending stage for fresh-owner recovery review.
                        emit(sink, reply(rid, kind, False,
                                         "FILEVIEW_FAILURE_REVIEW"))
                        return 2
                    elif kind == "freeze":
                        if (active is not None
                                or type(req["expectedEpoch"]) is not int):
                            raise ValueError("DRAIN_REQUIRED")
                        owner.freeze(req["expectedEpoch"])
                    emit(sink, reply(rid, kind, True, "TEST_ONLY", stage=stage))
                except (ValueError, TypeError, candidate.GateError):
                    # Malformed/stale/mismatched traffic is a closed session.
                    # Do not disclose user-supplied contents in diagnostics.
                    emit(sink, reply(last_request, "refused", False,
                                     "RECOVERY_REVIEW_REQUIRED"))
                    return 2
            emit(sink, reply(last_request, "limit", False,
                             "REQUEST_LIMIT"))
            return 2
    except (candidate.GateError, OSError, ValueError, TypeError):
        emit(sink, response(0, "hello", False, "TEST_HOST_UNAVAILABLE"))
        return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description="M11m disposable TASKS-copy host")
    ap.add_argument("--directory", required=True, type=Path)
    ap.add_argument("--writer-id", required=True)
    ap.add_argument("--bootstrap-test", action="store_true")
    args = ap.parse_args(argv)
    return serve(args.directory, args.writer_id, bootstrap=args.bootstrap_test)


if __name__ == "__main__":
    raise SystemExit(main())
