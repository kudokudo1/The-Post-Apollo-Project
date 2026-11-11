# Social PHONE // P36 disposable keyring + host-action trust boundary

> **STATUS:** Synthetic-only GitHub candidate, **not** a production keyring/consent host or usable Favorites/Notes screen.
>
> **Patient:** kudokudo1/The-Post-Apollo-Project. **Staff:** external Hospital-compatible DOC. **Room / Assignment / Session:** no verified live attachment. **Scope:** P34 identity/P35 encrypted vault to one-action protected-key lookup and authorization-order tests. Existing TASKS Secret Service, global Favorites++, Identity Gateway and current PHONE QML are out of scope.

## IMPLEMENTATION

- PhonePersonalKeyringP36.py is a **read-only disposable keyring adapter**. It can look up only an item tagged post-apollo-test=post-apollo-phone-p36-disposable-ci-only plus a random 128-bit selector. It validates a canonical base64url-encoded **32-byte** key with bounded output and a fixed error. There is **no** store, clear, auto-unlock, Secret Service service-enumeration, environmental key, CLI or QML activation in the shipped module. secret-tool lookup may activate a session provider when called; **do not invoke this module against the operator's real session**.
- PhonePersonalHostGateP36.py models **one** host-controlled metadata action, defaulting to denial. A synthetic host observer must report the current profile, exact BlueFerry unique owner, active session, fresh snapshot epoch, current contacts.read approval, connected device, and bounded contact cards. A separate synthetic human-gesture checker must approve the exact one-shot action. Only then is a key requested.
- The gate rechecks host/consent state after the key lookup (which may block) and just before the encrypted commit, ensuring changes to provider owner, session, snapshot, profile or approval cause refusal. It rejects unselected or cross-profile cards and malformed intents **before** requesting any key. One in-memory action nonce cannot be applied twice.
- A synthetic LINK, FAVORITE, NOTE or UNLINK executes the **existing P34 identity policy** against only the currently selected contact and already-loaded bounded snapshot, then the **existing P35 AES-GCM vault** using a strict revision comparison. The outward response has only SYNTHETIC_SEALED, a numeric revision, and productionEnabled:false; no key, note body, name, address, phone profile or saved record identifier is released.
- tests/phone/fixtures/PhoneP36PrivateSession.sh starts in a new dbus-run-session on GitHub, uses a disposable HOME/XDG tree and creates a throwaway GNOME Keyring. A Python fixture creates one randomly selected CI-only Secret Service item, performs LINK, FAVORITE, NOTE, then a **separate Python process** retrieves the test key from that private provider and decrypts only fictional data. The exact keyring item is cleared and a missing lookup verified before success.

## VERIFY

- tests/phone/test_phone_personal_host_gate_p36.py proves rejection on no consent, expired action, revoked device, invalid BlueFerry owner, cross-profile card, concurrent owner/epoch change, stale revision, forged action, repeated nonce, unlinked contact and malformed keyring replies. It verifies no key lookup before the initial checks, and no vault write after authority changes.
- Real isolated Secret Service harness proves synthetic key storage, lookup, independent-process recovery and exact-item cleanup in a disposable **GitHub runner** only. Existing P34/P35 regression tests remain. No private user data is used or logged.
- Separate P36 CI installs GNOME Keyring/Secret Service and PyCA cryptography only in CI; normal PHONE CI only compiles the dormant modules.

## WATCH OUT FOR // Why this remains disabled

- **Synthetic callbacks are forgeable.** A Python dataclass or lambda returning True is not an authenticated user identity, human gesture, C5 consent, trusted signed Identity Gateway grant, or OS authorization. The P36 coordinator is explicitly a behavioral fixture, not a secure production host. **Do not attach QML, D-Bus, a terminal command, or actual contacts to it.**
- Secret Service is a key-storage API, **not per-app identity authorization**. A keyring that is already unlocked may release items to other same-session clients. No real key lifecycle or specific protected collection, unlock UX, backup/restore/rotation/deletion strategy has been chosen or activated.
- Read-only key lookup is intentionally restricted to synthetic post-apollo-test attributes. Production must use a **different distinct namespace and key**, with explicit provisioning consent and a genuinely verified host process identity and scoped grant.
- Real PhoneRememberedRead.py is a remembered per-user read-only preference and **not cryptographic app-authenticated consent**. The current Identity Center gateway in C4b/C3e remains a separate unverified installed-host dependency. C5 owns genuine human-consent authority. P36 does not claim either service is available or integrate them.
- P34 match proofs are conservative candidates from the first 100 loaded BlueFerry contacts. No unique-person proof, automatic relink, real phone-blocking, contact editing/sync, messaging send or FaceTime was added.
- P35 ciphertext can still be historically rolled back by someone with valid older ciphertext; key loss or a locked Secret Service may render the vault unreadable. This test does not prove hardware-backed isolation, keyring persistence across reboot, malicious same-UID protection or Fedora/Sway installed-host behavior.
- P36's final host check precedes the file-system commit but is not an atomic lease across the separate BlueFerry/session authority and on-disk file. Production host needs an explicit locking/revalidation protocol or signed, short-lived commit capability before enabling writes.

## HOW TO USE

No PHONE buttons are added yet. P36 has no entrypoint to production, no new keyring item on Fedora, and does not change existing Personal read approval or saved contacts. Review its GitHub draft/CI. CI exercises the isolated fixture only and cleans up.

## CHECKLIST

- [x] Check current GitHub/Syntagma and keep existing TASKS/Connections keyring ownership independent.
- [x] Build strict, read-only synthetic key lookup, no key creation/auto-unlock in service code.
- [x] Model current-device/profile/session/approval/gesture rechecks around key lookup and encrypted save.
- [x] Reuse P34/P35, retaining AES-GCM, revision check and per-profile boundary.
- [x] Test revoked/drifting state, key failures, replay, stale revisions, no note leakage.
- [x] Isolated CI Secret Service creation, independent-process decrypt and exact cleanup.
- [ ] Inspect exact-head passing CI and operator PR acceptance.
- [ ] Finalize **real authenticated** installed-host identity/grant with C3e/C4b and **human consent** with C5.
- [ ] Select real keyring collection, unlock/backup/rotation/recovery, and native disposable Fedora verification under local approval.
- [ ] Implement production host with consent and key lifecycle, then connect visible FAVORITE star/NOTES editor.
- [ ] Confirm final operator acceptance.

## NEXT

**P37:** Coordinate with C3e/C4b/C5 to define a **real signed host identity and human-consent receipt contract**, plus a genuine keyring unlock/provisioning UI and per-action signed authorization. Keep P36 test-only until the host's authenticated source of truth, key backup/rotation and revoke behavior are verified on an installed Fedora host. Then implement the operator-approved favorite and notes UI, not an unverified proxy.

## DECISIONS

No app-specific Secret Service authentication claim. No production activation, local Fedora package/keyring writes, QML hook, provider calls or data migration. No merge without operator acceptance; no live Hospital Room or Session asserted. Keep test-only key provider names distinct from any future production key namespace.
