"""Actual Qt 6 QQmlEngine smoke test of the merged Organizations reader.

Requires PySide6 in disposable CI; no real Quickshell process or workstation.
Test-only Quickshell/Io QML stubs simulate stdout/exits and never start any
host service, Sway, browser, IPC server or network client. This exercises REAL
QML property bindings, signal handlers and Qt JavaScript, beyond Node parsing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "widgets/messanger/IdentityCenterOrganizationDisplayReader.qml"
STUBS = ROOT / "tests/messaging/fixtures/identity_qml_stubs"
SCHEMA = "post-apollo.identity.desktop-context-display.v0"
APP = QGuiApplication.instance() or QGuiApplication([])


def _value(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


def _body(*, status="READY", expired=False):
    companies = [
        {
            "organizationId": "synthetic_llc",
            "kind": "llc",
            "scopeGrants": [{
                "action": "records.read",
                "divisionId": "health",
                "unitId": "maryland",
                "expiresAt": 1 if expired else None,
            }],
        },
        {
            "organizationId": "synthetic_nonprofit",
            "kind": "nonprofit",
            "scopeGrants": [],
        },
    ]
    return {
        "schema": SCHEMA, "status": status,
        "organizations": companies if status == "READY" else [],
        "portfolios": ([{
            "portfolioId": "synthetic_group",
            "organizationIds": ["synthetic_llc", "synthetic_nonprofit"],
        }] if status == "READY" else []),
        "canSwitchOrganization": False,
    }


class RealQtOrganizationsReaderSmoke(unittest.TestCase):
    def setUp(self):
        self.engine = QQmlEngine()
        self.engine.addImportPath(str(STUBS))
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML)))
        self.assertTrue(
            self.component.isReady(),
            "The actual QML reader failed Qt parsing/loading:\n" +
            "\n".join(str(e) for e in self.component.errors()),
        )
        self.reader = self.component.create()
        self.assertIsNotNone(
            self.reader,
            "Reader QML instantiation failed:\n" +
            "\n".join(str(e) for e in self.component.errors()),
        )
        self.process = self.reader.findChild(QObject, "ciSnapshotProcess")
        self.assertIsNotNone(self.process, "Fake Quickshell Process was not bound")
        APP.processEvents()

    def tearDown(self):
        self.reader.setProperty("active", False)
        APP.processEvents()
        self.reader.deleteLater()
        self.engine.deleteLater()
        APP.processEvents()

    def _snapshot(self):
        return _value(self.reader.property("snapshot"))

    def _open(self):
        self.assertTrue(self.reader.setProperty("active", True))
        APP.processEvents()
        self.assertTrue(self.process.property("running"))
        self.assertEqual(
            list(_value(self.process.property("command"))),
            [
                "/usr/bin/python3",
                "/ci-fake-shell/services/identity/identity_display_reader_cli_v0.py",
                "--json",
            ],
            "QML spawned unexpected command or accepted caller parameters",
        )

    def _deliver(self, payload, code=0):
        self.process.finishWith(json.dumps(payload), code)
        APP.processEvents()

    def test_qt_engine_loads_real_reader_without_running_a_host(self):
        self.assertFalse(self.reader.property("active"))
        self.assertFalse(self.process.property("running"))
        self.assertIsNone(self._snapshot())
        self.assertFalse(self.reader.property("acceptResponse"))

    def test_active_view_reads_only_sanitized_organization_data(self):
        self._open()
        self._deliver(_body())
        current = self._snapshot()
        self.assertEqual(current["status"], "READY")
        self.assertEqual(
            [x["organizationId"] for x in current["organizations"]],
            ["synthetic_llc", "synthetic_nonprofit"],
        )
        self.assertFalse(current["canSwitchOrganization"])
        for key in ("Bearer", "accessToken", "refreshToken",
                    "principalId", "authorizationCode", "sessionId"):
            self.assertNotIn(key, repr(current))

    def test_logout_and_empty_membership_dismiss_company_list(self):
        self._open()
        self._deliver(_body())
        self.assertEqual(self._snapshot()["status"], "READY")
        self.reader.refresh()
        APP.processEvents()
        self._deliver(_body(status="SIGNED_OUT"))
        self.assertEqual(self._snapshot()["status"], "SIGNED_OUT")
        self.assertEqual(self._snapshot()["organizations"], [])
        self.reader.refresh()
        APP.processEvents()
        self._deliver(_body(status="NO_MEMBERSHIPS"))
        self.assertEqual(self._snapshot()["status"], "NO_MEMBERSHIPS")
        self.assertEqual(self._snapshot()["portfolios"], [])

    def test_provider_failure_clears_previous_company_metadata(self):
        self._open()
        self._deliver(_body())
        self.reader.refresh()
        APP.processEvents()
        self.process.finishWith("bad json", 1)
        APP.processEvents()
        self.assertIsNone(self._snapshot())

    def test_expired_grant_and_forged_portfolio_fail_closed(self):
        self._open()
        self._deliver(_body(expired=True))
        self.assertIsNone(self._snapshot())
        self.reader.refresh()
        APP.processEvents()
        forged = _body()
        forged["portfolios"][0]["organizationIds"].append("unrelated_customer")
        self._deliver(forged)
        self.assertIsNone(self._snapshot())

    def test_close_during_inflight_then_reopen_rejects_old_response(self):
        self._open()
        self.reader.setProperty("active", False)
        APP.processEvents()
        self.assertIsNone(self._snapshot())
        self.assertFalse(self.reader.property("acceptResponse"))
        # In-flight fake Process is still running and cannot be re-owned.
        self.reader.setProperty("active", True)
        APP.processEvents()
        self.assertFalse(self.reader.property("acceptResponse"))
        self._deliver(_body())
        self.assertIsNone(self._snapshot())
        self.reader.refresh()
        APP.processEvents()
        self._deliver(_body())
        self.assertEqual(self._snapshot()["status"], "READY")
        self.reader.setProperty("active", False)
        APP.processEvents()
        self.assertIsNone(self._snapshot())

    def test_null_or_extra_authority_never_becomes_a_display(self):
        self._open()
        malicious = _body()
        malicious["accessToken"] = "CI_ONLY_SECRET"
        self._deliver(malicious)
        self.assertIsNone(self._snapshot())
        self.reader.refresh()
        APP.processEvents()
        self.process.finishWith("null", 0)
        APP.processEvents()
        self.assertIsNone(self._snapshot())


if __name__ == "__main__":
    unittest.main()
