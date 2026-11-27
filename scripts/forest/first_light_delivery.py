"""FL5: bounded owner-side delivery for the existing disposable trial.

Not a native recipient authenticator, transport, UI wire schema or grant.
One owner worker owns the trial and generator; view-facing methods never
return an iterator, raw internal frame, operation ID or database key.
The caller must independently observe every view incarnation transition.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import secrets
import threading

from first_light_trial_host import FirstLightTrialHost, RealLocalTrialHost, FirstLightRefusal
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


class _OwnerDelivery:
    """One trial, one original view, one bounded latest-snapshot mailbox.

    Worker constructs/submits/advances/closes; a view observer or consumer
    may use observe_view/take/request_stop on another thread. No callbacks
    or provider progression under the mailbox lock. Withdrawal is sticky
    for this original lifetime, not STOP or worker cancellation.
    """

    def __init__(self, *, host):
        self._owner_thread = threading.current_thread()
        self._host = host
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


class FirstLightDelivery(_OwnerDelivery):
    """Existing offline fixture, with unchanged methods and false admission."""
    def __init__(self, *, test_transport):
        super().__init__(host=FirstLightTrialHost(test_transport=test_transport))


class RealLocalDelivery:
    """Owner-worker seam for actual ForestW, not an executable IPC service.

    Owner thread: submit, advance, close. Independent view/control thread:
    observe, take, stop, withdraw. The GUI must never block on advance.
    Epochs are local correlation, not authorization. Under current HOLD
    submit returns HELD, retains the draft and never attaches a response.
    No real native snapshot is emitted until the admission implementation
    exists; fixture snapshots must never be relabeled as native.
    """
    def __init__(self, *, endpoint=None):
        self._host = RealLocalTrialHost(endpoint=endpoint)
        self._delivery = _OwnerDelivery(host=self._host)
        self._view_lock = threading.Lock()
        self._epoch = None
        self._last_epoch = 0
        self._view = None

    @staticmethod
    def _valid_epoch(epoch):
        return type(epoch) is int and 0 < epoch <= 2**53 - 1

    def observe(self, epoch):
        """Each new view has a strictly increasing owner-observed epoch."""
        with self._view_lock:
            if epoch is not None and (not self._valid_epoch(epoch)
                    or epoch <= self._last_epoch):
                return False
            if self._view is not None:
                self._delivery.request_stop(self._view)
            if epoch is not None:
                self._last_epoch = epoch
            self._epoch = epoch
            self._view = object() if epoch is not None else None
            self._delivery.observe_view(self._view)
            return True

    def _current(self, epoch):
        with self._view_lock:
            if self._valid_epoch(epoch) and epoch == self._epoch:
                return self._view
            return None

    def submit(self, model, prompt, epoch):
        """Do not attach or clear draft unless original submission accepted."""
        self._delivery._worker()
        view = self._current(epoch)
        if view is None:
            return "REFUSED"
        try:
            self._host.stage_submission(model, prompt)
        except FirstLightRefusal as exc:
            return "HELD" if str(exc) == "NATIVE_ADMISSION_HOLD" else "REFUSED"
        # No alternate sender, no simulated response. This is unreachable
        # until independent admission and native snapshot release exist.
        try:
            self._delivery.submit(view, prompt)
        except DeliveryRefusal:
            # Staging may already have claimed the original attempt.
            return "UNKNOWN_HOLD"
        status, _ = self._delivery.owner_outcome()
        return "ACCEPTED" if status == "PREPARED" else "UNKNOWN_HOLD"

    def advance(self):
        self._delivery.advance()

    def take(self, epoch):
        view = self._current(epoch)
        if view is None:
            return None
        snapshot = self._delivery.take(view)
        # Never expose a fixture/non-admitted answer on the real path.
        # Native admission projection remains an explicit future boundary.
        if snapshot is not None and (snapshot.text or snapshot.status in
                ("GENERATING", "LOCAL_COMMITTED")) and not snapshot.native_admitted:
            self.withdraw(epoch)
            return None
        return snapshot

    def stop(self, epoch):
        view = self._current(epoch)
        if view is None:
            return "STOP_UNAVAILABLE"
        return self._delivery.request_stop(view)

    def withdraw(self, epoch):
        with self._view_lock:
            if not self._valid_epoch(epoch) or epoch != self._epoch:
                return False
            self._delivery.request_stop(self._view)
            self._delivery.observe_view(None)
            self._epoch = self._view = None
            return True

    def close(self):
        self.observe(None)
        return self._delivery.close()


class RealLocalRequestBridge:
    """Runtime-owned typed boundary for the UI1 original request owner.

    In-process owner API, not an IPC listener or permission issuer. Submit,
    advance and close belong to the owner worker; observe/attach/take/stop/
    withdraw may be called from its independently observed control side.
    A future IPC wrapper must keep one canonical JS correlation object per
    original token, validate bounded frames, and call attach only after the
    existing feed successfully attaches. No callbacks from this bridge.
    """
    def __init__(self, *, endpoint=None):
        self._runtime = RealLocalDelivery(endpoint=endpoint)
        self._lock = threading.Lock()
        self._epoch = None
        self._last_epoch = 0
        self._used = False
        self._token = None
        self._attached = False
        self._stop = False
        self._terminal = False
        self._closed = False

    def _matches(self, correlation):
        return (self._token is not None and type(correlation) is dict
                and set(correlation) == {"token"}
                and type(correlation["token"]) is str
                and correlation["token"] == self._token)

    def _retire_locked(self):
        # Retire the original before a replacement can observe any result.
        epoch = self._epoch
        self._token = None
        self._attached = False
        self._epoch = None
        if epoch is not None:
            self._runtime.withdraw(epoch)

    def observe(self, epoch):
        with self._lock:
            if self._closed:
                return False
            if epoch is not None and not RealLocalDelivery._valid_epoch(epoch):
                return False
            if epoch == self._epoch:
                return True
            # Refuse stale/recycled epochs before withdrawing original custody.
            if epoch is not None and epoch <= self._last_epoch:
                return False
            self._retire_locked()
            if not self._runtime.observe(epoch):
                return False
            self._epoch = epoch
            if epoch is not None:
                self._last_epoch = epoch
            return True

    def submit(self, model, prompt, epoch):
        with self._lock:
            if (self._closed or self._used or self._epoch is None
                    or not RealLocalDelivery._valid_epoch(epoch)
                    or epoch != self._epoch):
                return "REFUSED"
            # One original bridge lifetime, even on HELD or unknown.
            self._used = True
            try:
                # Allocate the complete acceptance envelope before any original
                # request effect. Entropy failure cannot orphan an acceptance.
                token = secrets.token_hex(16)
                accepted = {"accepted": True, "correlation": {"token": token}}
                result = self._runtime.submit(model, prompt, epoch)
            except Exception:
                return "UNKNOWN_HOLD"
            if result in ("HELD", "REFUSED"):
                return result
            if result != "ACCEPTED":
                return "UNKNOWN_HOLD"
            self._token = token
            return accepted

    def attach(self, correlation):
        """Explicit successful original UI attachment, not a native grant."""
        with self._lock:
            if (self._closed or self._attached or self._stop or self._terminal
                    or not self._matches(correlation)):
                return False
            self._attached = True
            return True

    def take(self, correlation):
        with self._lock:
            if (self._closed or not self._attached or self._terminal
                    or not self._matches(correlation)):
                return None
            snapshot = self._runtime.take(self._epoch)
            if snapshot is None:
                return None
            # STOP freeze: suppress additional provisional output; original
            # commit-won/unknown terminal is delivered, not a provider receipt.
            if self._stop and snapshot.status not in ("LOCAL_COMMITTED", "UNKNOWN_HOLD"):
                return None
            if snapshot.status in ("LOCAL_COMMITTED", "UNKNOWN_HOLD"):
                self._terminal = True
            return {"epoch": self._epoch, "correlation": {"token": self._token},
                    "snapshot": asdict(snapshot)}

    def stop(self, correlation):
        with self._lock:
            if (self._closed or self._stop or self._terminal
                    or not self._matches(correlation)):
                return False
            # Fence provisional display before calling original R3 control,
            # including an uncertain or commit-won cancellation result.
            self._stop = True
            return self._runtime.stop(self._epoch) == "STOP_LATCHED"

    def withdraw(self, correlation):
        with self._lock:
            if self._closed or not self._matches(correlation):
                return False
            self._retire_locked()
            return True

    def advance(self):
        self._runtime.advance()

    def close(self):
        with self._lock:
            self._retire_locked()
            self._closed = True
        return self._runtime.close()
