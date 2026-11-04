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

from PySide6.QtCore import QObject, QUrl, QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "widgets/messanger/IdentityCenterOrganizationDisplayReader.qml"
SECTIONS_QML = ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml"
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


class RealQtOrganizationsSettingsPaneSmoke(unittest.TestCase):
    """Load the REAL embedded Organizations section, not just its IPC reader.

    Quickshell-only APIs are inert test stubs. The existing ActionButton,
    Colors, QtQuick Repeater/Flickable, section visibility and QML bindings
    are the actual repository components executed by the Qt 6 engine.
    """

    def setUp(self):
        self.engine = QQmlEngine()
        self.engine.addImportPath(str(STUBS))
        self.component = QQmlComponent(
            self.engine, QUrl.fromLocalFile(str(SECTIONS_QML))
        )
        self.assertTrue(
            self.component.isReady(),
            "Full settings QML failed native Qt loading:\n" +
            "\n".join(str(e) for e in self.component.errors()),
        )
        self.sections = self.component.create()
        self.assertIsNotNone(
            self.sections,
            "Full settings QML failed native Qt construction:\n" +
            "\n".join(str(e) for e in self.component.errors()),
        )
        self.sections.setProperty("width", 820)
        self.sections.setProperty("height", 560)
        self.process = self.sections.findChild(QObject, "ciSnapshotProcess")
        self.assertIsNotNone(self.process, "Embedded reader not instantiated")
        APP.processEvents()

    def tearDown(self):
        self.sections.setProperty("settingsOpen", False)
        APP.processEvents()
        self.sections.deleteLater()
        self.engine.deleteLater()
        APP.processEvents()

    def _display(self):
        return _value(self.sections.property("organizationDisplaySnapshot"))

    def _objects(self):
        # A Repeater's delegates may have a visual parent without being
        # QObject children of the enclosing QML Item. Traverse BOTH trees.
        found = []
        visited = set()
        queue = [self.sections]
        while queue:
            item = queue.pop(0)
            if item is None:
                continue
            identity = id(item)
            if identity in visited:
                continue
            visited.add(identity)
            found.append(item)
            queue.extend(item.children())
            if isinstance(item, QQuickItem):
                queue.extend(item.childItems())
        return found

    def _text(self, contains):
        return [
            node for node in self._objects()
            if isinstance(node.property("text"), str)
            and contains in node.property("text")
        ]

    def _open_organizations(self):
        self.sections.setProperty("activeSection", "ORGANIZATIONS")
        self.sections.setProperty("settingsOpen", True)
        APP.processEvents()
        self.assertTrue(self.process.property("running"))
        self.assertEqual(list(_value(self.process.property("command"))), [
            "/usr/bin/python3",
            "/ci-fake-shell/services/identity/identity_display_reader_cli_v0.py",
            "--json",
        ])

    def _finish(self, payload, status=0):
        self.process.finishWith(json.dumps(payload), status)
        APP.processEvents()

    def test_real_navigation_keeps_reader_dormant_until_orgs_are_open(self):
        self.assertEqual(self.sections.property("activeSection"), "SOCIAL LAYOUT")
        self.assertFalse(self.sections.property("settingsOpen"))
        self.assertFalse(self.process.property("running"))
        self.sections.setProperty("settingsOpen", True)
        APP.processEvents()
        self.assertFalse(self.process.property("running"))
        self.sections.setProperty("activeSection", "PROFILE")
        APP.processEvents()
        self.assertFalse(self.process.property("running"))
        self.assertIsNone(self._display())

    def test_real_organizations_panel_renders_only_synthetic_memberships(self):
        self._open_organizations()
        self._finish(_body())
        self.assertTrue(self.sections.property("organizationDisplayReady"))
        current = self._display()
        self.assertEqual([x["organizationId"] for x in current["organizations"]],
                         ["synthetic_llc", "synthetic_nonprofit"])
        self.assertTrue(
            self._text("synthetic_llc // LLC // 1 SCOPE PREVIEWS"),
            "Missing dynamic LLC repeater row; visible Qt texts: " +
            repr([x.property("text") for x in self._objects()
                  if isinstance(x.property("text"), str)])[:1600],
        )
        self.assertTrue(self._text("synthetic_nonprofit // NONPROFIT // 0 SCOPE PREVIEWS"))
        self.assertTrue(self._text("PORTFOLIOS // 1"))
        labels = [node for node in self._objects()
                  if node.property("label") == "SWITCH ORGANIZATION // UNAVAILABLE"]
        self.assertEqual(len(labels), 1)
        self.assertIs(labels[0].property("interactive"), False)
        self.assertTrue(self._text("ACTIVE ORGANIZATION // NONE VERIFIED"))
        self.assertNotIn("accessToken", repr(current))

    def test_tab_change_clears_rendered_organizations_and_ignores_late_reply(self):
        self._open_organizations()
        self._finish(_body())
        self.assertTrue(self.sections.property("organizationDisplayReady"))
        self.sections.setProperty("activeSection", "SECURITY")
        APP.processEvents()
        self.assertIsNone(self._display())
        self.assertFalse(self.sections.property("organizationDisplayReady"))
        self.sections.setProperty("activeSection", "ORGANIZATIONS")
        APP.processEvents()
        self.assertTrue(self.process.property("running"))
        self.sections.setProperty("settingsOpen", False)
        APP.processEvents()
        self.assertIsNone(self._display())
        self._finish(_body())
        self.assertIsNone(self._display())

    def test_inline_modifier_form_shares_original_organizations_page(self):
        self._open_organizations()
        modifier = self.sections.findChild(QObject, "orgModifierForm")
        self.assertIsNotNone(modifier, "Modifier form not constructed in real QML")
        self.assertIsNone(self.sections.findChild(QObject, "orgNavigationV2"))
        self.assertEqual(modifier.property("selectedOrgId"), "")
        self.assertFalse(modifier.property("validSelection"))
        for heading in (
            "MY ORGANIZATIONS // LOCAL DIRECTORY",
            "MY PORTFOLIOS // LOCAL GROUPS",
            "MY STRUCTURE // LOCAL ORGANIZATION UNITS",
            "ORGANIZATION LINKS // APPLY MODIFIER",
        ):
            self.assertTrue(self._text(heading), heading + " missing from inline view")
        # The form is visible and its original stores are not connected by
        # this synthetic reader-only fixture. It must never fake a save.
        self.assertFalse(modifier.property("directoryReady"))
        self.assertFalse(modifier.property("structureReady"))
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_shared_local_org_selector_keeps_structure_and_modifiers_in_sync(self):
        self._open_organizations()
        self.assertIsNotNone(
            self.sections.findChild(QObject, "orgLocalEditingContext")
        )
        structure = self.sections.findChild(QObject, "localStructureEditor")
        modifier = self.sections.findChild(QObject, "orgModifierForm")
        self.assertIsNotNone(structure)
        self.assertIsNotNone(modifier)
        self.assertTrue(structure.property("useSharedContext"))
        self.assertTrue(modifier.property("useSharedContext"))
        self.assertEqual(self.sections.property("activeLocalEditingOrganizationId"), "")

        # Disposable local Directory snapshot. No storage writes, authentication,
        # provider accounts or real company data.
        sample = {
            "state": "ready",
            "saved": {"organizations": [
                {"id": "org-1", "name": "FAKE LLC ONE", "kind": "llc",
                 "archived": False, "branches": []},
                {"id": "org-2", "name": "FAKE NONPROFIT", "kind": "nonprofit",
                 "archived": False, "branches": []},
                {"id": "org-3", "name": "FAKE ARCHIVED", "kind": "llc",
                 "archived": True, "branches": []},
            ]},
        }
        # A QML var needs a JS object with real JavaScript arrays; passing
        # a Python QVariantMap can lose Array.isArray and filter semantics.
        js_sample = self.engine.evaluate("(" + json.dumps(sample) + ")")
        self.assertFalse(js_sample.isError())
        self.assertTrue(self.sections.setProperty("localDirectoryStore", js_sample))
        APP.processEvents()
        self.sections.setProperty("localEditingOrganizationId", "org-1")
        APP.processEvents()
        self.assertEqual(
            self.sections.property("activeLocalEditingOrganizationId"), "org-1",
            "QML source: " + repr(self.sections.property("localDirectoryStore")) +
            " / choices: " + repr(_value(self.sections.property(
                "localOrganizationsForEditing"))),
        )
        self.assertEqual(structure.property("selectedOrgId"), "org-1")
        self.assertEqual(modifier.property("selectedOrgId"), "org-1")

        self.sections.setProperty("localEditingOrganizationId", "org-2")
        APP.processEvents()
        self.assertEqual(structure.property("selectedOrgId"), "org-2")
        self.assertEqual(modifier.property("selectedOrgId"), "org-2")

        # Archived and unknown IDs must fail closed.
        for invalid in ("org-3", "org-999", ""):
            self.sections.setProperty("localEditingOrganizationId", invalid)
            APP.processEvents()
            self.assertEqual(self.sections.property("activeLocalEditingOrganizationId"), "")
            self.assertEqual(structure.property("selectedOrgId"), "")
            self.assertEqual(modifier.property("selectedOrgId"), "")
            self.assertFalse(modifier.property("validSelection"))

    def test_unified_local_search_finds_records_without_new_menus(self):
        self._open_organizations()
        search = self.sections.findChild(QObject, "orgLocalSearch")
        self.assertIsNotNone(search)
        self.assertEqual(search.property("searchText"), "")
        self.assertEqual(search.property("matchCount"), 0)

        # Genuine JS arrays, exactly as the JSON-backed local stores expose,
        # but entirely synthetic and disconnected from user data.
        fixtures = {
            "localDirectoryStore": {"state": "ready", "saved": {
                "organizations": [
                    {"id": "org-1", "name": "Acme Learning", "kind": "llc",
                     "archived": False, "branches": [
                         {"id": "branch-4", "name": "Bethesda Office",
                          "archived": False}]},
                    {"id": "org-2", "name": "Bright Foundation",
                     "kind": "nonprofit", "archived": False, "branches": []},
                    {"id": "org-3", "name": "Archived Ventures",
                     "kind": "llc", "archived": True, "branches": []},
                ]}},
            "localPortfoliosStore": {"state": "ready", "saved": {
                "portfolios": [
                    {"id": "portfolio-1", "name": "Development Partners",
                     "orgIds": ["org-1", "org-2"], "archived": False}]}},
            "localStructureStore": {"state": "ready", "saved": {
                "units": [
                    {"id": "unit-1", "orgId": "org-1", "kind": "division",
                     "name": "Education", "archived": False},
                    {"id": "unit-2", "orgId": "org-2", "kind": "team",
                     "name": "Outreach", "archived": False},
                    {"id": "unit-3", "orgId": "org-3", "kind": "department",
                     "name": "Legacy Lab", "archived": True},
                    {"id": "unit-4", "orgId": "org-1", "kind": "location",
                     "name": "Washington", "archived": False},
                ]}},
            "localUnitLocationLinksStore": {"state": "ready", "saved": {
                "links": [{"id": "unit-location-1", "orgId": "org-1",
                           "functionId": "unit-1", "locationId": "unit-4"}]}},
            "localBranchLocationLinksStore": {"state": "ready", "saved": {
                "links": [{"id": "branch-location-1", "orgId": "org-1",
                           "branchId": "branch-4", "locationId": "unit-4"}]}},
            "localFunctionalReportingStore": {"state": "ready", "saved": {
                "links": []}},
            "localLinksStore": {"state": "ready", "saved": {
                "links": [{"id": "social-link-1", "orgId": "org-2",
                           "branchId": None, "identityId": "identity-1",
                           "serviceId": None, "accountId": None}]}},
            "socialIdentitiesSnapshot": {"writable": True, "identities": [
                {"id": "identity-1", "name": "Public Outreach"}]},
        }
        for name, data in fixtures.items():
            snapshot = self.engine.evaluate("(" + json.dumps(data) + ")")
            self.assertFalse(snapshot.isError(), name)
            self.assertTrue(self.sections.setProperty(name, snapshot), name)
        APP.processEvents()

        def results(term, scope="all", archived=False):
            search.setProperty("scope", scope)
            search.setProperty("includeArchived", archived)
            search.setProperty("searchText", term)
            APP.processEvents()
            return _value(search.property("visibleMatches"))

        branches = results("Bethesda", "organizations")
        self.assertEqual(len(branches), 1, branches)
        self.assertIn("Bethesda Office", branches[0]["label"])
        self.assertEqual(branches[0]["orgId"], "org-1")
        self.assertEqual(search.property("matchCount"), 1)

        membership = results("Bright Foundation", "portfolios")
        self.assertEqual(len(membership), 1, membership)
        self.assertIn("Development Partners", membership[0]["label"])

        units = results("Education", "units")
        self.assertEqual(len(units), 1, units)
        self.assertEqual(units[0]["kind"], "division")

        self.assertEqual(results("Legacy Lab", "units"), [])
        hidden = results("Legacy Lab", "units", archived=True)
        self.assertEqual(len(hidden), 1)
        self.assertTrue(hidden[0]["archived"])

        saved = results("Washington", "links")
        self.assertEqual(len(saved), 2, saved)
        self.assertTrue(all("LOCATED AT" in x["label"] for x in saved))

        social = results("Public Outreach", "links")
        self.assertEqual(len(social), 1, social)
        self.assertIn("SOCIAL LABEL", social[0]["label"])

        self.sections.setProperty("localEditingOrganizationId", "org-1")
        APP.processEvents()
        structure = self.sections.findChild(QObject, "localStructureEditor")
        self.assertIsNotNone(structure)
        result = results("Washington", "units")
        self.assertEqual(len(result), 1)
        # Search crosses unit categories even when division remains selected.
        self.assertEqual(structure.property("selectedKind"), "division")
        visible_units = _value(structure.property("visibleUnits"))
        self.assertEqual(len(visible_units), 1, visible_units)
        self.assertEqual(visible_units[0]["kind"], "location")

        search.setProperty("searchText", "")
        APP.processEvents()
        self.assertEqual(search.property("matchCount"), 0)
        self.assertEqual(structure.property("searchQuery"), "")
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_one_archived_toggle_updates_all_inline_record_editors(self):
        self._open_organizations()
        search = self.sections.findChild(QObject, "orgLocalSearch")
        directory = self.sections.findChild(QObject, "orgLocalDirectoryEditor")
        portfolios = self.sections.findChild(QObject, "orgLocalPortfolioEditor")
        structure = self.sections.findChild(QObject, "localStructureEditor")
        archive_button = self.sections.findChild(QObject, "localShowArchivedRecords")
        for name, obj in (
            ("search", search), ("directory", directory),
            ("portfolios", portfolios), ("structure", structure),
            ("global archived button", archive_button),
        ):
            self.assertIsNotNone(obj, name + " missing from real QML")
        for obj, field in ((directory, "showArchived"),
                           (portfolios, "showArchived"),
                           (structure, "showArchivedUnits")):
            self.assertFalse(obj.property(field))
            self.assertTrue(obj.property("useSharedArchiveControl"))
        self.assertFalse(search.property("includeArchived"))

        fixtures = {
            "localDirectoryStore": {"state": "ready", "saved": {
                "organizations": [
                    {"id": "org-1", "name": "FAKE ACTIVE", "kind": "llc",
                     "archived": False, "branches": [
                         {"id": "branch-4", "name": "FAKE ARCHIVED BRANCH",
                          "archived": True}]},
                    {"id": "org-2", "name": "FAKE ARCHIVED COMPANY",
                     "kind": "nonprofit", "archived": True, "branches": []},
                ]}},
            "localPortfoliosStore": {"state": "ready", "saved": {
                "portfolios": [
                    {"id": "portfolio-1", "name": "FAKE ARCHIVED GROUP",
                     "orgIds": ["org-1"], "archived": True}]}},
            "localStructureStore": {"state": "ready", "saved": {
                "units": [
                    {"id": "unit-1", "orgId": "org-1",
                     "kind": "division", "name": "FAKE ACTIVE DIVISION",
                     "archived": False},
                    {"id": "unit-2", "orgId": "org-1",
                     "kind": "division", "name": "FAKE ARCHIVED DIVISION",
                     "archived": True},
                ]}},
        }
        for field, value in fixtures.items():
            js = self.engine.evaluate("(" + json.dumps(value) + ")")
            self.assertFalse(js.isError(), field)
            self.assertTrue(self.sections.setProperty(field, js), field)
        self.sections.setProperty("localEditingOrganizationId", "org-1")
        APP.processEvents()
        self.assertEqual(len(_value(structure.property("visibleUnits"))), 1)

        for obj in (directory, portfolios, structure):
            obj.setProperty("confirmationKey", "stale confirmation")
        # The actual page-wide archive button updates this same property.
        self.assertTrue(search.setProperty("includeArchived", True))
        APP.processEvents()
        for obj, field in ((directory, "showArchived"),
                           (portfolios, "showArchived"),
                           (structure, "showArchivedUnits")):
            self.assertTrue(obj.property(field), field)
            self.assertEqual(obj.property("confirmationKey"), "", field)
        self.assertEqual(len(_value(structure.property("visibleUnits"))), 2)

        search.setProperty("scope", "organizations")
        search.setProperty("searchText", "ARCHIVED COMPANY")
        APP.processEvents()
        self.assertEqual(search.property("matchCount"), 1)
        self.assertTrue(_value(search.property("visibleMatches"))[0]["archived"])

        search.setProperty("includeArchived", False)
        APP.processEvents()
        self.assertEqual(search.property("matchCount"), 0)
        # Restore the unfiltered Structure list before checking its normal
        # active/archived unit count. A search for "ARCHIVED COMPANY" correctly
        # matches no units regardless of visibility.
        search.setProperty("searchText", "")
        APP.processEvents()
        for obj, field in ((directory, "showArchived"),
                           (portfolios, "showArchived"),
                           (structure, "showArchivedUnits")):
            self.assertFalse(obj.property(field), field)
        self.assertEqual(len(_value(structure.property("visibleUnits"))), 1)
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_inline_save_feedback_uses_actual_revision_and_errors(self):
        self._open_organizations()
        feedback = self.sections.findChild(QObject, "orgLocalSaveFeedback")
        self.assertIsNotNone(feedback, "Save status missing from real Organizations QML")
        self.assertEqual(feedback.property("lastKind"), "neutral")
        self.assertIn("No write in progress", feedback.property("displayedStatus"))

        def state(field, value, revision, error=""):
            payload = {"state": value, "errorCode": error,
                       "saved": {"revision": revision}}
            js = self.engine.evaluate("(" + json.dumps(payload) + ")")
            self.assertFalse(js.isError(), field)
            self.assertTrue(self.sections.setProperty(field, js), field)
            APP.processEvents()

        state("localDirectoryStore", "ready", 3)
        self.assertNotIn("SAVED //", feedback.property("displayedStatus"))

        state("localDirectoryStore", "saving", 3)
        self.assertEqual(feedback.property("savingCount"), 1)
        self.assertIn("Not yet saved", feedback.property("displayedStatus"))
        self.assertNotIn("SAVED //", feedback.property("displayedStatus"))

        state("localDirectoryStore", "ready", 4)
        self.assertEqual(feedback.property("savingCount"), 0)
        self.assertEqual(feedback.property("lastKind"), "saved")
        self.assertIn("SAVED // Organizations / Branches",
                      feedback.property("displayedStatus"))
        self.assertIn("revision 4", feedback.property("displayedStatus"))

        # An asynchronous method returning true is merely queue admission:
        # if the writer fails, READY must never be inferred from the click.
        state("localDirectoryStore", "saving", 4)
        state("localDirectoryStore", "error", 4, "REVISION_CONFLICT")
        self.assertEqual(feedback.property("lastKind"), "conflict")
        self.assertTrue(feedback.property("hasConflict"))
        self.assertIn("REVISION_CONFLICT", feedback.property("displayedStatus"))
        self.assertNotIn("SAVED //", feedback.property("displayedStatus"))

        # An explicit read-only reload clears the error but must not become
        # a false write confirmation.
        state("localDirectoryStore", "loading", 4)
        state("localDirectoryStore", "ready", 4)
        self.assertEqual(feedback.property("lastKind"), "loaded")
        self.assertIn("RELOADED //", feedback.property("displayedStatus"))
        self.assertFalse(feedback.property("hasConflict"))

        # Test a second independent store without changing the original one.
        state("localPortfoliosStore", "ready", 11)
        state("localPortfoliosStore", "saving", 11)
        state("localPortfoliosStore", "ready", 12)
        self.assertIn("SAVED // Portfolios", feedback.property("displayedStatus"))
        self.assertIn("revision 12", feedback.property("displayedStatus"))

        # A store returning READY without a revision increment is unconfirmed.
        state("localPortfoliosStore", "saving", 12)
        state("localPortfoliosStore", "ready", 12)
        self.assertEqual(feedback.property("lastKind"), "unconfirmed")
        self.assertIn("NOT CONFIRMED //", feedback.property("displayedStatus"))
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_one_refresh_button_blocks_saves_and_avoids_duplicate_reads(self):
        self._open_organizations()
        refresher = self.sections.findChild(QObject, "orgLocalRefreshAll")
        button = self.sections.findChild(QObject, "orgRefreshAllButton")
        self.assertIsNotNone(refresher)
        self.assertIsNotNone(button)
        self.assertFalse(refresher.property("canRefresh"))

        sources = (
            ("localDirectoryStore", "organizations"),
            ("localPortfoliosStore", "portfolios"),
            ("localStructureStore", "units"),
            ("localUnitLocationLinksStore", "links"),
            ("localBranchLocationLinksStore", "links"),
            ("localFunctionalReportingStore", "links"),
            ("localLinksStore", "links"),
        )

        def inject(name, list_key, status, error="", allow=True):
            fixture = {"state": status, "errorCode": error,
                       "saved": {"revision": 3, list_key: []}, "calls": 0}
            source = ("(function(){var entry = " + json.dumps(fixture) +
                      "; entry.refresh = function(){this.calls += 1; return " +
                      ("true" if allow else "false") +
                      ";}; return entry;})()")
            value = self.engine.evaluate(source)
            self.assertFalse(value.isError(), name)
            self.assertTrue(self.sections.setProperty(name, value), name)
            APP.processEvents()
        for name, key in sources:
            inject(name, key, "ready")
        self.assertTrue(refresher.property("canRefresh"))
        self.assertEqual(refresher.property("missingCount"), 0)
        self.assertTrue(button.property("interactive"))

        # A saving store prevents the whole coordinated refresh rather than
        # launching partial reads or interrupting the asynchronous writer.
        inject(sources[0][0], sources[0][1], "saving")
        self.assertFalse(refresher.property("canRefresh"))
        self.assertFalse(button.property("interactive"))
        self.assertTrue(QMetaObject.invokeMethod(refresher, "requestRefresh"))
        self.assertEqual(refresher.property("acceptedRefreshCount"), 0)
        self.assertIn("NOT STARTED", refresher.property("lastRefreshResult"))

        inject(sources[0][0], sources[0][1], "ready")
        self.assertTrue(refresher.property("canRefresh"))
        self.assertTrue(QMetaObject.invokeMethod(refresher, "requestRefresh"))
        self.assertEqual(refresher.property("acceptedRefreshCount"), 7)
        self.assertTrue(refresher.property("refreshInProgress"))
        self.assertIn("7 local stores", refresher.property("lastRefreshResult"))

        def count_calls(name):
            value = self.sections.property(name)
            return value.property("calls").toInt()
        self.assertEqual([count_calls(name) for name, _ in sources], [1] * 7)

        # Even invoking the QML method a second time directly must not
        # queue new refreshes while the first is in progress.
        self.assertTrue(QMetaObject.invokeMethod(refresher, "requestRefresh"))
        self.assertEqual([count_calls(name) for name, _ in sources], [1] * 7)
        self.assertFalse(refresher.property("canRefresh"))
        for name, key in sources:
            inject(name, key, "loading")
        self.assertGreater(refresher.property("loadingCount"), 0)
        self.assertFalse(button.property("interactive"))
        for name, key in sources:
            inject(name, key, "ready")
        self.assertFalse(
            refresher.property("refreshInProgress"),
            "inflight=" + str(refresher.property("refreshInProgress"))
            + " signature=" + str(refresher.property("stateSignature"))
            + " loading=" + str(refresher.property("loadingCount"))
            + " result=" + str(refresher.property("lastRefreshResult")))
        self.assertIn("REFRESH COMPLETE", refresher.property("lastRefreshResult"))
        self.assertTrue(refresher.property("canRefresh"))

        # Backend refresh/read errors are visible and never called a save.
        self.assertTrue(QMetaObject.invokeMethod(refresher, "requestRefresh"))
        for name, key in sources:
            inject(name, key, "loading")
        for name, key in sources[:-1]:
            inject(name, key, "ready")
        inject(sources[-1][0], sources[-1][1], "error", "READ_UNAVAILABLE")
        self.assertIn("REFRESH ENDED WITH ERRORS",
                      refresher.property("lastRefreshResult"))
        self.assertIn("READ_UNAVAILABLE", refresher.property("lastRefreshResult"))
        self.assertNotIn("SAVED //", refresher.property("lastRefreshResult"))
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_private_backup_buttons_are_inline_and_restore_remains_locked(self):
        self._open_organizations()
        backup = self.sections.findChild(QObject, "orgLocalBackup")
        process = self.sections.findChild(QObject, "orgBackupProcess")
        create = self.sections.findChild(QObject, "orgBackupCreateButton")
        listing = self.sections.findChild(QObject, "orgBackupListButton")
        verify = self.sections.findChild(QObject, "orgBackupValidateButton")
        restore = self.sections.findChild(QObject, "orgBackupRestoreLockedButton")
        for name, obj in (("backup", backup), ("process", process),
                          ("create", create), ("list", listing),
                          ("verify", verify), ("restore", restore)):
            self.assertIsNotNone(obj, name)
        self.assertFalse(backup.property("sourcesReady"))
        self.assertFalse(create.property("interactive"))
        self.assertFalse(restore.property("interactive"))

        fixture_names = (
            ("localDirectoryStore", "organizations"),
            ("localPortfoliosStore", "portfolios"),
            ("localStructureStore", "units"),
            ("localUnitLocationLinksStore", "links"),
            ("localBranchLocationLinksStore", "links"),
            ("localFunctionalReportingStore", "links"),
            ("localLinksStore", "links"),
        )
        for field, records in fixture_names:
            doc = {"state": "ready", "saved": {"revision": 1, records: []}}
            js = self.engine.evaluate("(" + json.dumps(doc) + ")")
            self.assertFalse(js.isError())
            self.assertTrue(self.sections.setProperty(field, js))
        APP.processEvents()
        self.assertTrue(backup.property("sourcesReady"))
        self.assertTrue(create.property("interactive"))

        # Real QML function + fake OS process: no disk or live app touched.
        self.assertTrue(backup.runAction("create"))
        self.assertTrue(backup.property("busy"))
        self.assertFalse(create.property("interactive"))
        self.assertTrue(process.property("running"))
        self.assertIn("BACKUP WORKING", backup.property("resultText"))
        self.assertFalse(restore.property("interactive"))

        filename = "org-backup-20261104T012300Z-aabbcc112233.json"
        process.finishWith(json.dumps({
            "ok": True, "backup": filename, "createdAt": "2026-11-04T01:23:00Z",
            "inventory": {}, "restored": False
        }), 0)
        APP.processEvents()
        self.assertFalse(backup.property("busy"))
        self.assertEqual(backup.property("selectedBackup"), filename)
        self.assertIn("BACKUP CREATED", backup.property("resultText"))
        self.assertTrue(verify.property("interactive"))
        self.assertFalse(restore.property("interactive"))

        self.assertTrue(backup.runAction("verify"))
        self.assertTrue(backup.property("busy"))
        process.finishWith(json.dumps({
            "ok": True, "valid": True, "backup": filename,
            "createdAt": "2026-11-04T01:23:00Z",
            "inventory": {}, "restoreAvailable": False
        }), 0)
        APP.processEvents()
        self.assertIn("VALID BACKUP", backup.property("resultText"))
        self.assertIn("RESTORE NOT ENABLED", backup.property("resultText"))
        self.assertFalse(restore.property("interactive"))

        self.assertTrue(backup.runAction("list"))
        process.finishWith(json.dumps({
            "ok": True, "backups": [filename], "total": 1,
            "folder": "organization-backups-v1"
        }), 0)
        APP.processEvents()
        self.assertEqual(len(_value(backup.property("backups"))), 1)
        self.assertIn("BACKUPS LISTED", backup.property("resultText"))
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_current_session_activity_observes_results_only(self):
        self._open_organizations()
        activity = self.sections.findChild(QObject, "orgLocalSessionActivity")
        backup = self.sections.findChild(QObject, "orgLocalBackup")
        self.assertIsNotNone(activity)
        self.assertIsNotNone(backup)
        self.assertTrue(activity.property("recordingEnabled"))
        self.assertEqual(activity.property("entryCount"), 0)

        def state(value, revision, error=""):
            payload = {"state": value, "errorCode": error,
                       "saved": {"revision": revision}}
            js = self.engine.evaluate("(" + json.dumps(payload) + ")")
            self.assertFalse(js.isError())
            self.assertTrue(self.sections.setProperty("localDirectoryStore", js))
            APP.processEvents()

        # Loading a baseline does not invent an earlier save.
        state("ready", 3)
        self.assertEqual(activity.property("entryCount"), 0)
        state("saving", 3)
        self.assertEqual(activity.property("entryCount"), 0)
        state("ready", 4)
        events = _value(activity.property("entries"))
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0]["kind"], "saved")
        self.assertIn("revision 4", events[0]["detail"])
        self.assertTrue(events[0]["observedAt"])

        state("saving", 4)
        state("error", 4, "REVISION_CONFLICT")
        events = _value(activity.property("entries"))
        self.assertEqual(len(events), 2, events)
        self.assertEqual(events[0]["kind"], "conflict")
        self.assertIn("REVISION_CONFLICT", events[0]["detail"])

        state("loading", 4)
        state("ready", 4)
        events = _value(activity.property("entries"))
        self.assertEqual(len(events), 3, events)
        self.assertEqual(events[0]["kind"], "loaded")
        self.assertNotIn("SAVED //", events[0]["detail"])

        # A synthetic success response, not a real filesystem backup.
        backup.setProperty("operation", "list")
        backup.setProperty("readText", json.dumps({
            "ok": True, "backups": [], "total": 0,
            "folder": "organization-backups-v1",
        }))
        backup.acceptResponse(0)
        APP.processEvents()
        events = _value(activity.property("entries"))
        self.assertEqual(len(events), 4, events)
        self.assertEqual(events[0]["kind"], "listing")
        self.assertEqual(events[0]["source"], "Private Backups")

        # The observer is intentionally bounded and not recording while
        # a different Settings page is active.
        for number in range(45):
            self.assertTrue(activity.appendEvent(
                "listing", "FICTIONAL", "synthetic-" + str(number)))
        self.assertEqual(activity.property("entryCount"), 40)
        self.assertEqual(len(_value(activity.property("visibleEntries"))), 6)
        activity.setProperty("showAll", True)
        APP.processEvents()
        self.assertEqual(len(_value(activity.property("visibleEntries"))), 40)

        self.sections.setProperty("activeSection", "SOCIAL LAYOUT")
        APP.processEvents()
        self.assertFalse(activity.property("recordingEnabled"))
        self.assertFalse(activity.appendEvent("listing", "HIDDEN", "not observed"))
        self.assertEqual(activity.property("entryCount"), 40)

        # This clears only the in-memory view, no store or backup file.
        activity.setProperty("entries", [])
        APP.processEvents()
        self.assertEqual(activity.property("entryCount"), 0)
        self.assertFalse(self.sections.property("organizationDisplayReady"))

    def test_host_logout_and_failure_are_reflected_in_real_panel(self):
        self._open_organizations()
        self._finish(_body())
        self.assertTrue(self.sections.property("organizationDisplayReady"))
        self.sections.setProperty("settingsOpen", False)
        APP.processEvents()
        self.sections.setProperty("settingsOpen", True)
        APP.processEvents()
        self._finish(_body(status="SIGNED_OUT"))
        self.assertFalse(self.sections.property("organizationDisplayReady"))
        self.assertEqual(self._display()["status"], "SIGNED_OUT")
        self.assertEqual(self._display()["organizations"], [])
        self.assertTrue(self._text("NOT CONNECTED // TRUSTED BACKEND REQUIRED"))
        self.sections.setProperty("settingsOpen", False)
        APP.processEvents()
        self.sections.setProperty("settingsOpen", True)
        APP.processEvents()
        self.process.finishWith("not-json", 1)
        APP.processEvents()
        self.assertIsNone(self._display())


if __name__ == "__main__":
    unittest.main()
