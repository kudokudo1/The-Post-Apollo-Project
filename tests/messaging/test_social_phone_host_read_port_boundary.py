"""P18c is a host-internal integration seam, not a QML-accessible phone reader."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/phone/BlueFerryHostReadPort.py"


class SocialPhoneHostBoundaryTests(unittest.TestCase):
    def test_provider_read_has_no_executable_cli_or_qml_bridge(self):
        source = SOURCE.read_text()
        pane = (ROOT / "widgets/messanger/PhonePane.qml").read_text()
        self.assertNotIn('if __name__ == "__main__"', source)
        self.assertNotIn('BlueFerryHostReadPort', pane)
        self.assertIn('phoneReadAdapter.conversations : []', pane)
        self.assertIn('phoneReadAdapter.messages : []', pane)
        self.assertIn('sendEnabled: false', pane)
        self.assertIn('Social phone link: NOT VERIFIED', pane)

    def test_host_callbacks_and_release_barrier_are_explicitly_required(self):
        source = SOURCE.read_text()
        self.assertIn('def read_for_trusted_host(', source)
        self.assertIn('host_guard: Callable[[str, str, str], bool]', source)
        self.assertIn('host_release: Callable[[str, str, str, dict[str, object]], bool]',
                      source)
        self.assertIn('HOST_RELEASE_REFUSED', source)
        self.assertIn('HOST_OWNED_UNVERIFIED', source)
        self.assertIn('normalize_threads(payload, profile_id=profile_id)', source)
        self.assertIn('normalize_contact_page(', source)
        self.assertNotIn('import Quickshell', source)
        self.assertNotIn('subprocess.run(', source)
        self.assertNotIn('os.environ', source)
        self.assertNotIn('SendToThread(', source)

    def test_separate_read_capabilities_with_no_send_or_contact_photo(self):
        source = SOURCE.read_text()
        self.assertIn('frozenset({"messages.read", "contacts.read"})', source)
        self.assertIn('ListThreads(', source)
        self.assertIn('ListContactCards(', source)
        for forbidden in ('messages.send', 'contacts.write', 'GetContactPhoto(',
                          'SetPhoneAudioRoute(', 'ClearHistory(', 'Pair('):
            self.assertNotIn(forbidden, source)
        self.assertIn('get_object(owner, OBJECT, introspect=False)', source)


if __name__ == "__main__":
    unittest.main()
