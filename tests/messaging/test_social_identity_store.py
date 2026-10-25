"""Social identity creation: storage/UI source boundaries, not QML runtime proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = (ROOT / "services/social/SocialIdentityPolicy.js").read_text()
STORE = (ROOT / "services/social/SocialIdentityStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
MESSAGING = (ROOT / "widgets/messanger/MessagingW.qml").read_text()


class SocialIdentitySourceContracts(unittest.TestCase):
    def test_isolated_module_and_atomic_single_writer(self):
        for expected in (
            "pragma Singleton", "import Quickshell.Io",
            'import "SocialIdentityPolicy.js" as IdentityPolicy',
            'Quickshell.dataDir + "/social-identities-v1.json"',
            "watchChanges: false", "atomicWrites: true",
            "printErrors: false", "onLoaded: identities.acceptLoaded(",
            "FileViewError.FileNotFound", "onSaveFailed: function(error)",
            'storageState = "error"',
            "onSaved:", 'property string storageState: "loading"',
        ):
            self.assertIn(expected, STORE)
        self.assertEqual(STORE.count("FileView {"), 1)
        self.assertEqual(STORE.count("identityFile.setText("), 1)
        self.assertIn("singleton SocialIdentityStore 1.0 SocialIdentityStore.qml", QMLDIR)
        for prohibited in ("Process {", "Timer {", "writeAdapter(",
                           "SystemTelemetry {", "Qt.openUrlExternally("):
            self.assertNotIn(prohibited, STORE)

    def test_user_intent_only_and_safe_fallback(self):
        self.assertIn("function createIdentity(name, mode, copyFromId)", STORE)
        self.assertIn("function selectIdentity(id)", STORE)
        self.assertIn('? "unsupported" : "error"', STORE)
        self.assertIn("identityFile.reload()", STORE)
        self.assertIn("pendingDocument = result.document", STORE)
        self.assertIn('storageState !== "ready" && storageState !== "empty"', STORE)
        self.assertIn("IdentityPolicy.initialDocument()", STORE)
        self.assertIn("IdentityPolicy.create(", STORE)
        self.assertIn("IdentityPolicy.select(", STORE)
        self.assertIn("function parse(raw)", POLICY)
        self.assertIn("function cloneLayout(layout)", POLICY)
        self.assertIn("function validLayout(layout)", POLICY)
        self.assertIn('mode !== "default" && mode !== "copy" && mode !== "empty"', POLICY)
        self.assertIn('next.activeId = id;', POLICY)

    def test_existing_launcher_and_settings_footer_unchanged(self):
        self.assertIn("import qs.services.social", SELECTOR)
        self.assertIn("SocialIdentityStore.snapshot", SELECTOR)
        self.assertIn("SocialIdentityStore.createIdentity(", SELECTOR)
        self.assertIn("SocialIdentityStore.selectIdentity(", SELECTOR)
        self.assertIn("onStorageStateChanged()", SELECTOR)
        self.assertIn("newIdentityName.text = \"\";", SELECTOR)
        self.assertIn('mode:"default"', SELECTOR)
        self.assertIn('mode:"copy"', SELECTOR)
        self.assertIn('mode:"empty"', SELECTOR)
        self.assertIn('text: "ALL APPS (TEMP)"', SELECTOR)
        self.assertIn("id: settingsFooter", SELECTOR)
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);", SELECTOR)
        self.assertIn("const count = appSelector.visibleAppIndices.length;", MESSAGING)
        self.assertIn("if (appSelector.settingsOpen) {", MESSAGING)
        self.assertNotIn("SocialIdentityStore", MESSAGING)
        self.assertNotIn("SocialIdentityStore", (ROOT / "services/messaging/SocialMessageRouter.qml").read_text())

    def test_no_auth_or_provider_actions(self):
        # Intentional separation: organization identity != authenticated
        # provider profile. Do not use a comment-string false-positive check.
        for prohibited in ("sendMessage(", "startLogin(", "logout(",
                           "POST_APOLLO_TELEGRAM_API_HASH",
                           "getPassword(", "setPassword("):
            self.assertNotIn(prohibited, POLICY + STORE)
        self.assertIn("Select layout only; NEVER trigger account login", POLICY)


if __name__ == "__main__":
    unittest.main()
