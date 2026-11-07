"""CPU++ Identity Center context viewer safety and geometry contracts.

The real JSON schema, lifecycle and separate-process transport are tested in
the existing Identity Center suites. These source tests protect the new
CPU++ consumer boundary, not a production login or permission system.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusIdManagementPane.qml").read_text(
    encoding="utf-8")
HOST_VIEW = (ROOT / "widgets/cpuplus/CpuPlusIdVerifiedContextPane.qml").read_text(
    encoding="utf-8")
READER = (ROOT / "widgets/messanger/IdentityCenterOrganizationDisplayReader.qml").read_text(
    encoding="utf-8")
CLI = (ROOT / "services/identity/identity_display_reader_cli_v0.py").read_text(
    encoding="utf-8")


class CpuPlusIdentityHostContextContracts(unittest.TestCase):
    def test_uses_existing_cpuplus_overview_not_an_extra_window(self):
        for expected in (
            "implicitWidth: 1000", "implicitHeight: 834",
            "id: modeRail", "height: 110",
            "id: sharedInstrumentPane", "width: 390",
            "id: targetPane", "width: 260",
            "id: actuatorPane", 'name: "ID MANAGEMENT"',
            "id: idManagementOverviewPane",
            "id: idManagementSelectorPane",
            "id: idManagementDetailsPane",
        ):
            self.assertIn(expected, CPU)
        self.assertIn("CpuPlusIdVerifiedContextPane {", PANE)
        self.assertIn("id: verifiedHostContextPane", PANE)
        self.assertIn('activeMode: pane.area === "overview" && pane.visible', PANE)
        self.assertEqual(PANE.count("CpuPlusIdVerifiedContextPane {"), 1)
        self.assertNotIn("PanelWindow {", HOST_VIEW)
        self.assertNotIn("FloatingWindow {", HOST_VIEW)

    def test_existing_read_only_host_reader_reused_with_opt_in_lifecycle(self):
        for expected in (
            'import "../messanger"',
            "IdentityCenterOrganizationDisplayReader {",
            "id: contextReader",
            "active: view.activeMode && view.expanded",
            "onActiveModeChanged:",
            "if (!activeMode)",
            "expanded = false;",
            "readonly property var display: contextReader.snapshot",
            "CHECK HOST CONTEXT",
            "HIDE HOST CONTEXT",
            "REFRESH HOST CONTEXT",
            "onClicked: contextReader.refresh()",
            "NOT CONNECTED",
            "NO_MEMBERSHIPS",
            "SIGNED_OUT",
        ):
            self.assertIn(expected, HOST_VIEW)
        self.assertIn('interval: 5000', READER)
        self.assertIn("clear();", READER)
        self.assertIn("function validDisplay(view)", READER)
        self.assertIn('identity_display_reader_cli_v0.py', READER)
        self.assertIn('SOCKET_NAME, empty_display, read_private_display', CLI)

    def test_only_host_display_schema_can_expose_membership_previews(self):
        for expected in (
            'display.schema === "post-apollo.identity.desktop-context-display.v0"',
            'display.status === "READY"',
            'display.canSwitchOrganization === false',
            'Array.isArray(display.organizations)',
            'Array.isArray(display.portfolios)',
            'model: view.displayReady ? view.display.organizations : []',
            'model: orgRow.modelData.scopeGrants',
            'model: view.displayReady ? view.display.portfolios : []',
            'modelData.organizationId', 'modelData.scopeGrants.length',
            'modelData.action.toUpperCase()',
            'modelData.divisionId', 'modelData.unitId',
            'modelData.expiresAt',
        ):
            self.assertIn(expected, HOST_VIEW)
        self.assertNotIn('model: pane.identities', HOST_VIEW)
        self.assertNotIn('SocialIdentityStore.', HOST_VIEW)
        self.assertNotIn('SocialOrganizationLinksStore.', HOST_VIEW)
        self.assertNotIn('selectedId:', HOST_VIEW)
        self.assertNotIn('identityId:', HOST_VIEW)

    def test_no_claim_of_role_switch_or_authority_from_display(self):
        for expected in (
            "DISPLAY PREVIEW ONLY",
            "EVERY BUSINESS",
            "OPERATION MUST BE REAUTHORIZED BY THE SERVER.",
            "NO PERSON ID, ROLE EDITOR",
            "HOST MEMBERSHIPS ARE SEPARATE FROM LOCAL SOCIAL IDS",
        ):
            self.assertIn(expected, HOST_VIEW)
        for source in (HOST_VIEW, PANE):
            for prohibited in (
                "startLogin(", "beginLogin(", "selectOrganization(",
                "setPermission(", "grantPermission(", "assignRole(",
                "scopeGrants.push(", "Qt.openUrlExternally(",
                "Authorization:", "Bearer ", "refreshToken",
                "id_token", "accessToken", "client_secret",
            ):
                with self.subTest(prohibited=prohibited):
                    self.assertNotIn(prohibited, source)
        for prohibited in (
            "Process {", "FileView {", "Socket {", "WebSocket {",
            "XMLHttpRequest", "HttpRequest", "LocalStorage",
        ):
            self.assertNotIn(prohibited, HOST_VIEW)
        self.assertIn("No host is installed/activated", READER)
        self.assertIn("no: XDG_RUNTIME_DIR", CLI)

    def test_editor_still_reuses_local_store_without_host_grant(self):
        for expected in (
            "SocialIdentityStore.createIdentity(",
            "SocialIdentityStore.removeIdentity(",
            "CpuPlusIdDetailsEditor {",
            'label: "X"',
            "CONFIRM REMOVE ID",
        ):
            self.assertIn(expected, PANE)
        self.assertNotIn("contextReader.snapshot", PANE)
        self.assertNotIn("SocialIdentityStore.selectIdentity(", HOST_VIEW)


if __name__ == "__main__":
    unittest.main()
