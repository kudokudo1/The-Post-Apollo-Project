"""P23 PHONE storage visibility, explicit BlueFerry keyring unlock UI contract.

Read-only source tests only. This does NOT run Quickshell, unlock a real wallet,
read any real message, change Bluetooth pairing, or install a desktop service.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
STORAGE = ROOT / "services/phone/PhoneBlueFerryStorageUi.py"
READ = ROOT / "services/phone/PhoneRememberedRead.py"


class PhoneStorageUnlockUiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = PANE.read_text()
        cls.storage = STORAGE.read_text()
        cls.read = READ.read_text()

    def test_explicit_unlock_button_in_existing_phone_not_new_window(self):
        for item in (
            'id: phoneStorageSettings',
            '"UNLOCK LOCAL DATA"',
            '"RETRY UNLOCK LOCAL DATA"',
            '"UNLOCK DATA"',
            'function unlockBlueFerryStorage()',
            'phonePane.unlockBlueFerryStorage()',
            '"--unlock"',
            'id: phoneStorageUnlockProcess',
            'PhoneBlueFerryStorageUi.py',
            'visible: phonePane.setupState === "CHECKED"',
        ):
            with self.subTest(item=item):
                self.assertIn(item, self.pane)
        self.assertIn('id: setupOverlay', self.pane)
        self.assertIn('id: phoneContactList', self.pane)
        self.assertIn('sendEnabled: false', self.pane)
        self.assertNotIn('storage-reset', self.pane)

    def test_status_is_safe_and_does_not_unlock_or_pair(self):
        for item in (
            'function checkBlueFerryStorage()',
            'id: phoneStorageStatusProcess',
            '"--status"',
            'interval: 12500',
            'phonePane.checkBlueFerryStorage()',
            'phoneStorageStatusProcess.running',
            'phoneStorageUnlockProcess.running',
            'phoneStorageGeneration += 1;',
        ):
            self.assertIn(item, self.pane)
        self.assertNotIn("    Component.onCompleted: phonePane.unlockBlueFerryStorage()", self.pane)
        self.assertNotIn("blueferry storage-policy-set", self.pane)
        self.assertNotIn("ResetStorage(", self.storage)
        self.assertNotIn("SetStoragePolicy(", self.storage)
        self.assertNotIn("ClearHistory(", self.storage)
        self.assertIn('operation == "--status"', self.storage)
        self.assertIn('if operation == "--status":', self.storage)
        self.assertIn('if state != "LOCKED" or policy != "encrypted":', self.storage)

    def test_explicit_click_unlocks_and_retries_authorized_snapshot(self):
        for marker in (
            'if (phonePane.phoneStorageState === "LOCKED"',
            'phonePane.unlockBlueFerryStorage();',
            'if (reply.state === "READY" && phonePane.personalApproved',
            '!phonePane.personalNeedsExplicitReload',
            'phonePane.loadPersonalSnapshot();',
            '"UNLOCKING"',
            '"UNLOCK_FAILED"',
            'phoneReadAdapter.forgetHostView();',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.pane)
        # A storage unlock must never manufacture a read permission.
        self.assertNotIn('phonePane.savePersonalApproval("b")', self.storage)
        self.assertIn('function savePersonalApproval(choice)', self.pane)
        self.assertIn('function revokePersonalAccess()', self.pane)
        self.assertIn('"--revoke"', self.pane)

    def test_storage_state_is_not_same_as_social_approval(self):
        for marker in (
            'property string phoneStorageState: "UNKNOWN"',
            'property string phoneStoragePolicy: "unknown"',
            '"BLUEFERRY STORAGE LOCKED //',
            '"NO_RETENTION"',
            '"BLUEFERRY ENCRYPTED LOCAL DATA // READY."',
            '"BLUEFERRY STORAGE SERVICE NOT AVAILABLE',
            '"BLUEFERRY DOES NOT RETAIN LOCAL DATA',
            'Other apps running as your Linux user',
        ):
            self.assertIn(marker, self.pane)
        self.assertIn('contactCards', self.pane)
        self.assertIn('PhoneAdapters.BlueFerryAdapter', self.pane)
        self.assertNotIn("UnlockStorage(", self.read)


if __name__ == "__main__":
    unittest.main()
