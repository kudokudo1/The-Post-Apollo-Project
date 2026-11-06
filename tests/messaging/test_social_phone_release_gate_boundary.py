"""The P18d release model is not a live inbox, grant issuer, or QML adapter."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "services/phone/HostReadReleaseGateModel.py"
PORT = ROOT / "services/phone/BlueFerryHostReadPort.py"
PANE = ROOT / "widgets/messanger/PhonePane.qml"
CONTRACT = ROOT / "services/messaging/ADAPTER-CONTRACT.md"


class HostReleaseGateBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = MODEL.read_text(encoding="utf-8")
        cls.port = PORT.read_text(encoding="utf-8")
        cls.pane = PANE.read_text(encoding="utf-8")

    def test_existing_phone_still_has_no_private_data_read_command(self):
        self.assertNotIn("HostReadReleaseGateModel", self.pane)
        self.assertNotIn("BlueFerryHostReadPort", self.pane)
        self.assertIn("conversations: []", self.pane)
        self.assertIn("messages: []", self.pane)
        self.assertIn("sendEnabled: false", self.pane)
        self.assertIn("Social phone link: NOT VERIFIED", self.pane)

    def test_model_cannot_grant_sender_or_service_permissions(self):
        self.assertIn('EXECUTION = "IN_PROCESS_MODEL_ONLY"', self.model)
        self.assertIn('"authorization": "NOT_IMPLEMENTED"', self.model)
        self.assertIn('"routeEligible": False', self.model)
        self.assertIn('"contentAccessEnabled": False', self.model)
        self.assertIn('frozenset({"messages.read", "contacts.read"})', self.model)
        self.assertNotIn("def create_grant(", self.model)
        self.assertNotIn("def send_message(", self.model)
        self.assertNotIn("SetPhoneAudioRoute(", self.model)
        self.assertNotIn("org.kde.kdeconnect", self.model)

    def test_port_callbacks_remain_separate_and_host_owned(self):
        self.assertIn("host_guard: Callable[[str, str, str], bool]", self.port)
        self.assertIn(
            "host_release: Callable[[str, str, str, dict[str, object]], bool]",
            self.port,
        )
        self.assertIn("BoundReadCallbacks", self.model)
        self.assertIn("self._lock = RLock()", self.model)
        self.assertIn("self._cancel_locked()", self.model)
        self.assertIn("self._purge(old)", self.model)
        self.assertIn('PURGE_UNCONFIRMED', self.model)
        self.assertIn("self._epoch == epoch", self.model)

    def test_shared_social_contract_still_requires_separate_router_owner(self):
        spec = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("one integration owner", spec)
        self.assertIn("messages", spec)
        self.assertIn("conversations", spec)


if __name__ == "__main__":
    unittest.main()
