"""Social PHONE shows the configured Bluetooth device without unlocking content."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
HELPER = ROOT / "services/phone/PhoneDeviceObservation.py"


class PhoneDeviceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text(encoding="utf-8")

    def test_primary_connect_observes_device_without_repair_or_activation(self):
        start = self.ui.split("function startSetup() {", 1)[1].split(
            "\n    function openNativeSetup(", 1
        )[0]
        self.assertIn("refreshDeviceObservation();", start)
        self.assertIn('PhoneDeviceObservation.py', self.ui)
        self.assertIn('id: deviceObservationProcess', self.ui)
        self.assertIn('"--inspect"', self.ui)
        self.assertIn('phonePane.deviceObservationCheck = "CHECKED"', self.ui)

    def test_rendered_device_name_only_if_backend_profile_and_bluez_match(self):
        self.assertIn('observed.schema !== "post-apollo.phone.device-observation.v0"', self.ui)
        self.assertIn('observed.execution !== "READ_ONLY_DEVICE_OBSERVATION"', self.ui)
        self.assertIn('observed.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('observed.contentAccessEnabled !== false', self.ui)
        self.assertIn('observed.bluetoothLink !== "CONNECTED"', self.ui)
        self.assertIn('observed.bluetoothLink !== "PAIRED_OFFLINE"', self.ui)
        self.assertIn('textFormat: Text.PlainText', self.ui)
        self.assertIn('"IPHONE // " + phonePane.deviceObservation.displayName', self.ui)
        self.assertIn('Social messages and contacts: NOT LINKED.', self.ui)
        self.assertIn('No configured iPhone identity could be verified.', self.ui)

    def test_leave_phone_resets_observation_and_rechecks_after_stage(self):
        self.assertIn('deviceObservationCheck = "NOT CHECKED";', self.ui)
        self.assertIn('deviceObservation = ({});', self.ui)
        self.assertIn("phonePane.refreshDeviceObservation();", self.ui)

    def test_no_private_content_or_forged_connection_claim(self):
        self.assertIn("conversations: []", self.ui)
        self.assertIn("messages: []", self.ui)
        self.assertIn("sendEnabled: false", self.ui)
        self.assertNotIn('phonePane.deviceObservation.contentAccessEnabled = true', self.ui)
        self.assertNotIn("bluetoothctl remove", self.ui)
        self.assertNotIn("blueferry pair-setup", self.ui)
        self.assertIn("READ-ONLY SETUP PREVIEW", self.ui)
        self.assertTrue(HELPER.exists())


if __name__ == "__main__":
    unittest.main()
