"""P36 disposable, private-D-Bus Secret Service integration verification.

THIS IS NOT A PRODUCTION CLI. The shell wrapper forcibly creates an isolated
D-Bus session and temporary HOME before calling this fixture. The script
creates ONE random disposable synthetic key, exercises P35 encrypted saves
under an entirely temporary data directory, then deletes its exact item.
No real contact data, device/profile bus calls or production keyring access.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalContactVault as Vault
import PhonePersonalHostGateP36 as Gate
import PhonePersonalKeyringP36 as Keyring

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
FIXTURE_ONLY = "P36_DISPOSABLE_PRIVATE_SESSION"


def refuse() -> None:
    raise RuntimeError("P36_DISPOSABLE_ONLY_REFUSED")


def checked(command: list[str], *, data: bytes = b"", timeout: int = 10):
    try:
        return subprocess.run(command, input=data, capture_output=True,
                              check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        refuse()


def ensure_isolated() -> tuple[Path, Path]:
    home = Path(os.environ.get("HOME", ""))
    if (os.environ.get("P36_PRIVATE_TEST") != FIXTURE_ONLY
            or not home.is_absolute()
            or not str(home).startswith("/tmp/postapollo-p36-ci-")
            or not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
            or not os.environ.get("XDG_DATA_HOME")):
        refuse()
    data = Path(os.environ["XDG_DATA_HOME"])
    if data != home / ".local" / "share" or not data.exists():
        refuse()
    return home, data


def item(selector: str) -> list[str]:
    return ["post-apollo-test", Keyring.SERVICE, "nonce", selector]


def fake_card() -> dict[str, object]:
    return {
        "id": PROFILE + ":epoch-1:legacy-row-0",
        "serviceId": "blueferry", "deviceProfileId": PROFILE,
        "displayNameInProfile": "Synthetic Only",
        "hasAddressDetails": True,
        "phoneNumbers": ["+15550001001"], "emailAddresses": ["ci@example.invalid"],
        "phoneCount": 1, "emailCount": 1,
    }


def main() -> int:
    _, data = ensure_isolated()
    selector = secrets.token_hex(16)
    master = secrets.token_bytes(32)
    root = data / Vault.ROOT_NAME
    # Preflight random selector, never accidentally overwrite an existing item.
    if checked(["secret-tool", "lookup", *item(selector)]).returncode == 0:
        refuse()
    if checked(["secret-tool", "store", "--label=P36 Synthetic Disposable Only",
                *item(selector)],
               data=base64.urlsafe_b64encode(master).rstrip(b"=") + b"\n").returncode != 0:
        refuse()
    cleaned = False
    try:
        # Nothing can access the vault until the synthetic in-process host
        # resolves the explicit one-shot action.
        sample = fake_card()
        def state():
            return Gate.ObservedFixture(
                profile=PROFILE, provider_owner=":1.7",
                session="synthetic-session-p36", snapshot_epoch=1,
                expires_at=200, personal_scope=True, contacts_approved=True,
                device_connected=True, cards=(sample,)
            )
        coordinator = Gate.FixtureCoordinator(
            observe=state, verify_gesture=lambda action, ctx: True,
            key_lookup=lambda: Keyring.synthetic_key_lookup(selector),
            clock=lambda: 100, root=root
        )
        for operation, revision, nonce, extra in (
            ("LINK", 0, "a" * 32, {}),
            ("FAVORITE", 1, "b" * 32, {"favorite": True}),
            ("NOTE", 2, "c" * 32, {"note": "synthetic vault contact memo"}),
        ):
            status = coordinator.apply(Gate.ActionFixture(
                action=operation, selected_row=sample["id"],
                expected_revision=revision, nonce=nonce, **extra))
            if status != {"status": "SYNTHETIC_SEALED",
                          "revision": revision + 1, "productionEnabled": False}:
                refuse()
        # A second Python process looks up the same synthetic key through
        # a real Secret Service, and authenticates/decrypts the vault file.
        newprocess = r"""
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import PhonePersonalContactVault as vault
import PhonePersonalKeyringP36 as lookup
key = lookup.synthetic_key_lookup(sys.argv[2])
data = vault.read(key, sys.argv[3], Path(sys.argv[4]))
assert data['revision'] == 3
assert len(data['entries']) == 1
assert data['entries'][0]['note'] == 'synthetic vault contact memo'
assert data['entries'][0]['favorite'] is True
sys.stdout.write('P36_NEW_PROCESS_RECOVERY_PASS')
"""
        result = checked([
            sys.executable, "-c", newprocess,
            str(ROOT / "services" / "phone"), selector, PROFILE, str(root)])
        if result.returncode != 0 or result.stdout != b"P36_NEW_PROCESS_RECOVERY_PASS":
            refuse()
        # Key is only removed with both exact CI-only attributes.
        clear = checked(["secret-tool", "clear", *item(selector)])
        if clear.returncode != 0:
            refuse()
        try:
            Keyring.synthetic_key_lookup(selector)
        except Keyring.KeyUnavailable:
            cleaned = True
        if not cleaned:
            refuse()
        print("P36_DISPOSABLE_KEYRING_AND_VAULT_PASS")
        return 0
    finally:
        if not cleaned:
            checked(["secret-tool", "clear", *item(selector)])
            # Never claim success unless retrieval is demonstrably absent.


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Do NOT print arbitrary error, secret, private file or provider stderr.
        print("P36_DISPOSABLE_PRIVATE_TEST_REFUSED")
        raise SystemExit(1)
