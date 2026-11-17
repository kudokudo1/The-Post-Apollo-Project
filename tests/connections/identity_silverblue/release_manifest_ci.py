#!/usr/bin/env python3
"""Synthetic C4b Identity Silverblue release-root envelope. NOT host admission.

Only an ephemeral GitHub controller may create test keys; no private key is
written to disk or shipped in the RPM. External production root enrollment,
release floor, live process and SELinux/seat provenance are NOT implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "services/identity"
CI = ROOT / "tests/connections/identity_silverblue"
PREFIX = "/usr/libexec/post-apollo/identity/"
MODULES = (
    "identity-gateway-ci", "desktop_command_gateway_v0.py",
    "desktop_host_lifecycle_v0.py", "desktop_context_projection_v0.py",
    "desktop_session_host_v0.py", "native_loopback_callback_v0.py",
    "private_context_ipc_v0.py", "signed_command_receipt_v0.py",
)
UNIT_PATH = "/usr/lib/systemd/system/post-apollo-identity-silverblue-ci.service"
FILES = frozenset(PREFIX + n for n in MODULES) | {UNIT_PATH}
SCHEMA = "postapollo.identity.c4b.silverblue.synthetic-release.ci-v1"
ROLE = "postapollo.identity.native-command-gateway.deny-only-ci"
DOMAIN = b"postapollo.identity.c4b.silverblue.synthetic-release.ci-v1\0"
PACKAGE = "post-apollo-identity-silverblue-ci"
UNIT = "post-apollo-identity-silverblue-ci.service"
KEYS = {"schema", "role", "package", "epoch", "sequence",
        "rpmSha256", "receiptKeySha256", "unit", "files"}
HEX = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
MAX_MANIFEST = 4096
DENIED = {
    "signedGuestOriginAuthenticated": False,
    "evidenceCryptographicallyAttested": False,
    "installedGuestMeasured": False,
    "hostAuthenticated": False,
    "canApprove": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
    "canBeginSignIn": False,
}


class Refused(ValueError):
    pass


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Refused("DUPLICATE_FIELD")
        out[key] = value
    return out


def canonical(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def sha256(path):
    data = Path(path).read_bytes()
    if not 0 < len(data) <= 8 * 1024 * 1024:
        raise Refused("INPUT_SIZE_REFUSED")
    return hashlib.sha256(data).hexdigest()


def source_file(path):
    if path == UNIT_PATH:
        return CI / UNIT
    name = path[len(PREFIX):]
    if name == "identity-gateway-ci":
        return ROOT / "tests/identity/fixtures/identity_gateway_installed_ci"
    return SOURCE / name


def make_test_manifest(rpm, receipt_public_raw):
    if type(receipt_public_raw) is not bytes or len(receipt_public_raw) != 32:
        raise Refused("RECEIPT_KEY_REFUSED")
    return {
        "schema": SCHEMA, "role": ROLE, "package": PACKAGE,
        "epoch": 1, "sequence": 1, "unit": UNIT,
        "rpmSha256": sha256(rpm),
        "receiptKeySha256": hashlib.sha256(receipt_public_raw).hexdigest(),
        "files": {path: sha256(source_file(path)) for path in sorted(FILES)},
    }


def verify(raw, signature, root_public_raw, receipt_public_raw, rpm,
           minimum_epoch=1, minimum_sequence=1):
    if (type(raw) is not bytes or not 1 <= len(raw) <= MAX_MANIFEST
            or type(signature) is not bytes or len(signature) != 64
            or type(root_public_raw) is not bytes or len(root_public_raw) != 32
            or type(receipt_public_raw) is not bytes or len(receipt_public_raw) != 32
            or type(minimum_epoch) is not int or minimum_epoch < 1
            or type(minimum_sequence) is not int or minimum_sequence < 1):
        raise Refused("INDEPENDENT_SYNTHETIC_PINS_MISSING")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
        if type(document) is not dict or set(document) != KEYS or canonical(document) != raw:
            raise Refused("NONCANONICAL_OR_PARTIAL_RELEASE")
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError) as exc:
        raise Refused("RELEASE_JSON_REFUSED") from exc
    if (document["schema"] != SCHEMA or document["role"] != ROLE
            or document["package"] != PACKAGE or document["unit"] != UNIT
            or type(document["epoch"]) is not int
            or document["epoch"] < minimum_epoch
            or type(document["sequence"]) is not int
            or document["sequence"] < minimum_sequence
            or type(document["rpmSha256"]) is not str
            or HEX.fullmatch(document["rpmSha256"]) is None
            or type(document["receiptKeySha256"]) is not str
            or HEX.fullmatch(document["receiptKeySha256"]) is None
            or type(document["files"]) is not dict
            or set(document["files"]) != FILES):
        raise Refused("RELEASE_ROLE_OR_FLOOR_REFUSED")
    if any(type(digest) is not str or HEX.fullmatch(digest) is None
           for digest in document["files"].values()):
        raise Refused("RELEASE_MODULE_DIGEST_REFUSED")
    try:
        Ed25519PublicKey.from_public_bytes(root_public_raw).verify(signature, DOMAIN + raw)
    except (InvalidSignature, ValueError) as exc:
        raise Refused("RELEASE_ROOT_SIGNATURE_REFUSED") from exc
    if (sha256(rpm) != document["rpmSha256"]
            or hashlib.sha256(receipt_public_raw).hexdigest() != document["receiptKeySha256"]
            or any(sha256(source_file(path)) != document["files"][path]
                   for path in FILES)):
        raise Refused("SIGNED_RPM_SOURCE_OR_RECEIPT_PIN_MISMATCH")
    # This is only CI-controlled release envelope syntax, NOT evidence that
    # the RPM was installed or a real Linux host witnessed.
    return {"schema": SCHEMA, "syntheticReleaseSyntaxValid": True, **DENIED}


def _public_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("rpm", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args(argv)
    if (os.getenv("GITHUB_ACTIONS") != "true"
            or os.getenv("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.getenv("POST_APOLLO_ID_SILVERBLUE_CI_ONLY") != "1"):
        raise SystemExit("C4B_ID_REFUSED // NOT_DISPOSABLE_CI")
    folder = args.evidence
    if args.action == "create":
        folder.mkdir(mode=0o700)
        root = Ed25519PrivateKey.generate()
        receipt = Ed25519PrivateKey.generate()
        receipt_pub = _public_bytes(receipt)
        raw = canonical(make_test_manifest(args.rpm, receipt_pub))
        assert len(raw) <= MAX_MANIFEST
        (folder / "identity-synthetic-release.json").write_bytes(raw)
        (folder / "identity-synthetic-release.sig").write_bytes(root.sign(DOMAIN + raw))
        (folder / "identity-synthetic-root.pub").write_bytes(_public_bytes(root))
        (folder / "identity-synthetic-receipt.pub").write_bytes(receipt_pub)
        # No private key is serialized or sent to the RPM builder.
        print("C4B_ID_PASS // SEPARATE_TEST_ONLY_RELEASE_ROOT_AND_RECEIPT_KEYS_GENERATED")
        return 0
    result = verify(
        (folder / "identity-synthetic-release.json").read_bytes(),
        (folder / "identity-synthetic-release.sig").read_bytes(),
        (folder / "identity-synthetic-root.pub").read_bytes(),
        (folder / "identity-synthetic-receipt.pub").read_bytes(),
        args.rpm,
    )
    if any(result[key] is not False for key in DENIED):
        raise SystemExit("C4B_ID_REFUSED // AUTHORITY_FLAGS_CHANGED")
    print("C4B_ID_PASS // SIGNED_SYNTHETIC_RELEASE_BOUND_TO_RPM_MODULES_AND_RECEIPT_PUBLIC_KEY")
    print("C4B_ID_LIMITATION // NO_INDEPENDENT_PRODUCTION_ENROLLMENT_OR_INSTALLED_GUEST_WITNESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
