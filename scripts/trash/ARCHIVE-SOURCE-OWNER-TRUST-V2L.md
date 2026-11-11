# Trash++ // V2l Source-Owner Trust Enrollment (Deny-Only)

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal archive
PROVIDER // OPEN AI // CHATGPT
STAFF ROLE // DOC-compatible external developer; no verified live Hospital registration
ASSIGNMENT // Signed public-key enrollment, durable generation floors, permanent key revocation and test-only replay admission
PERMISSIONS // GitHub branch and draft PR only. No owner source edits, live signing, host writes, merging or Restore/Burn activation.

## IMPLEMENTATION

- Added scripts/trash/archive_v2_owner_trust.py to verify an authority-signed Ed25519 owner-key manifest against a separately supplied pinned test root. The root cannot come from the manifest or a source capture proof. Strict canonical schema binds owner (only Weather events/demo research), exact copy-only scope, key identity/public key, issuance/validity, generation, revocation and previous-manifest SHA-256.
- Added scripts/trash/archive_v2_trust_history.py, an explicitly test-only 0700 SQLite authority history. It requires monotonic generation increments, exact predecessor digest, sticky trust-root fingerprint, permanent retirement of rotated keys, and revocation that cannot be reversed by a later manifest for the same key.
- The V2l verifier uses the existing V2k Ed25519 source-claim verifier. Generation validation and nonce consumption share one private test-ledger transaction, denying stale enrollment, wrong owner, altered claims and nonce replay after process reopen.
- All results remain DENY_ONLY: captureAllowed=false, productionAllowed=false, sourceAuthorityVerified=false, humanConsentVerified=false, restoreAllowed=false, burnAllowed=false. No source signer, live key enrollment, ArchiveStore integration, protected owner expansion, QML button or host dependency is introduced.
- Synthetic tests generate ephemeral signing keys in CI memory only. They simulate source-owned signatures and independently signed enrollment without ever writing a private key to a user filesystem.

## HOW TO USE

No new Trash++ controls or local installation are part of V2l. ARCHIVE > SAVE SNAPSHOT / CONFIRM COPY and VERIFY CHAIN continue unchanged. V2i receipt provenance remains UNSIGNED_LOCAL. This stage tests the security prerequisites before any source-specific signing integration is approved.

## VERIFY

Synthetic Python tests cover: two independent signatures; externally pinned root and rejection of self-published keys; expired/invalid manifests; wrong owner/scope; generation rollback/skips and predecessor mismatch; trust-root replacement after enrollment; rotation/permanent retirement; explicit revocation; fresh source claims; stale enrolled claims; nonce replay across reopening; wrong signing key; symlink/root-mode refusal; and strict deny-only output. Existing Trash, Camera, snapshot, capacity bar, chain audit and Burn test suites must remain green.

## WATCH OUT FOR

- The pinned trust root exists only in test fixtures. No protected authority or Weather/demo signer has been established on the live system. A test root supplied by a caller is NOT a legitimate production enrollment authority.
- Trust floor and nonce consumption are transactionally coupled only within the test ledger. They are NOT coupled to a real ArchiveStore snapshot transaction and cannot authorize live copy, Restore or Burn.
- Source process identity, trusted time, actual key custody, signed consent, authority-owned release history, revocation distribution, external ledger anchoring, and crash-safe production admission are not implemented.
- V2i and V2j local unsigned receipt checking is distinct from V2k/V2l synthetic signature verification. Existing snapshot data and owners are not reclassified or migrated.
- No production private keys, public-key trust roots or credentials were added to the repository.

## CHECKLIST

- [x] V2k merged state, Syntagma Hospital protocols, concurrent ownership inspected
- [x] Strict signed owner-enrollment manifest and independent root verification
- [x] Durable test-only generation/revocation history with protected nonce use
- [x] Ephemeral key and adversarial security regression tests
- [ ] Full GitHub CI and any corrections
- [ ] Independent security review and source-owner authority agreement
- [ ] Operator-approved merge and eventual host deployment

## NEXT // V2m Implementation

Protected source-owned signing and crash-safe capture admission, only after authorized Weather/demo owner handoff. Place signing keys with the owner service rather than Trash++; pin authority keys through an independently managed trust store; bind host process and trusted time; couple nonce consumption to durable snapshot receipts with crash recovery. Production activation and new source owners remain blocked. Restore, retention and Burn permissions stay separate.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-source-owner-trust-v2l-20261111
STATE // Test-only, deny-only. No live Hospital registration or local desktop changes.
ROLLBACK // Revert this PR; no existing Archive SQLite schema/data, V2k policy, Weather, Finance, Camera, GIO, or Burn pathways are modified.
