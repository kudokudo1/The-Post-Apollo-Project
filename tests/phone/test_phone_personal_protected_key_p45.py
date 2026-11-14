"""PHONE P45 host-private read-only Secret Service key retrieval contracts."""
from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalProtectedKeyP45 as Keys

SELECTOR = "a" * 32
KEY = bytes(range(1, 33))


class KeyMechanismTests(unittest.TestCase):
    def call(self, *, selector=SELECTOR, tool=Keys.EXECUTABLE,
             code=0, output=None, fail=None):
        seen = []
        if output is None:
            output = base64.urlsafe_b64encode(KEY).rstrip(b"=") + b"\n"
        def run(args, **kwargs):
            seen.append((args, kwargs))
            if fail:
                raise fail
            return SimpleNamespace(
                returncode=code, stdout=output, stderr=b"PRIVATE PROVIDER ERROR"
            )
        return (lambda: Keys.read_existing_key_for_trusted_host(
            selector, which=lambda _: tool, run=run)), seen

    def test_existing_protected_key_read_is_strict_and_content_free(self):
        read, seen = self.call()
        self.assertEqual(read(), KEY)
        self.assertEqual(len(seen), 1)
        argv, kwargs = seen[0]
        self.assertEqual(argv, [
            "/usr/bin/secret-tool", "lookup",
            "post-apollo-service", Keys.SERVICE,
            "key-id", SELECTOR,
        ])
        self.assertEqual(kwargs, {
            "input": b"", "capture_output": True,
            "timeout": 4, "check": False,
        })
        self.assertNotIn(KEY, repr(argv).encode())
        self.assertNotIn("PRIVATE PROVIDER ERROR", str(KEY))
        self.assertNotIn("profileId", " ".join(argv))

    def test_wrong_id_missing_binary_and_path_shadow_refuse_no_execution(self):
        for selector in (None, 123, "", "A" * 32, "e" * 31,
                         "e" * 33, "../private", "abc/profile",
                         "g" * 32):
            with self.subTest(selector=selector):
                read, seen = self.call(selector=selector)
                with self.assertRaisesRegex(
                    Keys.ProtectedKeyUnavailable,
                    "^PHONE_PERSONAL_KEY_UNAVAILABLE$"
                ):
                    read()
                self.assertEqual(seen, [])
        for tool in (None, "/tmp/secret-tool", "/usr/local/bin/secret-tool"):
            read, seen = self.call(tool=tool)
            with self.assertRaises(Keys.ProtectedKeyUnavailable):
                read()
            self.assertEqual(seen, [])

    def test_bad_keyring_output_never_falls_back_or_reports_details(self):
        good = base64.urlsafe_b64encode(KEY).rstrip(b"=")
        for output in (
            b"", b"not-a-key", b" " * 44, b"?" * 43,
            good + b"\n\n", good + b"\x00", good + b"extra",
            base64.urlsafe_b64encode(bytes(32)).rstrip(b"="),
            good[:42] + b"/", b"x" * 129,
        ):
            with self.subTest(prefix=output[:3]):
                read, _ = self.call(output=output)
                with self.assertRaisesRegex(
                    Keys.ProtectedKeyUnavailable,
                    "^PHONE_PERSONAL_KEY_UNAVAILABLE$"
                ):
                    read()
        read, _ = self.call(code=1)
        with self.assertRaises(Keys.ProtectedKeyUnavailable):
            read()
        read, _ = self.call(fail=OSError("real secret from provider"))
        with self.assertRaisesRegex(
            Keys.ProtectedKeyUnavailable,
            "^PHONE_PERSONAL_KEY_UNAVAILABLE$"
        ):
            read()

    def test_no_mutation_or_public_service_entrypoint(self):
        src = (ROOT / "services/phone/PhonePersonalProtectedKeyP45.py").read_text()
        for forbidden in (
            "def main(", "if __name__ ==", '"store"',
            '"clear"', '"unlock"', '"export"', '"backup"',
            "QtQuick", "DBusGMainLoop", "os.environ", "print(",
            "Vault.commit(", "socket.", "import dbus",
        ):
            self.assertNotIn(forbidden, src)
        self.assertIn("lookup", src)
        self.assertIn("not a capability", src)


if __name__ == "__main__":
    unittest.main()
