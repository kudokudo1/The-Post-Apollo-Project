#!/usr/bin/env python3
"""Actual disposable D-Bus daemon/process pilot; never a production trust test."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from dbus_next import Message, MessageType
from dbus_next.aio import MessageBus

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "services/connections/experiments/C2mPrivateBusStatusPilot.py"
BUS_NAME = "org.postapollo.ConnectionsStatusPilot"
OBJ_PATH = "/org/postapollo/ConnectionsStatusPilot"
INTERFACE = "org.postapollo.ConnectionsStatusPilot1"


class C2mPrivateBusTests(unittest.TestCase):
    def setUp(self):
        if shutil.which("dbus-daemon") is None:
            self.fail("CI requires actual dbus-daemon, not a mocked API")
        self.temp = tempfile.TemporaryDirectory(prefix="c2m-private-bus-")
        self.addCleanup(self.temp.cleanup)
        self.bus = subprocess.Popen(
            ["dbus-daemon", "--session", "--nofork", "--print-address=1"],
            cwd=self.temp.name, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.addCleanup(self._stop, self.bus)
        address = self.bus.stdout.readline().decode().strip()
        self.assertTrue(address.startswith("unix:"), address)
        self.env = dict(os.environ)
        self.env.update({
            "DBUS_SESSION_BUS_ADDRESS": address,
            "POST_APOLLO_C2M_DISPOSABLE_TEST_ONLY": "1",
        })
        self.pilots = []

    @staticmethod
    def _stop(p):
        if p.poll() is None:
            p.terminate()
        try:
            p.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate(timeout=3)

    def _cmd(self, mode, env=None, timeout=5):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(PILOT), mode],
            cwd=self.temp.name, stdin=subprocess.DEVNULL, capture_output=True,
            timeout=timeout, env=self.env if env is None else env,
        )

    def _start(self):
        p = subprocess.Popen(
            [sys.executable, "-I", "-B", str(PILOT), "--ci-private-serve"],
            cwd=self.temp.name, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env,
        )
        self.pilots.append(p)
        self.addCleanup(self._stop, p)
        until = time.monotonic() + 5
        while time.monotonic() < until:
            if p.poll() is not None:
                stdout, stderr = p.communicate(timeout=1)
                self.fail("Pilot exited: " + stderr.decode() + stdout.decode())
            data = self._cmd("--ci-private-inspect")
            if data.returncode == 0:
                obj = json.loads(data.stdout)
                if obj["status"] == "OBSERVED_UNVERIFIED":
                    return p
            time.sleep(0.05)
        self.fail("D-Bus pilot did not become observable")

    def test_01_no_implicit_service_or_system_bus_access(self):
        for arg in ([], ["--serve"], ["--system"], ["--ci-private-inspect", "--grant"]):
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(PILOT), *arg],
                cwd=self.temp.name, capture_output=True,
                timeout=3, env=self.env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"C2M_REFUSED_NOT_DISPOSABLE_PRIVATE_BUS", result.stderr)
        no_flag = dict(self.env)
        del no_flag["POST_APOLLO_C2M_DISPOSABLE_TEST_ONLY"]
        self.assertEqual(self._cmd("--ci-private-serve", no_flag).returncode, 2)
        bad_address = dict(self.env)
        bad_address["DBUS_SESSION_BUS_ADDRESS"] = "tcp:host=localhost,port=1"
        self.assertEqual(self._cmd("--ci-private-serve", bad_address).returncode, 2)

    def test_02_real_dbus_roundtrip_remains_unverified(self):
        self._start()
        observed = self._cmd("--ci-private-inspect")
        self.assertEqual(observed.returncode, 0, observed.stderr)
        value = json.loads(observed.stdout)
        self.assertEqual(set(value), {
            "status", "state", "hostAuthenticated", "credentialPresent",
            "grantActive", "canApprove", "canUseApi",
        })
        self.assertEqual(value["status"], "OBSERVED_UNVERIFIED")
        self.assertEqual(value["state"], "IDLE")
        for key in ("hostAuthenticated", "credentialPresent", "grantActive",
                    "canApprove", "canUseApi"):
            self.assertIs(value[key], False)

    def test_03_name_collision_does_not_queue_or_replace(self):
        first = self._start()
        second = self._cmd("--ci-private-serve")
        self.assertEqual(second.returncode, 2)
        self.assertIn(b"C2M_NAME_ALREADY_OWNED", second.stderr)
        self.assertIsNone(first.poll())
        value = json.loads(self._cmd("--ci-private-inspect").stdout)
        self.assertEqual(value["status"], "OBSERVED_UNVERIFIED")

    def test_04_service_shutdown_removes_bus_name(self):
        p = self._start()
        p.terminate()
        self.assertEqual(p.wait(timeout=3), 0)
        observed = self._cmd("--ci-private-inspect")
        self.assertEqual(observed.returncode, 0, observed.stderr)
        data = json.loads(observed.stdout)
        self.assertEqual(data["status"], "HOST_NOT_FOUND")
        for key in ("hostAuthenticated", "credentialPresent", "grantActive",
                    "canApprove", "canUseApi"):
            self.assertIs(data[key], False)

    def test_05_unimplemented_approve_is_rejected_by_real_bus(self):
        self._start()
        async def inspect_unknown():
            bus = await MessageBus(
                bus_address=self.env["DBUS_SESSION_BUS_ADDRESS"]).connect()
            try:
                msg = Message(destination=BUS_NAME, path=OBJ_PATH,
                              interface=INTERFACE, member="Approve")
                reply = await bus.call(msg)
                return reply.message_type, reply.body
            finally:
                bus.disconnect()
        message_type, _body = asyncio.run(inspect_unknown())
        self.assertEqual(message_type, MessageType.ERROR)

    def test_06_no_name_returns_denial_only(self):
        value = json.loads(self._cmd("--ci-private-inspect").stdout)
        self.assertEqual(value["status"], "HOST_NOT_FOUND")
        self.assertIs(value["canUseApi"], False)

    def test_07_no_prod_import_or_credential_grants(self):
        source = PILOT.read_text()
        for forbidden in ("secret-tool", "POST_APOLLO_FIRMS_MAP_KEY",
                          "dbus_next.BusType.SYSTEM", "subprocess.Popen",
                          "APPROVED", "secretstorage", "ALLOW_REPLACEMENT"):
            self.assertNotIn(forbidden, source)
        self.assertIn('flags=NameFlag.DO_NOT_QUEUE', source)
        self.assertIn('value = denied("OBSERVED_UNVERIFIED")', source)
        for name in ("ConnectionsHostObservation.qml", "ConnectionsRequestStatus.qml",
                     "ConnectionsBroker.qml", "qmldir"):
            self.assertNotIn("C2mPrivateBusStatusPilot",
                             (ROOT / "services/connections" / name).read_text())

    def test_08_contract_exposes_only_single_status_method(self):
        path = ROOT / "services/connections/experiments/C2mConnectionsStatusPilot.xml"
        node = ET.fromstring(path.read_text())
        self.assertEqual(node.attrib["name"], OBJ_PATH)
        interfaces = node.findall("interface")
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].attrib["name"], INTERFACE)
        methods = interfaces[0].findall("method")
        self.assertEqual([m.attrib["name"] for m in methods], ["GetStatus"])
        args = methods[0].findall("arg")
        self.assertEqual([a.attrib["direction"] for a in args], ["out"])
        self.assertEqual([a.attrib["type"] for a in args], ["s"])


class C3aOwnerPinningTests(unittest.TestCase):
    """Deterministic owner-switch tests, alongside the actual bus tests above."""

    def simulated_inspection(self, owners):
        spec = importlib.util.spec_from_file_location("c3a_c2m_pilot", PILOT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        pilot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pilot)
        routes = []
        seen = []

        class Daemon:
            async def call_get_name_owner(self, name):
                self_name = owners[min(len(seen), len(owners) - 1)]
                seen.append(self_name)
                if self_name is None:
                    raise RuntimeError("simulated owner disappeared")
                return self_name

            async def call_get_connection_unix_user(self, owner):
                if owner != owners[0]:
                    raise RuntimeError("wrong owner UID lookup")
                return 1100

        daemon = Daemon()

        class Service:
            async def call_get_status(self):
                return pilot._payload()

        class Proxy:
            def __init__(self, service):
                self.service = service

            def get_interface(self, name):
                return daemon if self.service == "daemon" else Service()

        class Bus:
            async def connect(self):
                return self

            async def introspect(self, destination, path):
                routes.append(("introspect", destination, path))
                if destination not in {"org.freedesktop.DBus", owners[0]}:
                    raise RuntimeError("must never call the replaceable name")
                return object()

            def get_proxy_object(self, destination, path, xml):
                routes.append(("proxy", destination, path))
                if destination == "org.freedesktop.DBus":
                    return Proxy("daemon")
                if destination != owners[0]:
                    raise RuntimeError("must use pinned unique owner")
                return Proxy("service")

            def disconnect(self):
                routes.append(("disconnect", "", ""))

        with patch.object(pilot, "MessageBus", side_effect=lambda bus_address: Bus()):
            result = asyncio.run(pilot._inspect("unix:path=/ci-only"))
        return result, routes

    def assert_never_granted(self, result):
        for key in ("hostAuthenticated", "credentialPresent", "grantActive",
                    "canApprove", "canUseApi"):
            self.assertIs(result[key], False, (key, result))

    def test_09_stable_unique_owner_pins_all_service_calls(self):
        result, routes = self.simulated_inspection([":1.42", ":1.42"])
        self.assertEqual(result["status"], "OBSERVED_UNVERIFIED")
        self.assertEqual(result["state"], "IDLE")
        for action in ("introspect", "proxy"):
            self.assertIn((action, ":1.42", OBJ_PATH), routes)
        self.assertNotIn(("introspect", BUS_NAME, OBJ_PATH), routes)
        self.assertNotIn(("proxy", BUS_NAME, OBJ_PATH), routes)
        self.assert_never_granted(result)

    def test_10_owner_switch_after_response_fails_closed(self):
        result, routes = self.simulated_inspection([":1.42", ":1.43"])
        self.assertEqual(result["status"], "HOST_OWNER_CHANGED")
        self.assertEqual(result["state"], "")
        self.assert_never_granted(result)
        self.assertIn(("proxy", ":1.42", OBJ_PATH), routes)

    def test_11_owner_disappearance_after_response_fails_closed(self):
        result, _ = self.simulated_inspection([":1.42", None])
        self.assertEqual(result["status"], "HOST_OWNER_CHANGED")
        self.assert_never_granted(result)

    def test_12_forged_nonunique_name_fails_before_service_call(self):
        result, routes = self.simulated_inspection([BUS_NAME])
        self.assertEqual(result["status"], "RESPONSE_INVALID")
        self.assertNotIn(("proxy", BUS_NAME, OBJ_PATH), routes)
        self.assert_never_granted(result)



if __name__ == "__main__":
    unittest.main(verbosity=2)
