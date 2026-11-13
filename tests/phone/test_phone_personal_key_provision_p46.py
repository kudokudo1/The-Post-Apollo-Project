"""P46 host-private Secret Service provisioning tests with mocked provider.

No real keyring write, unlock, provider invocation, signer or PHONE contact.
"""
from __future__ import annotations

import base64
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalKeyProvisionP46 as Provision
import PhonePersonalProtectedKeyP45 as Existing

MASTER = bytes(range(1, 33))
IDENTIFIER = bytes(range(1, 17))


class ProvisionTests(unittest.TestCase):
    def prepared(self):
        values = iter((IDENTIFIER, MASTER))
        return Provision.prepare_new_key(random_bytes=lambda n: next(values))

    def test_first_use_preparation_has_distinct_private_material_and_no_io(self):
        p = self.prepared()
        self.assertEqual(p.key_id, IDENTIFIER.hex())
        self.assertEqual(p.material, MASTER)
        self.assertNotIn(MASTER.hex(), repr(p))
        self.assertNotIn(p.key_id, repr(p))
        self.assertNotIn("bytes", repr(p))
        self.assertEqual(len(p.key_id), 32)

    def test_reject_invalid_rng_without_attempting_store(self):
        for fake in (
            lambda n: b"",
            lambda n: b"0" * 4,
            lambda n: bytes(n),
            lambda n: "not bytes",
            lambda n: (_ for _ in ()).throw(ValueError("secret")),
        ):
            with self.subTest(fake=str(fake)):
                with self.assertRaisesRegex(
                    Provision.KeyProvisionRefused, "^PHONE_KEY_PROVISION_REFUSED$"
                ):
                    Provision.prepare_new_key(random_bytes=fake)

    def test_lookup_store_readback_uses_stdin_and_private_namespace(self):
        p = self.prepared()
        run_calls = []
        preflight_calls = []
        reserve_calls = []

        def run(argv, **kwargs):
            run_calls.append((argv, kwargs))
            if argv[1] == "store":
                return SimpleNamespace(returncode=0, stdout=b"",
                                       stderr=b"")
            self.assertEqual(argv[1], "lookup")
            return SimpleNamespace(
                returncode=0,
                stdout=base64.urlsafe_b64encode(MASTER).rstrip(b"=") + b"\n",
                stderr=b"",
            )
        def ready():
            preflight_calls.append(True)
            return True
        def reserve(value):
            reserve_calls.append(value)
            return True

        result = Provision.store_prepared_for_protected_host(
            p, preflight_unlocked=ready, reserve_unused_id=reserve,
            which=lambda _: Existing.EXECUTABLE, run=run,
        )
        self.assertEqual(result, Provision.OUTCOME)
        self.assertEqual(reserve_calls, [p.key_id])
        self.assertEqual(len(run_calls), 2)
        argv, kw = run_calls[0]
        self.assertEqual(argv, [
            Existing.EXECUTABLE, "store", "--label=" + Provision.LABEL,
            "post-apollo-service", Existing.SERVICE,
            "key-id", p.key_id,
        ])
        self.assertEqual(kw["input"],
                         base64.urlsafe_b64encode(MASTER).rstrip(b"=") + b"\n")
        self.assertEqual(kw["timeout"], 5)
        self.assertTrue(kw["capture_output"])
        self.assertFalse(kw["check"])
        self.assertNotIn(MASTER, " ".join(argv).encode())
        self.assertNotIn(MASTER.hex(), " ".join(argv))
        self.assertEqual(run_calls[1][0][1], "lookup")
        self.assertGreaterEqual(len(preflight_calls), 3)
        for forbidden in ("keyId", "masterKey", "material", "note", "profile"):
            self.assertNotIn(forbidden, result)
        for flag in ("productionEnabled", "installedHostVerified",
                     "keyDurablyAttested", "personalSaveAuthorized"):
            self.assertIs(result[flag], False)

    def test_locked_or_no_external_reservation_cannot_start_store(self):
        p = self.prepared()
        for valid, reserved, tool in (
            (False, True, Existing.EXECUTABLE),
            (True, False, Existing.EXECUTABLE),
            (True, True, "/tmp/secret-tool"),
            (True, True, None),
        ):
            with self.subTest(valid=valid, reserved=reserved, tool=tool):
                called = []
                def deny_run(*args, **kwargs):
                    called.append((args, kwargs))
                    self.fail("no provider call expected")
                with self.assertRaises(Provision.KeyProvisionRefused):
                    Provision.store_prepared_for_protected_host(
                        p, preflight_unlocked=lambda: valid,
                        reserve_unused_id=lambda _: reserved,
                        which=lambda _: tool, run=deny_run,
                    )
                self.assertEqual(called, [])

    def test_after_store_errors_never_auto_retry_or_erase(self):
        p = self.prepared()
        for case in ("store_failure", "store_nonempty",
                     "lookup_failure", "lookup_mismatch",
                     "preflight_revoked", "provider_timeout"):
            with self.subTest(case=case):
                calls = []
                ready_calls = []
                def ready():
                    ready_calls.append(True)
                    return not (case == "preflight_revoked"
                                and len(ready_calls) >= 3)
                def run(argv, **kwargs):
                    calls.append(argv[1])
                    if case == "provider_timeout":
                        raise TimeoutError("PRIVATE KEY")
                    if argv[1] == "store":
                        return SimpleNamespace(
                            returncode=1 if case == "store_failure" else 0,
                            stdout=b"bad" if case == "store_nonempty" else b"",
                            stderr=b"PRIVATE PROVIDER DIAGNOSTIC",
                        )
                    return SimpleNamespace(
                        returncode=1 if case == "lookup_failure" else 0,
                        stdout=(base64.urlsafe_b64encode(
                            bytes([55]) * 32 if case == "lookup_mismatch"
                            else MASTER).rstrip(b"=") + b"\n"),
                        stderr=b"PRIVATE PROVIDER DIAGNOSTIC",
                    )
                with self.assertRaisesRegex(
                    Provision.KeyProvisionRefused, "^PHONE_KEY_PROVISION_REFUSED$"
                ):
                    Provision.store_prepared_for_protected_host(
                        p, preflight_unlocked=ready,
                        reserve_unused_id=lambda _: True,
                        which=lambda _: Existing.EXECUTABLE, run=run
                    )
                self.assertEqual(calls.count("store"), 1)
                self.assertLessEqual(calls.count("lookup"), 1)
                self.assertNotIn("clear", calls)
                self.assertNotIn("unlock", calls)

    def test_reject_wrong_prepared_and_fake_inputs(self):
        p = self.prepared()
        invalid = (
            {"prepared": None},
            {"prepared": {"key_id": p.key_id, "material": MASTER}},
            {"prepared": Provision.PreparedKey("a" * 32, bytes(32))},
            {"prepared": Provision.PreparedKey("ABC", MASTER)},
            {"prepared": Provision.PreparedKey("a" * 32, b"short")},
            {"preflight_unlocked": None},
            {"reserve_unused_id": lambda _: 1},
        )
        for changed in invalid:
            kwargs = dict(
                prepared=p, preflight_unlocked=lambda: True,
                reserve_unused_id=lambda _: True,
                which=lambda _: Existing.EXECUTABLE,
                run=lambda *a, **kw: self.fail("unsafe provider invocation")
            )
            kwargs.update(changed)
            with self.subTest(fields=list(changed)):
                with self.assertRaises(Provision.KeyProvisionRefused):
                    Provision.store_prepared_for_protected_host(**kwargs)

    def test_no_export_rotation_erase_qml_or_service_entrypoint(self):
        src = (ROOT / "services/phone/PhonePersonalKeyProvisionP46.py").read_text()
        for bad in (
            "def main(", "if __name__ ==", "import dbus",
            "QtQuick", "Vault.commit(", "os.environ",
            '"clear"', '"unlock"', "print(",
            "return prepared.material", "logger.", "socket.",
        ):
            self.assertNotIn(bad, src)


if __name__ == "__main__":
    unittest.main()
