# 🏥💜 Connections Forest C5 // Writer enrollment + custody CLAIM preflight (NO AUTHORITY)

**PATIENT:** The-Post-Apollo-Project
**ROOM:** Connections C3e/C4b/C5 ↔ Forest B4c
**STAFF ROLE:** DOC 3 · external Hospital-compatible, live registration unverified
**SCOPE:** additive Connections-owned proof contract, read-only, not installed
**BASELINE:** #2168 / #2171 / #2175 / #2180 already merged and Nurse 2 scoped PASS
**STATE:** draft review candidate; production Forest authorization HOLD

## IMPLEMENTATION

Previous #2180 checks the signature on an exact COMMIT_GENERATE terminal receipt, but its expected writer key, release, predecessor hash, counter and permit are caller-selected. A signature can be produced over a fake COMMIT without a Forest SQLite transaction.

New isolated \`services/connections/forest/ForestC5WriterCustodyClaimPreflight.py\` adds a second **claim-consistency-only** layer:

- Exact canonical, role/domain-separated enrollment claim: writer key, installed release digest, writer instance, enrollment epoch, historical validity window and claimed enroller key.
- Exact canonical, separately signed journal-custody claim: receipt SHA256, original intent SHA256, permit/transaction, outcome, writer identity/epoch/key/release, sequence, predecessor and custody recording time.
- **Three distinct fixture keys**, writer + enroller + journal custodian; verify all three Ed25519 signatures. Reject role reuse, mismatched keys, modified signatures, wrong domains, replay/counter regression, malformed/noncanonical/duplicate JSON and any receipt/roster/journal mismatch.
- Reuse #2180's original receipt verifier; **do not weaken** its exact intent and signed terminal constraints.
- A receipt received after its original consent expires can be *inspected* against the purported writer key's historical validity. That cannot reauthorize GENERATE or settle UNKNOWN_HOLD.

**Security boundary:** enrollment and journal evidence are STILL supplied entirely by disposable caller fixtures. Anyone can fabricate all three keys and a plausible receipt+journal. Two additional valid signatures do **not** independently enroll the Forest writer, prove active Linux host/seat, prove disk fsync, establish a trusted journal floor, or authenticate a real SQLite COMMIT/ROLLBACK. The new source therefore always returns \`THREE_UNENROLLED_SIGNATURE_CLAIMS_CONSISTENT_NOT_SETTLED\`, \`safeActions=[]\`, and all authority/settlement flags FALSE. There is no signer, local service, process runner, key store, socket, C5 issuer, database writer or production bridge.

## OWNERSHIP BOUNDARY

- **DOC 3** owns this Connections-side evidence contract and denial tests only.
- **DOC 1** must separately own trusted source/installed-root enrollment and protected original process/seat proof.
- **DOC 4** owns Hospital-specific C5 consent; Forest C5 still needs its own exact audience, one-use protected issuer fence and serialized revocation authority. No reuse of another service's grant.
- **Forest backend owner** must own actual durable post-transaction COMMIT/ROLLBACK journal construction, native writer delivery and recovery semantics. This PR does not implement or edit Forest backend.
- **Nurse 2** must independently inspect exact head and hostile source tests **before merge**. Do not merge merely because CI is green.

## VERIFY

Dedicated CI runs 18 fresh hostile claim-consistency tests, plus the 16 signed-receipt, 12 signed-role, 12 canonical interop, 12 real two-DB revoke-ordering and 16 B4b synthetic pre-COMMIT checks: **86 tests expected**. Source static guards refuse DB writes, signers, socket/listener, privilege or production authority; Python compilation is checked. These tests use disposable keys and zero private user conversation data.

## WATCH OUT FOR

The next *real* gate is not another caller-authored fixture. A future verifier must receive independently trusted, historically versioned writer enrollment, kernel-verified original peer/release/seat, an issuer-held monotonic revocation/permit ledger and authenticated durable writer-journal evidence tied to the actual Forest SQLite transaction. These are separate owner/security decisions. The issuer's existing \`UNKNOWN_HOLD\` must remain until authenticated terminal proof or separately authorized recovery; TTL/lease expiration, a signed claim, a missing response, or another model run are not settlement.

Production Forest / Sign-In / TimeW Restore remain HOLD. No Fedora host mutation, installed keys, private data, Forest writer integration or live grant changes are part of this source-only milestone.

## NEXT / DECISIONS

Request independent Nurse 2 exact-head **pre-merge** review. Ask DOC 1 and Forest backend owners to agree on the *actual independent source* of writer root/release, custody checkpoint, transaction journal and history rollback resistance. Keep this module uninstalled and fail-closed until those sources exist and the operator separately approves production activation.
