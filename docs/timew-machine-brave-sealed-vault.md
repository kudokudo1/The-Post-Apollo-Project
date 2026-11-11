# MACHINE // Sealed Brave session vault V1

PATIENT // The-Post-Apollo-Project  
ROOM // TimeW MACHINE / Brave restart continuity  
STAFF ROLE // Hospital-compatible external DOC; live registration not verified  
ASSIGNMENT // Validate and persist only pre-encrypted session envelopes in separate protected local storage  
SCOPE // New inert CLI Python module and synthetic security tests, no Brave/Quickshell wiring

## IMPLEMENTATION

The preceding PR #1832 (confirmed on `main`) supplies operator-clicked
optional `tabs` access and an anonymous current-window preview. It
does not actually save page addresses.

This milestone adds `services/time/MachineBraveSealedVault.py`, a
**repository-only, nonregistered, ciphertext-only file vault** with
explicit CLI operations `put`, `list`, `read ID`,
`delete ID EXPECTED_SHA256`. No existing geometry checkpoint schema
or TimeW service is changed.

The vault demands an exact pre-encrypted envelope:
- `kind = machine-brave-sealed-session-v1`, version 1.
- `algorithm = AES-256-GCM` with a unique 96-bit nonce per encryption.
- `kdf = PBKDF2-HMAC-SHA256`, at least 600,000 iterations and a
  128-bit random salt, deriving a 256-bit key from a separate passphrase.
- Authenticated additional data (AAD) must be exactly
  `machine-brave-sealed-session-v1`.
- Ciphertext includes the 16-byte GCM tag. The vault validates shape,
  size and canonical base64url but **cannot authenticate a GCM tag**:
  it has no passphrase or secret key.
- There are *no* URL, title, profile, credential, window, workspace,
  monitor or free-form metadata fields in the accepted envelope.
  All sensitive data, including eventual operator labels and selected
  URLs, would live *inside* the encrypted payload.

Only an explicit `put` CLI invocation with
`operator_save_requested: true` creates a private file under
`$XDG_DATA_HOME/post-apollo/machine/brave-sealed-vault`
(or the normal XDG data-home fallback). This boolean is a
**declarative input, NOT proof of human consent**. The CLI is not
reachable from Brave or TimeW and is not installed as a native host.

Filesystem rules:
- New Post-Apollo/MACHINE/vault directories are created with 0700;
  existing paths must already be owned by the current user and private.
- Stored records are mode 0600, opened with no-follow checks and
  validated for owner, type, size and hardlink count.
- Content is first written to an exclusive temporary file, flushed
  and fsynced; an atomic hardlink publishes a **fresh UUID record name
  without replacing an existing record**. The temp link is removed
  and the directory fsynced. Failed writes roll back files created by
  that call.
- A crash can leave an orphan `.tmp-...`. Listing reports its
  presence but does not delete/consume it. New puts refuse until the
  orphan receives independent recovery handling.
- Read-only LIST/READ never create storage.
- A fixed 32-record cap limits retained ciphertext data.
- DELETE requires exact record UUID **and** the last observed
  SHA-256 of the serialized record, rejecting stale/mistyped requests.
  This is an optimistic user-action guard, not cryptographic
  authorization against another process with the same UID.
- CLI failures return a fixed generic refusal without printing paths,
  raw data, passwords, file contents or caller exceptions.

## HOW TO USE

**There is no new live UI and no local installation in this PR.**

A developer running tests in an isolated repository checkout may use:

```bash
python3 -B -I tests/timew/test_machine_brave_sealed_vault.py
node tests/timew/test_machine_brave_sealed_vault_crypto.mjs
```

The Python test uses intentionally fake bytes to exercise file
boundaries. The Node test encrypts *synthetic* two-window browser
data with real PBKDF2/AES-256-GCM (using a test-only password),
invokes the vault CLI in a temporary `XDG_DATA_HOME`, validates that
the stored file contains no readable page addresses or password,
reads the opaque envelope, authenticates and decrypts it **only in the
Node test process**, then deletes it via digest guarded confirmation.

**Do not copy the sample vault CLI PUT operation to a real desktop.**
There is no consent-bound browser saver yet. In particular, neither
this module nor the native title-marker host is allowed to write real
browser session records. No file containing raw tab addresses should
be fed into the CLI: it will reject any plaintext fields.

## VERIFY

The new workflow runs both tests and the earlier synthetic
recovery / permission-preview regression suites. It checks refusal on
plaintext fields, wrong permissions, symlinks, duplicate-input keys,
missing data, unsafe directory modes, stale deletes, a simulated
crash orphan, and no Brave/TimeW integration. Independent review and
live activation are not inferred from passing CI.

## WATCH OUT FOR

- There is **no passphrase creation, entry, key derivation, encryption
  or decryption in the actual Brave extension** yet. A validly shaped
  envelope is not proof of actual authenticated encryption; the
  future caller must encrypt before sending.
- Mode 0600 protects against other Unix user accounts under normal
  filesystem permissions. It does not defend against a malicious
  process already running as the same Unix user. Encryption is intended
  to reduce exposure of the stored browser address contents, but the
  passphrase strength, memory lifecycle and runtime environment matter.
- PBKDF2 600k is a defined initial compatibility floor, not a final
  security proof. A future encrypted payload must use unique random
  salt and nonce, authenticate the exact AAD, and be subject to
  independent cryptographic review.
- The existing `tabs` permission is browser-wide. A future capture
  path must still verify per-window user intent, review selected
  addresses individually, exclude private sessions and obtain
  separate explicit saving consent.
- No browser-to-Sway trust, persistent window identity, URL dedup,
  encrypted snapshot reader in UI, or window restore is added.
- Crash orphan cleanup is intentionally **not automatic**. Any
  recovery utility must distinguish orphaned data from an in-flight
  writer before removing it.

## CHECKLIST

- [x] Confirm merge/current source and Hospital assignment scope
- [x] Separate ciphertext store from geometry metadata
- [x] Strict sealed-envelope validation and bounded input
- [x] Private no-follow file paths; atomic publication and rollback
- [x] Read/list/delete with stale digest guard
- [x] Synthetic real crypto roundtrip, no plaintext on disk
- [ ] Exact-head CI and independent security review
- [ ] Operator-approved local disposable-vault exercise
- [ ] Consent UI: choose individual tab addresses to encrypt
- [ ] Browser WebCrypto key management / passphrase handling
- [ ] Secure local sender/receiver contract and origin trust
- [ ] Recovery import/dedup/monitor mapping and final acceptance

## NEXT / DECISIONS

Keep draft/unmerged until independent review and operator decision.
No credentials, real tabs, host manifests, browser profiles, local
files, SAVE/RESTORE operations or production components were modified
by this repository-only development milestone.
