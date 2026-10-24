#!/usr/bin/env python3
"""M10q: disposable, long-lived JSON-lines authority rehearsal host.

Only operates on an explicitly specified 'handoff-test.db' private fixture.
Never opens real tasks.db, legacy JSON, GitHub, or user Quickshell data.
No automatic bootstrap on reconnect; existing sessions enter RECOVERY_REVIEW.
The replies are TEST observations, NEVER authorization for live FileView.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

FIXTURE = Path(__file__).resolve().with_name("TaskSqliteWriterAuthorityFixture.py")
MAX_LINE = 2048
MAX_REQUESTS = 1000


def _load_fixture():
    spec = importlib.util.spec_from_file_location("m10q_authority_fixture", FIXTURE)
    if spec is None or spec.loader is None:
        raise RuntimeError("FIXTURE_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_KEY")
        result[key] = value
    return result


def _reply(request_id, kind, *, ok, status, phase="UNKNOWN", epoch=None,
           pending=False, simulated_admission=False):
    return {
        "protocol": 1, "requestId": request_id, "kind": kind,
        "ok": bool(ok), "status": status, "phase": phase, "epoch": epoch,
        "pending": bool(pending), "simulatedAdmission": bool(simulated_admission),
        "sqliteWriteAuthorized": False, "liveChangePerformed": False
    }


def _send(reply, stream):
    stream.write(json.dumps(reply, separators=(",", ":"), ensure_ascii=True) + "\n")
    stream.flush()


def _exact(req, names):
    return type(req) is dict and set(req) == set(names)


def _status(host, request_id, kind, ok=True, reason="OK"):
    state = host.snapshot()
    return _reply(request_id, kind, ok=ok, status=reason,
                  phase=state["phase"], epoch=state["epoch"],
                  pending=state["pendingStage"] is not None,
                  simulated_admission=state["simulatedJsonStagePermitted"])


def serve(db: Path, writer_id: str, *, bootstrap=False, source=None, sink=None):
    """Lifetime-bound flock owner; no network or file access beyond test DB."""
    src = source if source is not None else sys.stdin.buffer
    out = sink if sink is not None else sys.stdout
    fixture = _load_fixture()
    try:
        with fixture.Authority(db, writer_id, bootstrap=bootstrap) as host:
            _send(_status(host, 0, "hello"), out)
            last_id = 0
            for index in range(MAX_REQUESTS):
                line = src.readline(MAX_LINE + 1)
                if line == b"":
                    return 0
                if len(line) > MAX_LINE or not line.endswith(b"\n"):
                    _send(_reply(None, "protocol", ok=False,
                                 status="MALFORMED_OR_OVERSIZED_INPUT"), out)
                    return 2
                try:
                    req = json.loads(line, object_pairs_hook=_no_duplicate_keys,
                                     parse_constant=lambda v: (_ for _ in ()).throw(ValueError()))
                except (ValueError, TypeError, UnicodeDecodeError):
                    _send(_reply(None, "protocol", ok=False, status="INVALID_JSON"), out)
                    return 2
                rid = req.get("requestId") if type(req) is dict else None
                kind = req.get("kind") if type(req) is dict else None
                if (type(rid) is not int or rid <= last_id or rid > MAX_REQUESTS
                        or type(kind) is not str):
                    _send(_reply(None, "protocol", ok=False,
                                 status="INVALID_OR_REPLAYED_REQUEST"), out)
                    return 2
                last_id = rid
                shapes = {
                    "status": {"requestId", "kind"},
                    "admit": {"requestId", "kind", "stageId"},
                    "freeze": {"requestId", "kind", "expectedEpoch"},
                    "settle": {"requestId", "kind", "stageId", "saved"}
                }
                if kind not in shapes or not _exact(req, shapes[kind]):
                    _send(_reply(rid, kind, ok=False, status="UNSUPPORTED_COMMAND"), out)
                    continue
                try:
                    if kind == "admit":
                        host.admit_stage(req["stageId"])
                    elif kind == "freeze":
                        host.freeze(req["expectedEpoch"])
                    elif kind == "settle":
                        host.settle_stage(req["stageId"], saved=req["saved"])
                    _send(_status(host, rid, kind), out)
                except (fixture.AdmissionError, TypeError, ValueError) as exc:
                    # Only enumerated fixture error codes, not filesystem paths.
                    code = str(exc)
                    if not (code.isupper() and len(code) <= 72
                            and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in code)):
                        code = "OPERATION_REFUSED"
                    _send(_status(host, rid, kind, ok=False, reason=code), out)
            _send(_reply(None, "protocol", ok=False, status="REQUEST_LIMIT"), out)
            return 2
    except (fixture.AdmissionError, OSError, Exception):
        # No absolute paths or task contents in stdout or stderr.
        _send(_reply(0, "hello", ok=False, status="AUTHORITY_UNAVAILABLE"), out)
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="M10q test-only handoff host")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--writer-id", required=True)
    parser.add_argument("--bootstrap-fixture", action="store_true")
    args = parser.parse_args(argv)
    if (not args.db.is_absolute() or args.db.name != "handoff-test.db"):
        _send(_reply(0, "hello", ok=False, status="EXPLICIT_TEST_DB_REQUIRED"),
              sys.stdout)
        return 2
    return serve(args.db, args.writer_id, bootstrap=args.bootstrap_fixture)


if __name__ == "__main__":
    raise SystemExit(main())
