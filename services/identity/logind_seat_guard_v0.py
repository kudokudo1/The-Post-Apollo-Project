"""Read-only Linux systemd-logind seat monitor for the isolated Identity host.

EXPLICIT ACTIVATION ONLY. Creating this object does not open D-Bus, inspect
the operating system, start an event loop, install files or create a service.
A future approved native host must run start() on its own asyncio event loop
BEFORE DesktopHostLifecycle.start(), then pass is_active as the host-only
session_is_active callback and route on_revoke to host.session_event().

The monitor only *reads* system-bus logind state and signals. It cannot call
Lock(), Unlock(), SetLockedHint(), grant permissions, or start OAuth. It
requires the host PID to belong to an OS login session with matching UID.
If hosted in a detached systemd --user service, GetSessionByPID may fail,
which correctly prevents sign-in until a reviewed session binding exists.

Important: Sway/swaylock may not report real compositor lock state via
logind LockedHint. An independent reliable compositor lock signal is still
required before production. This is a real logind reader, not that signal.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import os
import threading
import time
from typing import Any

_OWNER = "org.freedesktop.login1"
_MANAGER = "/org/freedesktop/login1"
_MANAGER_INTERFACE = "org.freedesktop.login1.Manager"
_SESSION_INTERFACE = "org.freedesktop.login1.Session"
_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
_ALLOWED_REVOKE = {"lock", "suspend", "user-switch", "session-end"}


class LogindSeatGuard:
    """Bound-to-host-process login1 observer with one-shot revocation latch.

    A caller may inject a bus factory and host PID only for disposable CI.
    The production path always uses dbus-next's SYSTEM bus and os.getpid().
    All bus methods are read-only. No synthetic 'unlock' can revive the guard.
    """

    def __init__(
        self, *,
        on_revoke: Callable[[str], None],
        poll_seconds: float = 1.0,
        stale_after_seconds: float = 3.0,
        bus_factory: Callable[[], Awaitable[Any]] | None = None,
        pid_provider: Callable[[], int] = os.getpid,
        uid_provider: Callable[[], int] = os.getuid,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if (not callable(on_revoke)
                or type(poll_seconds) not in (int, float)
                or not 0.2 <= poll_seconds <= 5.0
                or type(stale_after_seconds) not in (int, float)
                or not poll_seconds < stale_after_seconds <= 15
                or (bus_factory is not None and not callable(bus_factory))
                or not all(callable(x) for x in
                           (pid_provider, uid_provider, monotonic))):
            raise ValueError("Host-owned logind guard requirements missing")
        self._on_revoke = on_revoke
        self._poll = poll_seconds
        self._stale = stale_after_seconds
        self._factory = bus_factory
        self._pid = pid_provider
        self._uid = uid_provider
        self._clock = monotonic
        self._revoke = threading.Event()
        self._mutex = threading.Lock()
        self._ready = False
        self._last_seen = float("-inf")
        self._started = False
        self._closing = False
        self._bus: Any = None
        self._properties: Any = None
        self._path = ""
        self._session_id = ""
        self._periodic: asyncio.Task | None = None
        self._disconnect: asyncio.Task | None = None

    def is_active(self) -> bool:
        """Bounded-latency, lock-free-from-asyncio, fail-closed host probe."""
        if self._revoke.is_set():
            return False
        with self._mutex:
            return (not self._revoke.is_set() and self._ready
                    and self._started and not self._closing
                    and self._clock() - self._last_seen <= self._stale)

    @property
    def revoked(self) -> bool:
        return self._revoke.is_set()

    def _invalidate(self, kind: str) -> None:
        """Set the gate BEFORE notifying or waiting on the host's mutex."""
        if kind not in _ALLOWED_REVOKE:
            raise ValueError("Invalid host session event")
        if self._revoke.is_set():
            return
        self._revoke.set()
        with self._mutex:
            self._ready = False
        # The host's session_event() may synchronously join socket threads.
        # Never run it on the D-Bus event loop, whose responsiveness is vital
        # to dispatching logind signals. The set Event gates host reads now.
        def notify() -> None:
            try:
                self._on_revoke(kind)
            except Exception:
                # Event still revokes host access, even if owner cleanup fails.
                pass
        threading.Thread(
            target=notify, daemon=True, name="identity-logind-revoke",
        ).start()

    @staticmethod
    def _get(properties: dict, key: str) -> object:
        value = properties.get(key)
        return getattr(value, "value", None)

    def _check_properties(self, values: object) -> None:
        """Verify THIS process session's UID, activity and logind lock hint."""
        if type(values) is not dict:
            self._invalidate("session-end")
            return
        session_id = self._get(values, "Id")
        owner = self._get(values, "User")
        active = self._get(values, "Active")
        state = self._get(values, "State")
        locked = self._get(values, "LockedHint")
        if (type(session_id) is not str or session_id != self._session_id
                or not isinstance(owner, (tuple, list)) or len(owner) != 2
                or type(owner[0]) is not int or owner[0] != self._uid()):
            self._invalidate("session-end")
            return
        if locked is True:
            self._invalidate("lock")
            return
        if active is not True or state != "active" or locked is not False:
            self._invalidate("user-switch")
            return
        try:
            now = self._clock()
            if type(now) not in (int, float):
                raise ValueError("Untrusted monotonic clock")
            with self._mutex:
                if not self._revoke.is_set():
                    self._ready = True
                    self._last_seen = now
        except Exception:
            self._invalidate("session-end")

    def _on_properties_changed(self, interface: str, changes: dict,
                               invalidated: list) -> None:
        if self._revoke.is_set() or interface != _SESSION_INTERFACE:
            return
        if (not isinstance(invalidated, list) or
                any(key in {"Id", "User", "Active", "State", "LockedHint"}
                    for key in invalidated)):
            self._invalidate("session-end")
            return
        if not isinstance(changes, dict):
            self._invalidate("session-end")
            return
        if "LockedHint" in changes and self._get(changes, "LockedHint") is True:
            self._invalidate("lock")
        elif ("Active" in changes and self._get(changes, "Active") is not True
              or "State" in changes and self._get(changes, "State") != "active"):
            self._invalidate("user-switch")
        elif any(key in changes for key in ("Id", "User")):
            self._invalidate("session-end")
        # Do not promote a green signal into authorization. Only a complete
        # periodic GetAll snapshot with matching process/UID can do that.

    def _on_sleep(self, preparing: bool) -> None:
        if preparing is True:
            self._invalidate("suspend")

    def _on_lock(self) -> None:
        self._invalidate("lock")

    def _on_removed(self, session_id: str, path: str) -> None:
        if session_id == self._session_id or path == self._path:
            self._invalidate("session-end")

    async def _get_all(self) -> None:
        if self._revoke.is_set():
            return
        try:
            values = await asyncio.wait_for(
                self._properties.call_get_all(_SESSION_INTERFACE),
                timeout=self._stale,
            )
            if not self._revoke.is_set():
                self._check_properties(values)
        except Exception:
            self._invalidate("session-end")

    async def _poll_loop(self) -> None:
        while not self._revoke.is_set() and not self._closing:
            await asyncio.sleep(self._poll)
            await self._get_all()

    async def _watch_disconnect(self) -> None:
        try:
            await self._bus.wait_for_disconnect()
        except Exception:
            pass
        if not self._closing:
            self._invalidate("session-end")

    async def start(self) -> None:
        """Subscribe to *real* system D-Bus signals before trusting a read."""
        if self._started or self._revoke.is_set():
            raise RuntimeError("One-shot logind seat guard cannot be reused")
        self._started = True
        try:
            if self._factory is None:
                from dbus_next import BusType
                from dbus_next.aio import MessageBus
                bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            else:
                bus = await self._factory()
            self._bus = bus
            manager_node = await asyncio.wait_for(
                bus.introspect(_OWNER, _MANAGER), timeout=self._stale,
            )
            manager_proxy = bus.get_proxy_object(_OWNER, _MANAGER, manager_node)
            manager = manager_proxy.get_interface(_MANAGER_INTERFACE)
            pid = self._pid()
            if type(pid) is not int or not 1 <= pid < 2**32:
                raise ValueError("Host PID unavailable")
            path = await asyncio.wait_for(
                manager.call_get_session_by_pid(pid), timeout=self._stale,
            )
            if (type(path) is not str
                    or not path.startswith("/org/freedesktop/login1/session/")):
                raise ValueError("No matching host login1 session")
            self._path = path
            node = await asyncio.wait_for(
                bus.introspect(_OWNER, path), timeout=self._stale,
            )
            proxy = bus.get_proxy_object(_OWNER, path, node)
            session = proxy.get_interface(_SESSION_INTERFACE)
            self._properties = proxy.get_interface(_PROPERTIES_INTERFACE)
            # Bind events before trusting initial state, closing subscribe/read
            # race. Only the selected session's Lock signal is subscribed.
            manager.on_prepare_for_sleep(self._on_sleep)
            manager.on_session_removed(self._on_removed)
            session.on_lock(self._on_lock)
            self._properties.on_properties_changed(self._on_properties_changed)
            self._disconnect = asyncio.create_task(self._watch_disconnect())
            await self._get_all()
            if not self.is_active():
                raise RuntimeError("Trusted logind session is not active")
            self._periodic = asyncio.create_task(self._poll_loop())
        except Exception:
            self._invalidate("session-end")
            await self.close()
            raise RuntimeError("Trusted logind session unavailable") from None

    async def close(self) -> None:
        """Release read-only bus connection and permanently revoke this guard."""
        self._closing = True
        self._revoke.set()
        with self._mutex:
            self._ready = False
        tasks = [task for task in (self._periodic, self._disconnect)
                 if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._bus is not None:
            self._bus.disconnect()
        self._bus = None
        self._properties = None
