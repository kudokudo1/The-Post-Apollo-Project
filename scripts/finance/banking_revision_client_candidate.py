"""M4t1: detached revision-bound manual client under M4s3 lifetime lease.

No command-line entry point or live QML integration. Each context represents
one fresh memory session; the consumer must discard that session at exit.
The cooperative lease is not a permission boundary or legacy-client detector.
"""
from contextlib import contextmanager
import copy

import banking_manual_store as manual
import banking_recovery_handoff_candidate as handoff

MAX_REVISION = handoff.MAX_REVISION

def fail(code):
    raise manual.Refusal(code)

def checked_document(doc):
    doc = manual.validate_doc(doc)
    if not 0 <= doc["revision"] <= MAX_REVISION:
        fail("CLIENT_REVISION_OUT_OF_RANGE")
    return copy.deepcopy(doc)

class _RevisionClient:
    def __init__(self, directory):
        self._directory = directory
        self._bound = checked_document(manual.read_doc(directory))
        self._closed = False
        self._blocked = False

    def _ready(self):
        if self._closed:
            fail("CLIENT_CLOSED")
        if self._blocked:
            fail("CLIENT_RELOAD_REQUIRED")

    def close(self):
        self._closed = True
        self._bound = None

    def snapshot(self):
        """Return a copy of the bound saved baseline, not a fresh disk read."""
        self._ready()
        return copy.deepcopy(self._bound)

    def _check_current(self):
        self._ready()
        try:
            observed = checked_document(manual.read_doc(self._directory))
            # Never update the bound revision merely because disk advanced.
            # Same-revision different content also refuses.
            if observed != self._bound:
                fail("CLIENT_BASELINE_CHANGED")
        except Exception:
            self._blocked = True
            raise

    def refresh(self):
        self._check_current()
        return self.snapshot()

    def save(self, expected_revision, session, *, confirm=False):
        self._ready()
        if confirm is not True:
            fail("CLIENT_CONFIRMATION_REQUIRED")
        session = copy.deepcopy(manual.validate_session(session))
        if session["mode"] != "manual":
            fail("ONLY_MANUAL_ACCOUNTS_CAN_BE_SAVED")
        return self._write(expected_revision, session, "save")

    def clear(self, expected_revision, *, confirm=False):
        self._ready()
        if confirm is not True:
            fail("CLIENT_CONFIRMATION_REQUIRED")
        return self._write(expected_revision, manual.empty_session(), "clear")

    def _write(self, expected_revision, session, action):
        self._ready()
        if (type(expected_revision) is not int
                or expected_revision != self._bound["revision"]):
            fail("CLIENT_EXPECTED_REVISION_MISMATCH")
        if expected_revision >= MAX_REVISION:
            fail("CLIENT_REVISION_OUT_OF_RANGE")
        self._check_current()
        request = {"action": action, "expectedRevision": expected_revision}
        if action == "save":
            request["session"] = session
        else:
            request["confirmClear"] = True
        try:
            # The existing store acquires its writer lock and rechecks the
            # expected revision atomically. No retry with a newer revision.
            receipt = checked_document(manual.run(self._directory, request))
            expected = {"version": 1, "revision": expected_revision + 1,
                        "session": session}
            if receipt != expected:
                fail("CLIENT_WRITE_RESULT_UNCERTAIN")
            self._bound = receipt
        except Exception:
            # Failure may occur after replacement; require a fresh client
            # session and explicit operator resolution, never blind retry.
            self._blocked = True
            raise
        return self.snapshot()

@contextmanager
def revision_client(directory):
    """Hold shared lease before first read through session disposal."""
    with handoff.client_lifetime(directory):
        client = _RevisionClient(directory)
        try:
            yield client
        finally:
            client.close()
