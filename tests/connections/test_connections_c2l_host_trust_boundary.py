#!/usr/bin/env python3
"""C2l synthetic topology adversarial and current production boundary checks."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/connections/experiments/C2lHostTrustBoundaryModel.py"
spec = importlib.util.spec_from_file_location("c2l_model_review_only", SOURCE)
assert spec is not None and spec.loader is not None
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

FLAGS = ("hostAuthenticated", "credentialPresent", "grantActive",
         "canApprove", "canUseApi")


def candidate(**overrides):
    case = {
        "schema": model.SCHEMA,
        "transport": model.CURRENT_SOCKET,
        "clientUid": 1000,
        "peerUid": 1000,
        "serviceUid": 1000,
        "unitRootOwned": False,
        "codeRootOwned": False,
        "busPolicyRootOwned": False,
        "operatorConsentVerified": False,
    }
    case.update(overrides)
    return case


class C2lHostTrustBoundaryTests(unittest.TestCase):
    def deny(self, evidence, reason, review=False):
        result = model.assess(evidence)
        self.assertEqual(set(result), set(FLAGS) |
                         {"status", "reason", "reviewCandidate"})
        self.assertEqual(result["status"], "DENY")
        self.assertEqual(result["reason"], reason)
        self.assertIs(result["reviewCandidate"], review)
        for flag in FLAGS:
            self.assertIs(result[flag], False, flag)

    def test_01_current_c2k_same_uid_is_never_identity(self):
        self.deny(candidate(), "SAME_UID_SOCKET_NOT_IDENTITY")

    def test_02_stronger_labels_cannot_upgrade_same_uid(self):
        self.deny(candidate(unitRootOwned=True, codeRootOwned=True,
                            busPolicyRootOwned=True,
                            operatorConsentVerified=True),
                  "SAME_UID_SOCKET_NOT_IDENTITY")

    def test_03_current_c2i_cross_uid_cannot_use_fixed_socket(self):
        self.deny(candidate(peerUid=1500, serviceUid=1500),
                  "C2I_C2J_CROSS_UID_INCOMPATIBLE")

    def test_04_future_bus_same_uid_is_still_insufficient(self):
        self.deny(candidate(transport=model.PROPOSED_BUS),
                  "PROPOSED_PEER_NOT_ISOLATED")

    def test_05_future_bus_peer_and_service_uid_must_agree(self):
        self.deny(candidate(transport=model.PROPOSED_BUS, peerUid=1500),
                  "PROPOSED_SERVICE_PEER_MISMATCH")

    def test_06_future_bus_requires_all_protected_components(self):
        base = candidate(transport=model.PROPOSED_BUS,
                         peerUid=1500, serviceUid=1500,
                         unitRootOwned=True, codeRootOwned=True,
                         busPolicyRootOwned=True,
                         operatorConsentVerified=True)
        for flag in ("unitRootOwned", "codeRootOwned", "busPolicyRootOwned"):
            case = dict(base)
            case[flag] = False
            with self.subTest(flag=flag):
                self.deny(case, "PROPOSED_INSTALL_PROTECTION_MISSING")

    def test_07_future_bus_missing_real_consent_is_refused(self):
        self.deny(candidate(transport=model.PROPOSED_BUS,
                            peerUid=1500, serviceUid=1500,
                            unitRootOwned=True, codeRootOwned=True,
                            busPolicyRootOwned=True),
                  "PROPOSED_CONSENT_NOT_PROVEN")

    def test_08_even_perfect_fake_topology_cannot_be_authenticated(self):
        self.deny(candidate(transport=model.PROPOSED_BUS, peerUid=1500,
                            serviceUid=1500, unitRootOwned=True,
                            codeRootOwned=True, busPolicyRootOwned=True,
                            operatorConsentVerified=True),
                  "PROPOSAL_ONLY_NO_DEPLOYED_TRUST_ROOT", review=True)

    def test_09_malformed_and_forged_evidence_is_denied(self):
        base = candidate()
        cases = [
            None, "APPROVED", True, [], {},
            {**base, "hostAuthenticated": True},
            {**base, "schema": "fake"},
            {**base, "transport": "user-requested-authentication"},
            {**base, "peerUid": True},
            {**base, "clientUid": -1},
            {**base, "serviceUid": "1500"},
            {**base, "codeRootOwned": 1},
            {**base, "operatorConsentVerified": "true"},
        ]
        for item in cases:
            with self.subTest(case=repr(item)[:60]):
                self.deny(item, "INVALID_EVIDENCE")

    def test_10_no_model_runtime_io_or_credential_actuation(self):
        text = SOURCE.read_text()
        tree = ast.parse(text)
        loaded = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                loaded.update(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom):
                loaded.add(node.module)
        self.assertTrue({"collections.abc", "__future__"} <= loaded)
        self.assertFalse(loaded & {
            "os", "sys", "subprocess", "socket", "pathlib", "requests",
            "dbus", "keyring", "time", "ctypes", "secretstorage",
        })
        for prohibited in ("secret-tool", "XDG_RUNTIME_DIR",
                           "POST_APOLLO_FIRMS_MAP_KEY", "AF_INET",
                           "systemctl", "os.geteuid(", "subprocess."):
            self.assertNotIn(prohibited, text)

    def test_11_current_production_seams_are_explicitly_unverified(self):
        inspect = (ROOT / "services/connections/ConnectionsHostStatusInspect.py").read_text()
        server = (ROOT / "services/connections/ConnectionsHostStatusServer.py").read_text()
        launcher = (ROOT / "services/connections/ConnectionsHostReadOnlyLauncher.py").read_text()
        observation = (ROOT / "services/connections/ConnectionsHostObservation.qml").read_text()
        request = (ROOT / "services/connections/ConnectionsRequestStatus.qml").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("uid == os.geteuid()", inspect)
        self.assertIn("uid == os.geteuid()", server)
        self.assertIn("0o600", server)
        self.assertIn("mode=0o700", server)
        self.assertIn("status_provider=lambda: \"IDLE\"", launcher)
        self.assertIn("readonly property bool hostAuthenticated: false", observation)
        self.assertIn("readonly property bool hostAuthenticated: false", request)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("return result(\"OBSERVED_UNVERIFIED\", decoded[\"state\"])", inspect)
        for file in (
            ROOT / "services/connections/qmldir",
            ROOT / "services/connections/ConnectionsHostObservation.qml",
            ROOT / "services/connections/ConnectionsRequestStatus.qml",
            ROOT / "services/connections/ConnectionsBroker.qml",
        ):
            self.assertNotIn("C2lHostTrustBoundaryModel", file.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
