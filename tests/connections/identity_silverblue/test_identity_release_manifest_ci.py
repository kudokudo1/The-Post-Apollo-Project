#!/usr/bin/env python3
"""Adversarial synthetic release-root tests. Never assert production authority."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SOURCE = Path(__file__).with_name("release_manifest_ci.py")
spec = importlib.util.spec_from_file_location("c4b_id_ci_release", SOURCE)
assert spec is not None and spec.loader is not None
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def pub(private):
    return private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )


class C4bSyntheticReleaseRootContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.rpm = Path(self.temp.name) / "synthetic-fixture.rpm"
        self.rpm.write_bytes(b"CI-only placeholder RPM payload used in syntax tests")
        self.root = Ed25519PrivateKey.generate()
        self.receipt = pub(Ed25519PrivateKey.generate())
        self.doc = M.make_test_manifest(self.rpm, self.receipt)
        self.raw = M.canonical(self.doc)
        self.sig = self.root.sign(M.DOMAIN + self.raw)

    def check(self, raw=None, sig=None, root=None, receipt=None, rpm=None,
              minimum_epoch=1, minimum_sequence=1):
        return M.verify(
            self.raw if raw is None else raw,
            self.sig if sig is None else sig,
            pub(self.root) if root is None else root,
            self.receipt if receipt is None else receipt,
            self.rpm if rpm is None else rpm,
            minimum_epoch=minimum_epoch,
            minimum_sequence=minimum_sequence,
        )

    def sign(self, doc):
        raw = M.canonical(doc)
        return raw, self.root.sign(M.DOMAIN + raw)

    def refused(self, code, **kwargs):
        with self.assertRaises(M.Refused) as r:
            self.check(**kwargs)
        self.assertEqual(str(r.exception), code)

    def test_01_deny_only_valid_synthetic_release(self):
        response = self.check()
        self.assertIs(response["syntheticReleaseSyntaxValid"], True)
        self.assertEqual(set(M.FILES), set(self.doc["files"]))
        for key in M.DENIED:
            self.assertIs(response[key], False, key)

    def test_02_unsigned_or_different_release_root(self):
        self.refused("RELEASE_ROOT_SIGNATURE_REFUSED", sig=b"1" * 64)
        self.refused("RELEASE_ROOT_SIGNATURE_REFUSED",
                     root=pub(Ed25519PrivateKey.generate()))
        self.refused("INDEPENDENT_SYNTHETIC_PINS_MISSING", root=b"")

    def test_03_different_receipt_key_or_package_bytes(self):
        self.refused("SIGNED_RPM_SOURCE_OR_RECEIPT_PIN_MISMATCH",
                     receipt=pub(Ed25519PrivateKey.generate()))
        self.rpm.write_bytes(b"tampered")
        self.refused("SIGNED_RPM_SOURCE_OR_RECEIPT_PIN_MISMATCH")

    def test_04_replay_floor_or_wrong_role(self):
        self.refused("RELEASE_ROLE_OR_FLOOR_REFUSED", minimum_epoch=2)
        self.refused("RELEASE_ROLE_OR_FLOOR_REFUSED", minimum_sequence=2)
        for item, value in (
            ("schema", "other"),
            ("role", "postapollo.connections.c4d-status"),
            ("package", "postapollo-connections-c3d-ci-status"),
            ("unit", "wrong-unit.service"),
            ("epoch", True),
        ):
            with self.subTest(item=item):
                changed = dict(self.doc, **{item: value})
                raw, sig = self.sign(changed)
                self.refused("RELEASE_ROLE_OR_FLOOR_REFUSED", raw=raw, sig=sig)

    def test_05_missing_extra_or_invalid_module(self):
        modules = dict(self.doc["files"])
        modules.pop(next(iter(modules)))
        raw, sig = self.sign(dict(self.doc, files=modules))
        self.refused("RELEASE_ROLE_OR_FLOOR_REFUSED", raw=raw, sig=sig)
        modules = dict(self.doc["files"])
        modules["/etc/unapproved"] = "a" * 64
        raw, sig = self.sign(dict(self.doc, files=modules))
        self.refused("RELEASE_ROLE_OR_FLOOR_REFUSED", raw=raw, sig=sig)
        modules = dict(self.doc["files"])
        modules[next(iter(modules))] = "BAD"
        raw, sig = self.sign(dict(self.doc, files=modules))
        self.refused("RELEASE_MODULE_DIGEST_REFUSED", raw=raw, sig=sig)

    def test_06_noncanonical_or_duplicate_fields(self):
        expanded = self.raw.replace(b'"epoch":1', b'"epoch":1, "epoch":1', 1)
        self.refused("RELEASE_JSON_REFUSED", raw=expanded,
                     sig=self.root.sign(M.DOMAIN + expanded))
        noncanonical = self.raw.replace(b'"epoch":1', b'"epoch": 1', 1)
        self.refused("RELEASE_JSON_REFUSED", raw=noncanonical,
                     sig=self.root.sign(M.DOMAIN + noncanonical))


if __name__ == "__main__":
    unittest.main(verbosity=2)
