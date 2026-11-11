# Trash++ // V2k Deny-Only Signed Capture Contract

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal source archive
STAFF ROLE // External DOC-compatible development; live Hospital registration not verified
ASSIGNMENT // Signed source-owner capture claim and durable replay contract, synthetic-only
PERMISSIONS // GitHub draft branch/tests/docs. No local host writes, production keys, source authorization, or Restore/Burn expansion.

## IMPLEMENTATION

- Adds scripts/trash/archive_v2_signed_capture.py, an Ed25519 **signature verifier only**. It uses Python's established cryptography library; no homegrown signature algorithm, private-key generation, signer, fallback to unsigned SHA-256 or automatic key discovery.
- The canonical claim schema post-apollo.trash-capture-owner-proof.v2k binds a fixed audience/purpose, allowlisted demo-scrape or weather-events owner, resource ID, source revision, normalized payload SHA-256, source-observed time, issued/expires timestamps, signer key ID and 128-bit nonce. Unrecognized fields, arbitrary file paths, other owners and different purposes are rejected. Expiry is at most five minutes with a bounded 30-second future clock skew.
- Verifier requires an **externally supplied pinned policy** and checks exact owner/key ID/scope, source identity, source revision, current payload digest, policy validity window, revocation and Ed25519 signature. Policy origin is strictly TEST_FIXTURE_ONLY. Any production-origin policy is refused as SOURCE_TRUST_NOT_PROVISIONED, because neither permitted owner has yet supplied an independently authorized signer/public key. A key ID or public key inside a proof can never establish trust.
- Every successful fixture verification still returns signatureVerified=true but sourceAuthorityVerified=false, humanConsentVerified=false, captureAllowed=false, restoreAllowed=false, burnAllowed=false and productionAllowed=false.
- Adds scripts/trash/archive_v2_replay_ledger.py: explicit test-only 0700-directory SQLite nonce ledger. After valid signature verification, a nonce may be durably recorded once; repeat use is refused even if the process is restarted. The ledger never touches the live Archive database, Quickshell data, original sources or a protected trust authority. Invalid signatures never consume a nonce.
- No CLI, UI button, live capture wrapper, production enrollment, key provisioning, data migration, scheduler or host activation. V2i's existing unsigned metadata receipts and V2j's read-only chain audit remain exactly as they were. A signature over a source claim is not a signature on the Archive itself or proof of human consent.

## HOW TO USE

V2k currently has **no live button or production entry point**. Its consumer is the synthetic Python test suite. This is intentional: a real source owner's signing key and pinned authority policy have not been established. Existing Trash++ > ARCHIVE > SAVE SNAPSHOT, CONFIRM COPY and VERIFY CHAIN keep their current meanings and permissions, and V2i receipts remain explicitly UNSIGNED_LOCAL.

When a protected signing authority has been independently approved in a future milestone, the source owner would issue the claim, a protected verifier would validate it against a pinned key and approved source scope, and a durable nonce witness would be consumed in an atomic capture contract before source data could be copied. That production path is not supplied by this change.

## VERIFY

Synthetic tests use a newly generated ephemeral Ed25519 keypair held only in the running test process. They cover valid signature with all permissions still denied; altered source owner/resource/revision/payload; wrong signer key and modified claims; invalid Base64; unapproved owner/purpose/audience; malformed time/nonce; expired or far-future claims; revoked/wrong/expired signer policy; unsupported production policy; missing cryptography backend; SQLite nonce consumption persisted across reopening; replay rejection; invalid signature not consuming a nonce; and symlink/unsafe-root refusal.

The GitHub Trash CI installs the cryptography verifier dependency for tests only; **this does not install it on the user's desktop**, activate a signer or create a production key.

## WATCH OUT FOR

- TEST_FIXTURE_ONLY is a deliberately hard deny gate. Successful Ed25519 verification proves a test key signed particular bytes, **not** that Weather or the demo owner is actually registered or authorized.
- No production public keys are pinned in this repo, no private keys are created outside tests, and no host-side dependency is installed. If cryptography is unavailable, the verifier refuses rather than using an unsafe fallback.
- This test ledger is not transactionally coupled to ArchiveStore. In a real capture, nonce consumption and the snapshot save must be crash-safe and tied to the source revision and authority record. Do not use this test-only fixture to authorize actual writes.
- Clock skew, expiry and key validity are verified only with the caller-provided time and pinned test policy. A protected time source, authority-owned key lifecycle, key revocation log, process provenance and independent attestation are future security gates.
- This does not provide human approval, signed payload provenance, retention permission, deletion authority, production rollback safety or the ability to restore an archive.
- Any owner beyond the two existing pilot scopes, particularly Identity, Hospital, personal finance or protected host data, requires an explicit separate owner contract.

## CHECKLIST

- [x] Current V2j merged state, canonical protocols and concurrent ownership checked
- [x] Strict signed-claim schema and Ed25519 verification, no crypto fallback
- [x] Fixture-only pinned-policy and deny-only return
- [x] Durable private test nonce ledger and replay refusal
- [x] Synthetic adversarial signature, expiration, revocation and replay tests
- [ ] GitHub CI green and corrections
- [ ] Independent security review and source-owner authority approval
- [ ] Explicit operator merge/install/production decisions

## NEXT

**V2l // Source-owned signed issuer and protected trust-store integration.** The implementation should establish each source-owner's actual authority to sign a capture request, immutable public-key enrollment and revocation floors, trusted time/process evidence, and durable nonce use coupled to a validated snapshot transaction. Production activation, any new protected owners, and automatic Restore/Burn remain blocked until these contracts and approvals are independently verified. It should not silently reuse Identity Center C3e keys as source-copy authorization.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-signed-capture-deny-gate-v2k-20261111
ROLLBACK // Revert test-only verifier, ledger, tests and workflow dependency. No Archive data or schema changes; no user key material involved.
STATE // GitHub-only draft development, not live Hospital registered, no merge/activation authority.
