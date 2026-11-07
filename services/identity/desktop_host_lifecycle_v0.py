"""Explicit, host-side wiring of existing Identity Center v0 components.

CI-ONLY INTEGRATION: NOT a production login service, runnable daemon, CLI,
credential vault, vetted IdP/network client or authority for business actions.
Constructing this object NEVER starts a listener, socket, browser or process.
Only a separately authorized *host-owned* start() makes local test transports.

The host supplies pinned HTTPS/PKCE exchange, ID-token signature verification,
system-browser launcher, authenticated API client, clock and private 0700
runtime directory. No QML or Social label can supply these dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from collections.abc import Callable

from desktop_context_projection_v0 import HostContextReply
from desktop_session_host_v0 import (
    DesktopSessionHost, TrustedHostConfig, VerifiedCodeExchange,
)
from native_loopback_callback_v0 import LoopbackCallbackReceiver
from private_context_ipc_v0 import PrivateContextSocket, empty_display


@dataclass(frozen=True, slots=True)
class HostLifecycleConfig:
    """Trusted host-owned settings, never loaded from QML or provider tokens."""

    issuer: str
    authorization_endpoint: str
    client_id: str
    api_audience: str
    runtime_directory: Path

    def __post_init__(self) -> None:
        # Validate pinned HTTPS and client values before *any* socket binds.
        # The actual callback URI uses the OS-bound port in start().
        TrustedHostConfig(
            issuer=self.issuer,
            authorization_endpoint=self.authorization_endpoint,
            client_id=self.client_id,
            api_audience=self.api_audience,
            redirect_uri="http://127.0.0.1:8765/callback",
        )
        if not isinstance(self.runtime_directory, Path) or not self.runtime_directory.is_absolute():
            raise ValueError("An explicit absolute host runtime directory is required")


class DesktopHostLifecycle:
    """One-shot owner-process lifecycle joining three reviewed v0 components.

    This object is not an IPC command handler. UI cannot call begin_login(),
    logout() or complete an OAuth callback through the read-only display socket.
    The protected host must independently decide when to invoke these methods.
    One login attempt is permitted per start, so an exhausted callback cannot
    be accidentally replayed with a new state. Restart requires a new object.
    """

    def __init__(
        self, *, config: HostLifecycleConfig,
        browser_open: Callable[[str], None],
        exchange_and_verify: Callable[[str, str, str, str], VerifiedCodeExchange],
        api_get: Callable[[str], HostContextReply],
        clock: Callable[[], int],
        session_is_active: Callable[[], bool] | None = None,
    ) -> None:
        if (type(config) is not HostLifecycleConfig or not all(
            callable(item) for item in
            (browser_open, exchange_and_verify, api_get, clock)
        ) or (session_is_active is not None and not callable(session_is_active))):
            raise ValueError("Trusted host-owned dependencies required")
        self._config = config
        self._browser_open = browser_open
        self._exchange = exchange_and_verify
        self._api_get = api_get
        self._clock = clock
        # A real seat/logind adapter must be supplied by a separately
        # approved isolated host. Legacy synthetic fixtures omit this gate.
        self._session_is_active = session_is_active
        self._revoked = threading.Event()
        self._lock = threading.RLock()
        self._status = "NEW"
        self._receiver: LoopbackCallbackReceiver | None = None
        self._session: DesktopSessionHost | None = None
        self._socket: PrivateContextSocket | None = None
        self._attempted = False
        self._allow_callback = False
        self._signed_in = False

    @property
    def started(self) -> bool:
        with self._lock:
            return self._status == "STARTED"

    @property
    def redirect_uri(self) -> str:
        """Host-only callback URI, never returned on the display socket."""
        with self._lock:
            if self._status != "STARTED" or self._receiver is None:
                raise RuntimeError("Host lifecycle is not running")
            return self._receiver.redirect_uri

    @property
    def display_socket_path(self) -> Path:
        """Host diagnostic only; clients use a fixed, separately approved path."""
        with self._lock:
            if self._status != "STARTED" or self._socket is None:
                raise RuntimeError("Host lifecycle is not running")
            return self._socket.socket_path

    def _seat_ok(self) -> bool:
        """Only host-owned checks. Missing production probes remain a gap."""
        if self._revoked.is_set():
            return False
        try:
            accepted = (self._session_is_active is None
                        or self._session_is_active() is True)
            return accepted and not self._revoked.is_set()
        except Exception:
            return False

    def _revoke_locked(self) -> None:
        self._revoked.set()
        self._allow_callback = False
        self._signed_in = False
        self._attempted = True
        if self._session is not None:
            self._session.logout()

    def session_event(self, kind: str) -> None:
        """Host-only seat event, NOT an IPC command or OS subscription.

        Call on an actual trusted lock, suspend, user switch or end event.
        The Event is set BEFORE waiting on the mutex; a pending HTTPS fetch
        cannot publish an older organization preview after revocation.
        """
        if kind not in ("lock", "suspend", "user-switch", "session-end"):
            raise ValueError("Unsupported trusted desktop session event")
        self._revoked.set()
        self.close()

    def _accept_callback(self, uri: str) -> dict[str, object]:
        # Invoked only by the fixed one-use numeric-loopback HTTP receiver.
        with self._lock:
            if not self._seat_ok():
                self._revoke_locked()
                return {"status": "SIGNED_OUT"}
            if (self._status != "STARTED" or not self._allow_callback
                    or self._session is None):
                return {"status": "SIGNED_OUT"}
            self._allow_callback = False
            answer = self._session.complete_callback(uri)
            if not self._seat_ok():
                self._revoke_locked()
                return {"status": "SIGNED_OUT"}
            self._signed_in = (answer == {"status": "SIGNED_IN"})
            return answer

    def _display_snapshot(self) -> dict[str, object]:
        # Invoked only by the private socket's fixed SNAPSHOT request.
        with self._lock:
            if self._status != "STARTED" or self._session is None:
                return empty_display("UNAVAILABLE")
            if not self._seat_ok():
                self._revoke_locked()
                return empty_display("SIGNED_OUT")
            if not self._signed_in:
                return empty_display("SIGNED_OUT" if self._attempted
                                     else "NOT_CONNECTED")
            view = self._session.refresh_context()
            # Seat lock/session revocation may arrive DURING the HTTPS call.
            if not self._seat_ok():
                self._revoke_locked()
                return empty_display("SIGNED_OUT")
            if view.get("status") not in ("READY", "NO_MEMBERSHIPS"):
                # A failed/denied verified API fetch must not retain a bearer
                # or preserve a previous company's display for future reads.
                self._signed_in = False
                self._allow_callback = False
                self._session.logout()
            return view

    def start(self) -> None:
        """Explicitly start test-only loopback and view-only socket transports.

        Required directory MUST preexist and meet the existing private IPC
        checks; no mkdir, autostart, login or browser action occurs here.
        """
        failure: Exception | None = None
        socket: PrivateContextSocket | None = None
        receiver: LoopbackCallbackReceiver | None = None
        with self._lock:
            if self._status != "NEW":
                raise RuntimeError("Host lifecycle cannot be started twice")
            if not self._seat_ok():
                self._status = "CLOSED"
                self._revoked.set()
                raise RuntimeError("Trusted desktop session unavailable")
            self._status = "STARTING"
            try:
                receiver = LoopbackCallbackReceiver(callback=self._accept_callback)
                self._receiver = receiver
                receiver.start()
                pinned = TrustedHostConfig(
                    issuer=self._config.issuer,
                    authorization_endpoint=self._config.authorization_endpoint,
                    client_id=self._config.client_id,
                    api_audience=self._config.api_audience,
                    redirect_uri=receiver.redirect_uri,
                )
                self._session = DesktopSessionHost(
                    config=pinned, browser_open=self._browser_open,
                    exchange_and_verify=self._exchange,
                    api_get=self._api_get, clock=self._clock,
                )
                socket = PrivateContextSocket(
                    runtime_directory=self._config.runtime_directory,
                    snapshot_provider=self._display_snapshot,
                    clock=self._clock,
                )
                self._socket = socket
                socket.start()
                self._status = "STARTED"
            except Exception as exc:
                failure = exc
                self._status = "CLOSED"
                if self._session is not None:
                    self._session.logout()
                socket, receiver = self._socket, self._receiver
                self._session = None
                self._receiver = None
                self._socket = None
        if failure is not None:
            # shutdown() waits for handler threads; never hold host lock here.
            try:
                if socket is not None:
                    socket.close()
            finally:
                if receiver is not None:
                    receiver.close()
            raise failure

    def begin_login(self) -> dict[str, object]:
        """Host-only one-time login initiation, never a display IPC method."""
        with self._lock:
            if self._status != "STARTED" or self._session is None:
                return {"status": "UNAVAILABLE"}
            if not self._seat_ok():
                self._revoke_locked()
                return {"status": "UNAVAILABLE"}
            if self._attempted:
                return {"status": "UNAVAILABLE"}
            self._attempted = True
            self._allow_callback = True
            result = self._session.start_login()
            if not self._seat_ok():
                self._revoke_locked()
                return {"status": "UNAVAILABLE"}
            if result != {"status": "LOGIN_PENDING"}:
                self._allow_callback = False
            return result

    def logout(self) -> dict[str, object]:
        """Fail closed before any in-flight callback or HTTPS read finishes."""
        self._revoked.set()
        with self._lock:
            self._revoke_locked()
            return {"status": "SIGNED_OUT"}

    def close(self) -> None:
        """Invalidate host secrets before closing transports, idempotently.

        Shutdown happens OUTSIDE the lock: server.shutdown() waits for handler
        threads, which may themselves be waiting to take this host lock.
        """
        # Immediate revocation blocks an in-flight network reply from becoming
        # a new display even while close is waiting for the host mutex.
        self._revoked.set()
        with self._lock:
            if self._status == "CLOSED":
                return
            self._status = "CLOSED"
            self._revoke_locked()
            socket, receiver = self._socket, self._receiver
            self._socket = None
            self._receiver = None
            self._session = None
        try:
            if socket is not None:
                socket.close()
        finally:
            if receiver is not None:
                receiver.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, kind, value, traceback):
        self.close()
