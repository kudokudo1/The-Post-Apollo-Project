#!/usr/bin/env python3
"""C2n noninstalled service/package contract. No host changes or process launch."""
from configparser import ConfigParser
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "services/connections/experiments/c2n_package"
UNIT = PKG / "postapollo-connections-status.service.template"
POLICY = PKG / "org.postapollo.ConnectionsStatus1.conf.template"
API = PKG / "org.postapollo.ConnectionsStatus1.xml"
NAME = "org.postapollo.ConnectionsStatus1"
PATH = "/org/postapollo/ConnectionsStatus1"
SERVICE_USER = "postapollo-connections"
READERS_GROUP = "postapollo-status-readers"


class C2nProtectedPolicyContract(unittest.TestCase):
    def setUp(self):
        self.unit = UNIT.read_text()
        self.policy_source = POLICY.read_text()
        self.xml = ET.fromstring(self.policy_source)
        self.cfg = ConfigParser(interpolation=None)
        self.cfg.read_string(self.unit)

    def test_01_service_is_noninstalled_and_missing_executable(self):
        self.assertEqual(list(self.cfg.sections()), ["Unit", "Service"])
        service = self.cfg["Service"]
        self.assertEqual(service["Type"], "dbus")
        self.assertEqual(service["BusName"], NAME)
        self.assertEqual(service["User"], SERVICE_USER)
        self.assertEqual(service["Group"], SERVICE_USER)
        self.assertEqual(service["DynamicUser"], "no")
        self.assertEqual(service["ExecStart"],
                         "/usr/libexec/post-apollo/connections-status-host --read-only")
        self.assertNotIn("Install", self.cfg.sections())
        self.assertIn("deliberately absent", self.unit)
        self.assertFalse((ROOT / "usr/libexec/post-apollo/connections-status-host").exists())

    def test_02_service_has_no_network_or_host_write_capability(self):
        s = self.cfg["Service"]
        expected = {
            "Restart": "no", "NoNewPrivileges": "yes",
            "ProtectSystem": "strict", "ProtectHome": "yes",
            "PrivateTmp": "yes", "PrivateDevices": "yes",
            "ProtectKernelTunables": "yes", "ProtectControlGroups": "yes",
            "ProtectKernelModules": "yes", "RestrictAddressFamilies": "AF_UNIX",
            "IPAddressDeny": "any", "CapabilityBoundingSet": "",
            "AmbientCapabilities": "", "LockPersonality": "yes",
            "RestrictSUIDSGID": "yes",
            "SystemCallArchitectures": "native", "UMask": "0077",
        }
        for key, value in expected.items():
            with self.subTest(setting=key):
                self.assertEqual(s.get(key), value)
        for unexpected in ("EnvironmentFile", "Environment",
                           "ReadWritePaths", "WorkingDirectory",
                           "ExecStartPre", "ExecStartPost"):
            self.assertNotIn(unexpected, s)
        self.assertNotRegex(self.unit, r"(?:^|\n)\[Socket\]")

    def test_03_policy_is_narrow_and_default_denied(self):
        policies = self.xml.findall("policy")
        self.assertEqual(len(policies), 3)
        self.assertEqual(policies[0].attrib, {"context": "default"})
        self.assertEqual([n.tag for n in policies[0]], ["deny", "deny"])
        self.assertEqual(policies[0][0].attrib, {"own": NAME})
        self.assertEqual(policies[0][1].attrib, {"send_destination": NAME})
        self.assertEqual(policies[1].attrib, {"user": SERVICE_USER})
        self.assertEqual([n.tag for n in policies[1]], ["allow"])
        self.assertEqual(policies[1][0].attrib, {"own": NAME})
        self.assertEqual(policies[2].attrib, {"group": READERS_GROUP})
        self.assertEqual([n.tag for n in policies[2]], ["allow"])
        self.assertEqual(policies[2][0].attrib, {
            "send_destination": NAME, "send_interface": NAME,
            "send_path": PATH, "send_member": "GetStatus",
            "send_type": "method_call",
        })

    def test_04_contract_has_only_getstatus_and_one_output(self):
        xml = ET.parse(API).getroot()
        self.assertEqual(xml.tag, "node")
        self.assertEqual(xml.attrib, {"name": PATH})
        interfaces = xml.findall("interface")
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].attrib, {"name": NAME})
        self.assertEqual([m.attrib.get("name") for m in interfaces[0]], ["GetStatus"])
        self.assertEqual([a.attrib for a in interfaces[0][0].findall("arg")],
                         [{"name": "statusJson", "type": "s", "direction": "out"}])

    def test_05_no_auto_install_or_credential_interface(self):
        for text in (self.unit, self.policy_source, API.read_text()):
            for word in ("password", "secret-tool", "POST_APOLLO_FIRMS_MAP_KEY",
                         "Approve", "Authorize", "ReadCredential",
                         "writeFileSync", "subprocess", "ExecStopPost"):
                self.assertNotIn(word, text)
        for path in (
            ROOT / "services/connections/ConnectionsBroker.qml",
            ROOT / "services/connections/ConnectionsRequestStatus.qml",
            ROOT / "services/connections/ConnectionsHostObservation.qml",
            ROOT / "services/connections/qmldir",
        ):
            current = path.read_text()
            self.assertNotIn(NAME, current)
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)

    def test_06_no_root_policy_wildcard_and_no_dynamic_user(self):
        for p in self.xml.findall("policy"):
            self.assertNotIn("*", str(p.attrib))
            for element in p:
                self.assertNotIn("*", str(element.attrib))
        self.assertNotIn("DynamicUser=yes", self.unit)
        self.assertNotIn("User=root", self.unit)
        self.assertNotIn('send_destination="*"', self.policy_source)
        self.assertNotIn('own="*"', self.policy_source)
        self.assertNotIn("org.freedesktop.systemd1", self.policy_source)
        self.assertEqual(
            len([p for p in (ROOT / "services/connections").glob("*.qml")
                 if NAME in p.read_text()]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
