"""Bounded logind system-bus adapter tests with disposable D-Bus doubles.

No actual host session, logind manipulation, screen lock or local OS writes.
The production adapter calls real dbus-next SYSTEM bus methods; the fakes
assert exact DBus method and signal names without using someone's desktop.
"""
from __future__ import annotations

import asyncio
import http.client
import json
from pathlib import Path
import os
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from logind_seat_guard_v0 import LogindSeatGuard
from desktop_host_lifecycle_v0 import DesktopHostLifecycle, HostLifecycleConfig
from desktop_context_projection_v0 import HostContextReply
from desktop_session_host_v0 import VerifiedCodeExchange
from private_context_ipc_v0 import read_private_display

NOW = 1_800_000_000
ISSUER = "https://ci-issuer.invalid/realms/ci"


class Variant:
    def __init__(self, value):
        self.value = value


class MockSession:
    def __init__(self):
        self.on_lock_callback = None

    def on_lock(self, callback):
        self.on_lock_callback = callback

    async def get_id(self):
        return "c2"

    def lock(self):
        self.on_lock_callback()


class MockProperties:
    def __init__(self, uid):
        self.on_properties_changed_callback = None
        self.fail = False
        self.responses = {
            "Id": Variant("c2"),
            "User": Variant([uid, "/org/freedesktop/login1/user/1000"]),
            "Active": Variant(True),
            "State": Variant("active"),
            "LockedHint": Variant(False),
        }

    def on_properties_changed(self, cb):
        self.on_properties_changed_callback = cb

    async def call_get_all(self, interface):
        assert interface == "org.freedesktop.login1.Session"
        if self.fail:
            raise OSError("Synthetic dbus failure")
        return dict(self.responses)

    def changed(self, properties=None, invalidated=None):
        self.on_properties_changed_callback(
            "org.freedesktop.login1.Session", properties or [],
            invalidated or [],
        )


class MockManager:
    def __init__(self, bus):
        self.bus = bus
        self.on_sleep_callback = None
        self.on_removed_callback = None

    async def call_get_session_by_pid(self, pid):
        self.bus.seen_pid = pid
        if self.bus.no_session:
            raise RuntimeError("No OS session for host PID")
        return self.bus.session_path

    def on_prepare_for_sleep(self, cb):
        self.on_sleep_callback = cb

    def on_session_removed(self, cb):
        self.on_removed_callback = cb

    def sleep(self):
        self.on_sleep_callback(True)

    def resume(self):
        self.on_sleep_callback(False)

    def removed(self):
        self.on_removed_callback("c2", self.bus.session_path)


class MockProxy:
    def __init__(self, bus, path):
        self.bus, self.path = bus, path

    def get_interface(self, name):
        if self.path == "/org/freedesktop/login1":
            assert name == "org.freedesktop.login1.Manager"
            return self.bus.manager
        if name == "org.freedesktop.login1.Session":
            return self.bus.session
        assert name == "org.freedesktop.DBus.Properties"
        return self.bus.properties


class MockBus:
    def __init__(self, uid=1000):
        self.session_path = "/org/freedesktop/login1/session/_c2"
        self.manager = MockManager(self)
        self.session = MockSession()
        self.properties = MockProperties(uid)
        self.no_session = False
        self.seen_pid = None
        self.paths = []
        self.disconnected = asyncio.Event()

    async def introspect(self, owner, path):
        assert owner == "org.freedesktop.login1"
        self.paths.append(path)
        return object()

    def get_proxy_object(self, owner, path, node):
        assert owner == "org.freedesktop.login1"
        return MockProxy(self, path)

    async def wait_for_disconnect(self):
        await self.disconnected.wait()

    def disconnect(self):
        self.disconnected.set()


class LogindSeatGuardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = 10.0
        self.bus = MockBus()
        self.revokes = []
        self.notified = threading.Event()
        self.guard = self._guard()
        self.addAsyncCleanup(self.guard.close)

    def _callback(self, kind):
        self.revokes.append(kind)
        self.notified.set()

    def _guard(self):
        async def factory():
            return self.bus
        return LogindSeatGuard(
            on_revoke=self._callback, bus_factory=factory,
            pid_provider=lambda: 1200,
            uid_provider=lambda: 1000,
            monotonic=lambda: self.now,
            poll_seconds=0.2, stale_after_seconds=0.7,
        )

    async def _event(self):
        self.assertTrue(await asyncio.to_thread(self.notified.wait, 2))

    async def test_no_bus_connection_until_explicit_start(self):
        self.assertEqual(self.bus.paths, [])
        self.assertFalse(self.guard.is_active())
        await self.guard.start()
        self.assertEqual(self.bus.seen_pid, 1200)
        self.assertEqual(self.bus.paths, [
            "/org/freedesktop/login1", self.bus.session_path,
        ])
        self.assertTrue(self.guard.is_active())

    async def test_default_factory_uses_real_system_bus_api_not_session_bus(self):
        from dbus_next import BusType
        source = self.bus
        def factory(*, bus_type):
            self.assertEqual(bus_type, BusType.SYSTEM)
            class Connector:
                async def connect(self):
                    return source
            return Connector()

        monitor = LogindSeatGuard(
            on_revoke=self._callback,
            pid_provider=lambda: 1200, uid_provider=lambda: 1000,
            monotonic=lambda: self.now, poll_seconds=0.2,
            stale_after_seconds=0.7,
        )
        try:
            with patch("dbus_next.aio.MessageBus", side_effect=factory):
                await monitor.start()
            self.assertTrue(monitor.is_active())
            self.assertEqual(source.seen_pid, 1200)
        finally:
            await monitor.close()

    async def test_lock_signal_revokes_and_never_recovers(self):
        await self.guard.start()
        self.bus.session.lock()
        self.assertFalse(self.guard.is_active())
        await self._event()
        self.assertEqual(self.revokes, ["lock"])
        with self.assertRaises(RuntimeError):
            await self.guard.start()

    async def test_suspend_preparation_revokes_but_resume_cannot_restore(self):
        await self.guard.start()
        self.bus.manager.resume()
        self.assertTrue(self.guard.is_active())
        self.bus.manager.sleep()
        await self._event()
        self.assertEqual(self.revokes, ["suspend"])
        self.bus.manager.resume()
        self.assertFalse(self.guard.is_active())

    async def test_session_removed_revokes(self):
        await self.guard.start()
        self.bus.manager.removed()
        await self._event()
        self.assertEqual(self.revokes, ["session-end"])

    async def test_user_switch_and_locked_hint_change_revoke(self):
        for change, wanted in (
            ({"Active": Variant(False)}, "user-switch"),
            ({"State": Variant("online")}, "user-switch"),
            ({"LockedHint": Variant(True)}, "lock"),
            ({"User": Variant([2000, "/org/freedesktop/login1/user/2000"])},
             "session-end"),
        ):
            with self.subTest(change=list(change)):
                await self.guard.close()
                self.bus = MockBus()
                self.notified.clear()
                self.guard = self._guard()
                await self.guard.start()
                self.bus.properties.changed(change)
                await self._event()
                self.assertEqual(self.revokes[-1], wanted)
                self.assertFalse(self.guard.is_active())
        await self.guard.close()

    async def test_invalidation_of_critical_property_revokes(self):
        await self.guard.start()
        self.bus.properties.changed({}, ["LockedHint"])
        await self._event()
        self.assertEqual(self.revokes, ["session-end"])

    async def test_wrong_os_uid_and_missing_pid_session_fail_closed(self):
        self.bus.properties.responses["User"] = Variant(
            [2000, "/org/freedesktop/login1/user/2000"]
        )
        with self.assertRaises(RuntimeError):
            await self.guard.start()
        self.assertFalse(self.guard.is_active())
        await self._event()
        await self.guard.close()
        self.bus = MockBus()
        self.bus.no_session = True
        self.guard = self._guard()
        with self.assertRaises(RuntimeError):
            await self.guard.start()
        self.assertFalse(self.guard.is_active())

    async def test_bus_disconnect_revokes(self):
        await self.guard.start()
        self.bus.disconnect()
        await self._event()
        self.assertEqual(self.revokes, ["session-end"])
        self.assertFalse(self.guard.is_active())

    async def test_periodic_read_failure_revokes(self):
        await self.guard.start()
        self.bus.properties.fail = True
        await self._event()
        self.assertEqual(self.revokes, ["session-end"])

    async def test_stale_sample_prevents_access_even_before_next_poll(self):
        await self.guard.start()
        self.now += 1.0
        self.assertFalse(self.guard.is_active())

    async def test_close_does_not_revive_and_requires_new_instance(self):
        await self.guard.start()
        await self.guard.close()
        self.assertFalse(self.guard.is_active())
        with self.assertRaises(RuntimeError):
            await self.guard.start()

    async def test_host_integration_lock_clears_socket_and_blocks_login(self):
        runtime = tempfile.TemporaryDirectory(prefix="seat-host-ci-")
        self.addCleanup(runtime.cleanup)
        parent = Path(runtime.name)
        parent.chmod(0o700)
        urls = []
        holder = {}
        self.guard._on_revoke = lambda kind: holder["host"].session_event(kind)

        def exchange(code, verifier, nonce, uri):
            return VerifiedCodeExchange(
                access_token="test-only-host-memory-bearer",
                issuer=ISSUER, client_id="ci-native",
                nonce=nonce, subject="disposable-person",
                expires_at=NOW + 100,
                token_type="Bearer", signed_id_token_verified=True,
            )

        def api(token):
            self.assertEqual(token, "test-only-host-memory-bearer")
            return HostContextReply(200, "application/json", json.dumps({
                "schema": "post-apollo.identity.context-summary.v0",
                "status": "OK",
                "organizations": [{
                    "organizationId": "llc_ci", "kind": "llc",
                    "scopeGrants": [{
                        "action": "records.read", "divisionId": "test",
                        "unitId": "east", "expiresAt": NOW + 50,
                    }],
                }],
                "portfolios": [],
            }).encode("ascii"))

        host = DesktopHostLifecycle(
            config=HostLifecycleConfig(
                issuer=ISSUER,
                authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
                client_id="ci-native", api_audience="ci-api",
                runtime_directory=parent,
            ),
            browser_open=urls.append, exchange_and_verify=exchange,
            api_get=api, clock=lambda: NOW,
            session_is_active=self.guard.is_active,
        )
        holder["host"] = host
        self.addCleanup(host.close)
        await self.guard.start()
        await asyncio.to_thread(host.start)
        self.assertEqual(host.begin_login(), {"status": "LOGIN_PENDING"})
        auth = parse_qs(urlsplit(urls[-1]).query)
        callback_port = urlsplit(host.redirect_uri).port
        def callback():
            connection = http.client.HTTPConnection(
                "127.0.0.1", callback_port, timeout=3,
            )
            connection.request(
                "GET", "/callback?" + urlencode({
                    "code": "ci-test-code", "state": auth["state"][0],
                    "iss": ISSUER,
                }), headers={"Host": f"127.0.0.1:{callback_port}"},
            )
            response = connection.getresponse()
            status = response.status
            response.read()
            connection.close()
            return status
        self.assertEqual(await asyncio.to_thread(callback), 200)
        socket_path = host.display_socket_path
        display = await asyncio.to_thread(
            read_private_display, socket_path, clock=lambda: NOW,
        )
        self.assertEqual(display["status"], "READY")
        self.bus.session.lock()
        self.assertFalse(self.guard.is_active())
        # Host teardown runs in a background notifier thread.
        for _ in range(50):
            if not host.started:
                break
            await asyncio.sleep(0.05)
        self.assertFalse(host.started)
        self.assertFalse(socket_path.exists())
        self.assertEqual(host.begin_login(), {"status": "UNAVAILABLE"})
        empty = await asyncio.to_thread(
            read_private_display, socket_path, clock=lambda: NOW,
        )
        self.assertEqual(empty["organizations"], [])


if __name__ == "__main__":
    unittest.main()
