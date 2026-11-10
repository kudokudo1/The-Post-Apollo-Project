"""Guard Identity's eventual native desktop caller against a raw-client bypass.

The production UI is deliberately still OFFLINE. This *source contract* stops
new shipped services/widgets from directly importing or constructing the
experimental SignedIdentityCommandClient instead of the mandatory composite
InstalledIdentityCommandAdapterV1. Real C4b/C5 witnesses/consent are pending.

This is not dynamic Python import security or host authentication: it is a CI
regression gate for this repository's supported native call path.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLIENT = Path("services/identity/desktop_signed_command_client_v0.py")
ADAPTER = Path("services/identity/installed_command_adapter_v1.py")
ALLOWED = frozenset((CLIENT, ADAPTER))
SOURCE_SUFFIXES = frozenset((".py", ".qml", ".js", ".cjs", ".mjs", ".ts", ".tsx"))
DIRECT_CLIENT = re.compile(
    r"\b(?:SignedIdentityCommandClient|desktop_signed_command_client_v0)\b"
)


class NativeAdapterOnlyCallPath(unittest.TestCase):
    def test_shipped_services_and_widgets_cannot_bypass_composite_adapter(self):
        offenders = []
        inspected = 0
        for subtree in ("services", "widgets"):
            for path in (ROOT / subtree).rglob("*"):
                if (not path.is_file() or path.is_symlink()
                        or path.suffix not in SOURCE_SUFFIXES):
                    continue
                inspected += 1
                rel = path.relative_to(ROOT)
                if rel in ALLOWED:
                    continue
                if DIRECT_CLIENT.search(path.read_text(encoding="utf-8")):
                    offenders.append(str(rel))
        self.assertGreater(inspected, 0, "Repository source was not scanned")
        self.assertEqual(offenders, [],
                         "Bypass path to raw signed client: " + ", ".join(offenders))

    def test_only_allowed_adapter_wires_both_live_witnesses_to_signed_client(self):
        source = (ROOT / ADAPTER).read_text(encoding="utf-8")
        self.assertIn("SignedIdentityCommandClient(", source)
        self.assertIn("enrolled_origin_consistent=complete_origin", source)
        self.assertIn("origin_probe.consistent(peer) is True", source)
        self.assertIn("installed_witness.consistent(peer) is True", source)
        self.assertIn("trusted_server_peer=trusted_server_peer", source)
        self.assertIn("active_seat=active_seat", source)
        # The original CPU++ boundary must remain inert until C4b/C5 approval.
        offline = (ROOT / "services/connections/ConnectionsSignInHostBoundary.js"
                   ).read_text(encoding="utf-8")
        for field in ("canBeginSignIn", "canCancel", "canRetry"):
            self.assertIn(field + ": false", offline)
        upper = (ROOT / "widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml"
                 ).read_text(encoding="utf-8")
        self.assertIn("HostBoundary.offline()", upper)
        self.assertNotIn("SignedIdentityCommandClient", upper)
        self.assertNotIn("InstalledIdentityCommandAdapterV1", upper)


if __name__ == "__main__":
    unittest.main()
