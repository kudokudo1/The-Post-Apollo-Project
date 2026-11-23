#!/usr/bin/env python3
"""DOC 1: actual SIGKILL during a disposable C3e local SQLite transaction.

Demonstrates local crash/ACK semantics, not rollback resistance or custody.
No new SQL writer or wire protocol is implemented: the existing signed-history
DevelopmentLedger.record() performs every database change. A test-only
connection wrapper kills the forked writer after an exact SQLite statement.
This code must never be installed as a production service or used on a live DB.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import signal
import sys

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_PROCESS_CRASH_LOCAL_LEDGER_REQUIRED")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


L = _load("c3e_real_process_kill_existing_local_ledger",
          HERE / "C3eLocalDevelopmentHistoryLedger.py")
# Capture import-side process; the destructive trap may run only after fork.
IMPORT_PROCESS_PID = os.getpid()
SCHEMA = "postapollo.connections.c3e-process-sigkill-recovery.ci-v1"
STATUS = "LOCAL_PROCESS_CRASH_OBSERVATION_NOT_PROTECTED_SETTLEMENT"
TRAPS = ("AFTER_META_UPDATE_BEFORE_COMMIT", "AFTER_SQLITE_COMMIT_BEFORE_ACK")
DENIED = {
    **L.DENIED,
    "localStateProvesProtectedNonCommit": False,
    "localStateProvesProtectedCommit": False,
    "signedTerminalReceiptVerified": False,
    "independentRecoveryVerified": False,
    "safeToRetry": False,
}


class Refused(ValueError):
    """Unsafe CI execution or false authority claim."""


def _deny(msg: str):
    raise Refused(msg)


def _guard(root: Path):
    if (sys.platform != "linux"
            or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_REAL_SIGKILL_DISPOSABLE_HOSTED_ROOT_ONLY")
    if not isinstance(root, Path):
        _deny("C3E_REAL_SIGKILL_EXACT_FIXTURE_PATH_REQUIRED")
    return L._hosted_ci_root(root)


class _SqliteCrashTrap:
    """Only wraps existing DevelopmentLedger connection inside CI child."""

    def __init__(self, db, point: str):
        self._db = db
        self._point = point

    @property
    def in_transaction(self):
        return self._db.in_transaction

    def close(self):
        self._db.close()

    def execute(self, sql, parameters=()):
        result = self._db.execute(sql, parameters)
        if (self._point == TRAPS[0]
                and sql.startswith("UPDATE meta SET head=")
                and self._db.in_transaction):
            # Both challenge spend and head update were executed in SQLite,
            # but no COMMIT was performed. SIGKILL skips Python cleanup.
            os.kill(os.getpid(), signal.SIGKILL)
            os._exit(120)  # unreachable unless the kernel refused to kill
        if self._point == TRAPS[1] and sql == "COMMIT":
            # SQLite says COMMIT returned successfully, but no caller ACK
            # could be sent. The process terminates without a normal return.
            os.kill(os.getpid(), signal.SIGKILL)
            os._exit(121)
        return result


def child_writer_sigkill_ci_only(*, root: Path, record_args: dict,
                                 trap_point: str):
    """Called ONLY in a forked disposable GitHub-hosted child process."""
    root = _guard(root)
    if type(record_args) is not dict or trap_point not in TRAPS:
        _deny("C3E_REAL_SIGKILL_WRITER_EXACT_INPUTS_REQUIRED")
    if os.getpid() == IMPORT_PROCESS_PID:
        _deny("C3E_REAL_SIGKILL_FORKED_CHILD_REQUIRED")
    # Validate guard and database before installing the child-local trap.
    ledger = L.DevelopmentLedger(root)
    original_connect = L.connect

    def _connect_with_trap(known_root):
        if known_root != root:
            _deny("C3E_REAL_SIGKILL_WRONG_ROOT_REFUSED")
        return _SqliteCrashTrap(original_connect(known_root), trap_point)

    L.connect = _connect_with_trap
    ledger.record(**record_args)
    # The expected SIGKILL must happen before any ordinary return.
    os._exit(122)


def reopened_local_observation_ci_only(*, root: Path, challenge: bytes):
    """New process may observe local SQLite only, not independent authority."""
    root = _guard(root)
    if type(challenge) is not bytes or len(challenge) != 32:
        _deny("C3E_REAL_SIGKILL_EXACT_CHALLENGE_REQUIRED")
    ledger = L.DevelopmentLedger(root)
    snap = ledger.snapshot()
    outcome = ledger.outcome(challenge)
    if (type(snap) is not dict or type(outcome) is not dict
            or snap.get("status") != L.STATUS
            or outcome.get("status") != L.STATUS
            or any(snap.get(k) is not False
                   or outcome.get(k) is not False for k in L.DENIED)):
        _deny("C3E_REAL_SIGKILL_LOCAL_BACKEND_ATTEMPTED_GRANT")
    state = outcome.get("developmentOnlyState")
    head = outcome.get("developmentOnlyCommittedHeadSha256")
    if (state not in ("issued", "consumed")
            or (state == "issued" and head is not None)
            or (state == "consumed"
                and (type(head) is not str
                     or L.HEX.fullmatch(head) is None))
            or type(snap.get("previousSequence")) is not int
            or snap["previousSequence"] < 1
            or type(snap.get("previousHeadSha256")) is not str
            or L.HEX.fullmatch(snap["previousHeadSha256"]) is None):
        _deny("C3E_REAL_SIGKILL_MALFORMED_LOCAL_OBSERVATION")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "developmentOnlyObservedState": state,
        "developmentOnlyObservedHeadSha256": snap["previousHeadSha256"],
        "developmentOnlyObservedSequence": snap["previousSequence"],
        "developmentOnlyObservedCommittedHeadSha256": head,
        "next": "HOLD_NO_AUTOMATIC_RETRY_INDEPENDENT_CUSTODIAN_REQUIRED",
        **DENIED,
    }


def protected_recovery_admission(*_args, **_kwargs):
    _deny("C3E_REAL_SIGKILL_NO_PROTECTED_HISTORY_OR_RECOVERY_AUTHORITY")
