"""CPU++ ID editor source contracts: explicit local saves, no provider auth.

Static integration checks only. No Quickshell Wayland appearance or runtime
permission claim is inferred from these tests.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusIdManagementPane.qml").read_text(
    encoding="utf-8")
DETAIL = (ROOT / "widgets/cpuplus/CpuPlusIdDetailsEditor.qml").read_text(
    encoding="utf-8")
ACCOUNTS = (ROOT / "widgets/cpuplus/CpuPlusIdAccountEditor.qml").read_text(
    encoding="utf-8")
FIELD = (ROOT / "widgets/cpuplus/CpuPlusIdField.qml").read_text(
    encoding="utf-8")
POLICY = (ROOT / "services/social/SocialIdentityPolicy.js").read_text(
    encoding="utf-8")
STORE = (ROOT / "services/social/SocialIdentityStore.qml").read_text(
    encoding="utf-8")
DETAIL_STORE = (ROOT / "services/social/SocialAccountDetailsStore.qml").read_text(
    encoding="utf-8")


class CpuPlusIdEditorContracts(unittest.TestCase):
    def test_existing_three_column_geometry_and_main_mode_untouched(self):
        for snippet in ("implicitWidth: 1000", "implicitHeight: 834",
                        "width: 390", "width: 260", "height: 110",
                        "name: \"ID MANAGEMENT\"",
                        "id: idManagementOverviewPane",
                        "id: idManagementSelectorPane",
                        "id: idManagementDetailsPane"):
            self.assertIn(snippet, CPU)
        self.assertIn("idManagementSelectorPane.editingText", CPU)
        self.assertIn("idManagementDetailsPane.editingText", CPU)
        self.assertIn('selectedModeIndex === 5', CPU)

    def test_new_id_uses_existing_safe_create_choices(self):
        for snippet in ("+ NEW ID", "+ CREATE ID", "CANCEL NEW ID",
                        'key: "default"', 'key: "copy"', 'key: "empty"',
                        "SocialIdentityStore.createIdentity(",
                        "pane.effectiveId", "creationPending = true",
                        'SocialIdentityStore.storageState === "ready"',
                        'pane.idRequested("");',
                        "identityActionError"):
            self.assertIn(snippet, PANE)
        self.assertIn("next.activeId = id;", POLICY)
        self.assertIn("onSaved:", STORE)
        self.assertIn("atomicWrites: true", STORE)

    def test_stable_id_rename_and_error_feedback(self):
        for snippet in ("function renameIdentity(doc, id, name)",
                        "var next = clone(doc);",
                        "next.identities.find(function(item) { return item.id === id; }).name = title",
                        'reason:"DUPLICATE_NAME"',
                        'reason:"NO_CHANGE"'):
            self.assertIn(snippet, POLICY)
        self.assertIn("function renameIdentity(id, name)", STORE)
        self.assertIn("IdentityPolicy.renameIdentity(", STORE)
        self.assertEqual(STORE.count("FileView {"), 1)
        self.assertEqual(STORE.count("identityFile.setText("), 1)
        for snippet in ("SAVE NAME", "CANCEL", "SocialIdentityStore.renameIdentity(",
                        "pendingRenameId", "ID NAME SAVED // LOCAL",
                        "ID SAVE FAILED", "identityActionError",
                        "inspectedIdentity.id"):
            self.assertIn(snippet, DETAIL)

    def test_contact_save_pin_and_existing_private_account_store(self):
        for snippet in ("DEFAULT EMAIL", "DEFAULT PHONE",
                        "SAVE CONTACT", "CANCEL",
                        "SocialAccountDetailsStore.saveContact(",
                        "pendingContactId", "CONTACT SAVED // LOCAL",
                        "CONTACT SAVE FAILED"):
            self.assertIn(snippet, DETAIL)
        for snippet in ("function saveContact(identityId, email, phone)",
                        "function addAccountName(identityId, serviceId, label)",
                        "function renameAccountName(identityId, serviceId, accountId, label)",
                        "function removeAccountName(identityId, serviceId, accountId)"):
            self.assertIn(snippet, DETAIL_STORE)
        self.assertIn("return stage(result);", STORE)

    def test_linked_accounts_are_local_labels_with_confirmed_delete(self):
        for snippet in ("SocialAccountDetailsStore.accountNamesFor(",
                        "IdentityPolicy.APP_IDS", "storedRecord.accounts",
                        "SAVED SERVICES", "CHOOSE SERVICE",
                        "FILTER SERVICES", "SAVED NAMES",
                        "+ ACCOUNT NAME", "SAVE ACCOUNT NAME",
                        "CANCEL ACCOUNT EDIT", "REMOVE ACCOUNT NAME",
                        "CONFIRM REMOVE LABEL",
                        "SocialAccountDetailsStore.addAccountName(",
                        "SocialAccountDetailsStore.renameAccountName(",
                        "SocialAccountDetailsStore.removeAccountName(",
                        "LOCAL LABELS ONLY // NOT PROVIDER SIGN-IN STATUS"):
            self.assertIn(snippet, ACCOUNTS)
        self.assertIn("if (confirmRemoveId !== selectedAccountId)", ACCOUNTS)
        self.assertIn("pendingIdentityId === accountEditor.identityId", ACCOUNTS)

    def test_per_id_red_remove_and_guarded_two_click_confirmation(self):
        for snippet in ('label: "X"', "destructive: true",
                        "function armRemove(id, name)",
                        "function requestRemove()",
                        "function cancelRemove()",
                        "CONFIRM REMOVE ID", "CANCEL REMOVAL",
                        "pane.identities.length > 1",
                        "SocialIdentityStore.removeIdentity(",
                        "removeArmedId", "removeArmedName",
                        "pendingRemoveId", "LOCAL ID REMOVED",
                        'pane.idRequested("");',
                        "UNLINK ORGANIZATION LINKS FIRST",
                        "CLEAR CONTACT AND ACCOUNT NAMES FIRST",
                        "NO BACKUP REQUIRED" if False else "LAST_ID_REQUIRED"):
            self.assertIn(snippet, PANE)
        for snippet in ("function removeIdentity(doc, id)",
                        "if (doc.identities.length <= 1)",
                        "next.identities.splice(index, 1)",
                        "next.activeId = next.identities[0].id"):
            self.assertIn(snippet, POLICY)
        for snippet in ("function removeIdentity(id)",
                        "IdentityPolicy.removeIdentity(document, id)",
                        'SocialAccountDetailsStore.state !== "ready"',
                        'SocialOrganizationLinksStore.state !== "ready"',
                        'link.identityId === id',
                        "UNLINK_ORGANIZATION_FIRST",
                        "CLEAR_CONTACT_AND_ACCOUNT_NAMES_FIRST",
                        "Object.prototype.hasOwnProperty.call(saved, id)"):
            self.assertIn(snippet, STORE)
        self.assertEqual(STORE.count("FileView {"), 1)
        self.assertEqual(STORE.count("identityFile.setText("), 1)

    def test_input_semantics_and_no_bypass_writers(self):
        for snippet in ("color: Colors.magenta",
                        "color: Colors.orange",
                        "cursorDelegate: Component {",
                        "maximumLength: field.maxLength",
                        "Keys.onEscapePressed"):
            self.assertIn(snippet, FIELD)
        for source in (PANE, DETAIL, ACCOUNTS, FIELD):
            for forbidden in ("FileView {", "Process {",
                              "Qt.openUrlExternally(", "startLogin(",
                              "sendMessage(", "logout(", "session_token",
                              "accessToken:", "pkexec"):
                with self.subTest(forbidden=forbidden):
                    self.assertNotIn(forbidden, source)
        for source in (PANE, DETAIL, ACCOUNTS):
            self.assertNotIn("SocialIdentityStore.selectIdentity(", source)
        self.assertIn("selectedLocalIdForManagement = localId;", CPU)


if __name__ == "__main__":
    unittest.main()
