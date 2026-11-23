# 🏥💜 DOC 1 // Independent custodian migration candidate: reject local authority promotion

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Connections · Protected C3e Identity  
**STAFF ROLE //** DOC 1, external Hospital-compatible; live Hospital session/registration unverified  
**ASSIGNMENT //** CI-only negative cutover preflight, after merged [#2217 local→independent roadmap](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2217), [#2224 rollbackable SQLite history ledger](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2224), [#2229 storage-independent client](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2229)  
**STATE //** New isolated test source, no production trust, no real NAS, no privilege, no keys, no network or Sign-In. **PRODUCTION HOLD**.

## IMPLEMENTATION // What the code actually does

A local test database can store a signed history head and record that a challenge was consumed, but restoring the database restores both to their old values. This was demonstrated in #2224. #2229 added a storage-independent semantic interface but **did not** turn its local records into trusted evidence.

This milestone introduces one **pure read-only candidate classifier**:
- `tests/connections/c3e_release_trust/C3eCustodianCutoverNegativePreflight.py`
- `tests/connections/test_connections_c3e_custodian_cutover_negative.py`
- a dedicated CI workflow and this explanation.

It accepts **synthetic caller-supplied descriptions** of (1) the existing C3e local test snapshot, (2) known fake role fingerprints, fake local epoch and fake challenge digests, and (3) a candidate future independent custodian's proposed new public fingerprints/epoch/genesis. It does **not** read, open or copy SQLite, import a private key, contact a protected server, fetch a root, mutate enrollment, grant consent or admit a host.

Its job is to reject *obvious unsafe cutover shapes*:

| Unsafe candidate | Required result |
| --- | --- |
| Reuse local test current history head as new authoritative genesis | Refuse |
| Reuse known disposable local signer/public-root fingerprints | Refuse |
| Alias new candidate custodian root and history-signer role | Refuse |
| Reuse any known synthetic local development epoch | Refuse |
| Carry over even one challenge digest, irrespective of issued/spent claim | Refuse |
| Assert itself already enrolled or accepted by the operator | Refuse unexpected status/fields |
| Use C5/TimeW/Hospital audience in this C3e Identity-only candidate | Refuse wrong signed purpose |
| Claim positive host, credential, production, or custodian-attested flags | Refuse or return all authority flags FALSE |
| Unknown/malformed local snapshot, fingerprints, epoch, sequence or host | Refuse |

A well-formed candidate only produces `CUTOVER_HOLD_NO_INDEPENDENT_TRUST` with `candidateFieldsConsistentInCI: true`, an explicitly *audit-only* digest of the local test head/sequence, and **every** protected-custody, host, consent and production authorization flag **false**.

The candidate's metadata is test-only. **A syntactically different public key or history head does not prove that a separate administrator controls the key or that a database cannot roll back.** These tests know only the fake local identities listed in the fixture; they cannot prove the inventory is exhaustive. Four explicit incomplete-inventory tests also show that omitted local signer/epoch/challenge records may escape *format-based* overlap detection, yet never yield protected custody, a trusted head, consent or cutover authority. The supplied candidate fields, host and epoch are caller-controlled. This is **not** the real future custodian's wire schema, a root-enrollment proof or a migration mechanism.

## HOW TO USE

There is nothing to do on the operator workstation or NAS. The new negative classifier runs in disposable GitHub CI using in-memory test dictionaries. No provider connection, network endpoint, filesystem migration or production data access.

The source and tests are part of DOC 1's protected C3e lane only. DOC 2 continues to own the signed Silverblue installed gateway/source proof; C5 and Identity Center own human consent and command execution. Forest, Hospital and TimeW retain purpose-specific roles and cannot inherit C3e Identity permissions or keys.

For later independent cutover, a separately approved custodian must generate and protect its **own** keys, independently enroll the verified root and release/host-witness roles, establish fresh protected current history and one-use challenge state, authenticate transports, make signed terminal outcomes queryable after crashes, and pass real failure/recovery/backup-restore reviews. Local data may be retained **as untrusted audit evidence only**; it must never be treated as a protected genesis or permission.

## VERIFY

This milestone's new test suite contains 32 rejection and diagnostic cases including root/history alias, old head/epoch/nonce migration, purpose confusion, forged authority fields, malformed hashes, bool-as-counter, non-ASCII host, and unavailable protected authorization. The workflow also reruns the existing 28-case storage boundary, 28-case local ledger, and 24+22+22+20 signed history/enrollment/AF/Z tests. It retains the static `ConnectionsBroker.qml` credential-action disabled assertion.

No new production service, signing helper or privileged native interface is present. A passing source-only test cannot certify an NAS computer, service authentication, independent root or antirollback storage.

## WATCH OUT FOR

**Review debt:** #2229 merged after exact-head CI **4/4 PASS** but before independent Nurse 2 review. Its exact head `925193aa0906738bbaa03bd96957db7960baa1b2` requires an explicit retrospective review; this new draft does not cancel that debt. Do not merge this new work before a fresh exact-head Nurse 2 review and the operator's merge authorization.

**No automatic fallback:** When the future independent custodian is missing, stale or failed, protected operations must return HOLD/UNKNOWN, not reconnect to the local SQLite test ledger. This module's always-false authority flags are not a replacement for that future protected runtime check.

## CHECKLIST / NEXT

- [x] Re-check current `main`, source #2229, independent review status and DOC 5's separate TimeW C5 custodian probe #2228.
- [x] Keep new tests isolated in DOC 1-owned C3e files without modifying existing signed-history, storage-neutral interface or DOC 2/C5 runtime.
- [ ] Exact-head test workflow and inherited regressions pass.
- [ ] Nurse 2 independent pre-merge source/CI review and retrospective #2229 review.
- [ ] Operator gives separate merge decision; production remains HOLD.
- [ ] Eventually choose and independently verify the actual NAS/other computer, root custody, key rotation/revocation, fresh epoch/genesis, native host/seat provenance, external atomic commit, rollback recovery and C5/Identity activation gates.

## DECISIONS

The operator selected the **Local Development Ledger first → independently administered custodian later** development sequence. This change only documents/executes a **test-only rejection of obviously invalid cutover proposals**. No actual production custodian has been selected or authorized; no keys or services are provisioned. **PRODUCTION HOLD**.
