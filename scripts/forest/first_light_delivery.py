"""FL5: bounded owner-side delivery for the existing disposable trial.

Not a native recipient authenticator, transport, UI wire schema or grant.
One owner worker owns the trial and generator; view-facing methods never
return an iterator, raw internal frame, operation ID or database key.
The caller must independently observe every view incarnation transition.
"""
from __future__ import annotations

from dataclasses import dataclass
import threading

from first_light_trial_host import FirstLightTrialHost
from session_journal_v0 import MAX_BODY


class DeliveryRefusal(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TrialSnapshot:
    # Complete replacement snapshots: monotonic, not contiguous at take().
    sequence: int
    status: str
    text: str
    local_outcome: str
    provisional: bool
    # Local fixture status does not establish actual native admission.
    native_admitted: bool = False


class FirstLightDelivery:
    """One trial, one original view, one bounded latest-snapshot mailbox.

    Worker constructs/submits/advances/closes; a view observer or consumer
    may use observe_view/take/request_stop on another thread. No callbacks
    or provider progression under the mailbox lock. Withdrawal is sticky
    for this original lifetime, not STOP or worker cancellation.
    """

    def __init__(self, *, test_transport):
        self._owner_thread = threading.current_thread()
        self._host = FirstLightTrialHost(test_transport=test_transport)
        self._lock = threading.Lock()
        self._observed = None
        self._view = None
        self._withdrawn = False
        self._used = False
        self._busy = False
        self._closed = False
        self._stream = None
        self._operation = None
        self._attempt = None
        self._ordinal = 0
        self._seq = 0
        self._mailbox = None
        self._text = ""
        self._status = "IDLE"
        self._local = "UNKNOWN_HOLD"
        self._stop_requested = False
        self._terminal = False

    def _worker(self):
        if (threading.current_thread() is not self._owner_thread or self._closed
                or self._busy):
            raise DeliveryRefusal("OWNER_ACTION_UNAVAILABLE")

    def _current_locked(self, view):
        return (not self._closed and not self._withdrawn
                and self._view is not None and view is self._view
                and self._observed is self._view)

    def observe_view(self, view):
        """Independent owner observation; opaque incarnation object or None."""
        with self._lock:
            self._observed = view
            if self._view is not None and view is not self._view:
                self._withdrawn = True
                self._mailbox = None

    def _publish_locked(self):
        if not self._current_locked(self._view):
            return
        self._seq += 1
        self._mailbox = TrialSnapshot(
            self._seq, self._status, self._text, self._local,
            self._status in ("GENERATING", "STOP_REQUESTED") and bool(self._text))

    def submit(self, view, prompt):
        """Owner worker only; PREPARED is not actual provider admission."""
        self._worker()
        with self._lock:
            if self._used or view is None or view is not self._observed:
                raise DeliveryRefusal("SUBMIT_UNAVAILABLE")
            self._used = True
            self._view = view
            self._busy = True
        try:
            operation = self._host.submit(prompt)
            stream = self._host.run_internal()
            with self._lock:
                self._operation = operation
                self._stream = stream
                self._status = "PREPARED"
                self._publish_locked()
        except Exception:
            # No inference of safe retry from missing RESERVED.
            with self._lock:
                self._status = "UNKNOWN_HOLD"
                self._terminal = True
                self._publish_locked()
        finally:
            self._busy = False

    def take(self, view):
        """Dequeue once at exact observed view; no stale queue replay.

        Caller must still discard if its view is replaced before rendering.
        This is local mailbox consumption, not authenticated delivery ACK.
        """
        with self._lock:
            if not self._current_locked(view):
                return None
            snapshot = self._mailbox
            self._mailbox = None
            return snapshot

    def _finish(self, frame=None):
        # Owner only; finish the actual generator before local inspection.
        stream = self._stream
        try:
            if frame is not None:
                try:
                    next(stream)
                except StopIteration:
                    pass
                else:
                    frame = None
        except Exception:
            frame = None
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    frame = None
            self._stream = None
        try:
            local = self._host.local_outcome()
        except Exception:
            local = "UNKNOWN_HOLD"
        with self._lock:
            committed = (frame is not None and frame.payload["event"] == "COMMITTED"
                         and local == "COMMITTED_LOCAL"
                         and frame.payload.get("text") == self._text)
            self._local = local
            self._terminal = True
            self._status = "LOCAL_COMMITTED" if committed else "UNKNOWN_HOLD"
            if not committed:
                # Disposable policy: no partial answer in terminal snapshot.
                self._text = ""
            self._publish_locked()

    def advance(self):
        """Advance one original internal frame, on owner worker only."""
        self._worker()
        if self._stream is None:
            raise DeliveryRefusal("NO_ACTIVE_TRIAL")
        self._busy = True
        try:
            frame = next(self._stream)
            if (frame.operation != self._operation
                    or frame.ordinal != self._ordinal + 1):
                raise DeliveryRefusal("ORIGINAL_FRAME_MISMATCH")
            self._ordinal = frame.ordinal
            event = frame.payload["event"]
            if event == "RESERVED":
                if self._attempt is not None or frame.attempt_id is None:
                    raise DeliveryRefusal("ORIGINAL_ATTEMPT_MISMATCH")
            elif frame.attempt_id != self._attempt:
                raise DeliveryRefusal("ORIGINAL_ATTEMPT_MISMATCH")
            if event in ("COMMITTED", "UNKNOWN_HOLD"):
                self._finish(frame)
                return
            with self._lock:
                if event == "REQUESTED":
                    if self._ordinal != 1:
                        raise DeliveryRefusal("INVALID_FRAME_ORDER")
                elif event == "RESERVED":
                    self._attempt = frame.attempt_id
                    if not self._stop_requested:
                        self._status = "LOCAL_RESERVED"
                elif event == "STARTED":
                    if not self._stop_requested:
                        self._status = "GENERATING"
                elif event == "DELTA":
                    chunk = frame.payload["text"]
                    if (type(chunk) is not str or not chunk
                            or frame.payload.get("provisional") is not True
                            or len((self._text + chunk).encode("utf-8")) > MAX_BODY):
                        raise DeliveryRefusal("INVALID_CONTENT")
                    self._text += chunk
                    self._status = ("STOP_REQUESTED" if self._stop_requested
                                    else "GENERATING")
                else:
                    raise DeliveryRefusal("INVALID_FRAME")
                self._publish_locked()
        except Exception:
            self._finish()
        finally:
            self._busy = False

    def request_stop(self, view):
        """Use only original operation/attempt, never a caller-supplied ID."""
        with self._lock:
            if (not self._current_locked(view) or self._operation is None
                    or self._terminal or self._stop_requested):
                return "STOP_UNAVAILABLE"
            # R2/R3 control only: no callback, SQLite or transport work.
            # A pre-reservation request may race binding; never retarget.
            try:
                ack = self._host.request_stop(self._operation, self._attempt)
            except Exception:
                return "STOP_UNAVAILABLE"
            if ack == "STOP_LATCHED":
                self._stop_requested = True
                self._status = "STOP_REQUESTED"
                self._publish_locked()
            return ack

    def owner_outcome(self):
        """Worker-only local report, independent of view lifetime."""
        self._worker()
        return self._status, self._local

    def close(self):
        """Worker-only cleanup, no native quiescence or receipt claim."""
        self._worker()
        self._busy = True
        try:
            if self._stream is not None:
                self._finish()
            local = self._host.close()
            with self._lock:
                self._closed = True
                self._mailbox = None
                self._text = ""
            return local
        finally:
            self._busy = False
