# 🏥💜 Connections Forest B4c // Signed terminal writer receipt preflight (NO AUTHORITY)

**PATIENT:** The-Post-Apollo-Project
**ROOM:** Connections C3e/C4b/C5 ↔ Forest B4c
**STAFF ROLE:** DOC, external Hospital-compatible, live Hospital registration unverified
**OWNER SCOPE:** Forest-facing Connections receipt verification; Forest B3/B4a/ForestW UI and separately paused Identity protected producer remain with other workers
**STATE:** source-only, uninstalled, VERIFY-ONLY, production Forest HOLD
**CHECKPOINT:** Reviewed merged #2168 (two-store revoke ordering), #2171 (two signed fixture roles), #2175 (canonical signed-intent interop), each scoped Nurse 2 PASS

## IMPLEMENTATION

Before the protected C5 issuer may mark a previously admitted GENERATE attempt as COMMIT_CONFIRMED or ROLLBACK_CONFIRMED, the future **installed and authenticated Forest storage writer** must produce an independently trusted, durable terminal receipt. The older #2168 fixture settlement method accepts forgeable test data. The new standalone Connections-owned module, services/connections/forest/ForestC5TerminalReceiptPreflight.py, does **not** replace that fixture or connect to the Forest database.

It validates **only cryptographic consistency of a candidate signed writer receipt**:
- Require the exact previously defined Forest COMMIT_GENERATE canonical intent and a fixed Forest-only terminal receipt schema/commit-writer role.
- Bind intent SHA256, actual B3 reserved attempt, principal/Tree, request/grant/model/revision, challenge, consent epoch and exact commit-host release digest.
- Bind an exact one-operation permit ID, previous writer journal hash, monotonically increasing journal sequence and storage transaction label.
- Require a separately supplied 32-byte Ed25519 public key with SHA256 matching a separately supplied expected pin; verify its 64-byte signature over the exact canonical writer-receipt bytes.
- Permit late receipt verification even **after the original grant expiry**. Expiry must not permanently prevent resolving a prior admitted operation; a terminal receipt still requires separately trusted durable writer evidence.
- Reject wrong domain, role, outcome, key, signature, field grammar, duplicate JSON keys, malformed JSON, mismatched consent/model/attempt, mismatched writer release, swapped permit, stale counter, predecessor hash, and noncanonical encoding.

**Crucial limitation:** every expected key pin, writer release, journal predecessor, floor, permit and original signed intent in this phase is supplied by a **disposable caller fixture**, NOT by an independently enrolled protected C3e/C5 host. Anyone may create their own key and sign a claimed COMMIT. A valid signature here is only byte consistency. The source exposes no issue_grant, settle_permit, native writer, C5 gate or service. Every returned production, verified human, writer process, journal durability, C5 fence and Forest read/commit/tool permission remains **False**; safeActions is always empty.

This module's result `UNENROLLED_RECEIPT_SIGNATURE_CONSISTENT_NOT_SETTLED` is **not a terminal outcome**. Its claimed terminal value is explicitly `claimedTerminalOutcomeUntrusted`. Do not pass it to the #2168 test fixture's settlement method, and never import it into Forest B3/B4a before a protected issuer and writer are independently accepted.

## VERIFY

Dedicated CI pins cryptography 46.0.4 on a disposable Ubuntu runner and runs:
- 16 new adversarial signed-writer-receipt cases
- 12 original Forest signed-role preflight cases
- 12 original two-store revocation reference cases
- 12 signed intent/reference interoperability cases
- 16 Forest B4b synthetic pre-COMMIT regressions

The tests check valid claimed COMMIT and ROLLBACK signatures that still grant no authority, receipt-after-expiry for recovery, writer key substitution and pin mismatch, exact transaction/permit binding, malformed and duplicate JSON, replay counter floor and predecessor chain, wrong intent, fake COMMIT without a real database, and no C5 fence settlement.

## WATCH OUT FOR

Real production still needs the **independently enrolled** signer trust root and current writer release, kernel-authenticated process and active seat, real human approval, protected C5 one-use grant/permit with revocation ordering, and independently verifiable durable writer journal built **after** actual Forest SQLite COMMIT or ROLLBACK. Neither the reported signature nor a claimed journal sequence proves those facts. External key custody and rollback-resistant receipt history cannot be supplied by caller arguments. Missing, contradictory or stale receipts must remain UNKNOWN_HOLD without automated re-inference, permit release, or revocation-complete acknowledgment.

The separately paused Identity signer work in Issue #2018 remains paused. No actual signing roots, live source, local files, private user chats or installed services are changed by this test-only preflight.

## NEXT / DECISIONS

Request Nurse 2 exact-head independent **pre-merge** security review. Once source consistency is accepted, the next Connections owner work is a protected installed-writer witness/receipt source and independent custody interface, not promotion of this fixture result to real authorization. The Forest backend worker must own future actual COMMIT/ROLLBACK journal creation and durable delivery, with a separate explicit transfer. Production Forest, Identity Sign-In and TimeW Restore remain HOLD.
