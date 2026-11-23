# 🏥💜 Universal Connections // Local security development now → independent trust custodian later

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity · DOC 1  
**ASSIGNMENT:** Preserve the operator's staged implementation decision in full words, independent of older A/B/C option labels  
**OPERATOR DIRECTION:** **LOCAL-FIRST DEVELOPMENT, THEN INDEPENDENT TRUST AUTHORITY** once a protected NAS or additional Post-Apollo computer is available. This is an accepted **development sequence**, not approval for production Sign-In, a particular server, private key, or rollout.  
**STATE:** Development roadmap; future custodian architecture / host / owner / root / recovery still need explicit acceptance. **Production protected Sign-In HOLD.**  
**RELATED:** [C3e custody/admission RFC](./connections-c3e-protected-identity-witness-custody-admission-rfc.md), [operator signer history #2192](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2192), [original trust handoff #2018](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2018), [owner ledger #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119).

## TWO MODES // Plain-language names, not just option letters

| Name | What it means | Authority boundary |
| --- | --- | --- |
| **Local Development Ledger** (formerly **Option A**) | The current computer runs a small **test-only** security process backed by local SQLite. It stores simulated enrollments, one-use challenges and history to develop the interface and test rollback/crash behavior. | **Cannot independently authorize real Sign-In or prove that its own history has not been rolled back.** |
| **Independent Trust Custodian** (future direction from **Option C**) | A separately administered security process on a suitably isolated NAS or another Post-Apollo computer retains the real, current trust roster, signed history, challenge-spend state and restricted signing authority. | **Potential production source of truth only after real enrollment, isolation, crash/rollback testing and operator acceptance.** |

The operator approved the **sequence**: build with the Local Development Ledger now, then deliberately migrate to an independently protected custodian when suitable hardware is ready. The operator has not selected the specific NAS/computer, the custodian administrator, keys, backup topology or release date. **A migration is a new trust enrollment and cutover, not an automatic promotion of the SQLite database.**

## IMPLEMENTATION // What is actually being stored and run

A *security service* is a program that receives requests to look up enrolled public keys, issue one-use challenges, verify evidence and manage a durable history of decisions. A separate database holds its records. The source code and build/test recipes belong in the repository; they are **not** the security authority themselves.

- **Enrollment roster:** which separately authorized public signing keys/roles, host identities, signed releases and policies are current, revoked or expired.
- **Current history head and sequence:** the authoritative latest committed digest and monotonically advancing position. Checking a signed old head without a protected current reference cannot prevent rollback.
- **Challenge ledger:** which unpredictable one-use challenges were issued, to what exact purpose/host/release, their deadlines, and whether each was consumed, revoked or left UNKNOWN after a crash.
- **Signed terminal receipts:** authenticated records for a specific committed/denied/recovery outcome, bound to the original request, head, issuer and key epoch.
- **Private signing keys:** *separate from code and ordinary database exports*. Development uses disposable synthetic keys; eventual production custody and key recovery need their own approved protection and access controls.

The key mechanism is that a verifier must ask an **authority it already trusts** what the latest valid state is, instead of trusting whichever old record the gateway presents. This is why a local SQLite file is valuable for implementing transaction behavior, but cannot be the sole real antirollback authority when the guest and its database can be restored together.

## PHASE 1 // Local Development Ledger: build and test on existing Post-Apollo hardware

**Meaning of former Option A for this phase:** a *development-only* process and SQLite ledger on the current development computer, or disposable CI runner. This is **not** production trust custody.

**Storage and execution:**
- **Program:** source code in GitHub, executed in a disposable development/test environment only. No local machine service is installed by this decision.
- **Records:** SQLite test database and test backups in isolated test-owned directories. Never label a fixture database the authoritative protected history.
- **Keys:** new disposable CI/development key pairs and clearly marked fake root fingerprints, never a production enrollment key or real provider secret.
- **Client:** DOC 1's read-only verification/admission seam and DOC 2's separately owned C4b Silverblue gateway-evidence seam operate against strict test contracts, not arbitrary trusted production inputs.

**Build the future interface now:** define versioned, purpose-specific *conceptual* operations for reading an authenticated trust snapshot, issuing a challenge, accepting one proposed history transition, looking up its terminal outcome and revoking an enrollment. The actual wire schema, API names, authentication and durable commit implementation stay pending owner review. Keep verification code separate from whether the backend is local SQLite or remote custodian.

**Developable behavior:** schema validation, role separation, signature and receipt checks, transaction atomicity simulations, concurrent/duplicate challenge attempts, timeout/UNKNOWN handling, simulated backup restore, exact C4b process/release/receipt-key matching and clearly negative authority flags.

**Not allowed in this phase:** real root enrollment; production Sign-In `BEGIN`; provider credential grants; trusted `hostAuthenticated`, `canBeginSignIn` or `credentialActionsEnabled`; independent antirollback claims; silently falling back to local authority when remote service becomes unavailable. Tests can show how the design behaves, not that the development laptop can vouch for itself.

## PHASE 2 // Prepare independently protected authority hardware

The operator plans to bring online a **NAS and additional Post-Apollo computers**. Either could potentially host an independent service, but **network location alone does not make it independent**.

- **Preferred candidate for evaluation:** a separately administered security process on a dedicated machine, or properly isolated NAS compute environment, whose credentials, service binaries, signing keys, administrative control, history storage, backups and recovery rights **cannot all be rewritten or restored together with the Post-Apollo desktop**.
- **NAS as storage only:** a network share mounted read/write by the desktop is **not** an independent security authority. If the desktop administrator can overwrite database files, signing keys or backups, the same rollback flaw remains.
- **Dedicated computer:** may be simpler to harden than a multipurpose NAS; it still requires a documented enrollment ceremony, hardened runtime, audited updates, authenticated network transport and independent backups.
- **Availability:** loss of the independent authority should cause protected operations to return **HOLD / UNKNOWN**, not permit local trust fallback. Safe read-only diagnostics may remain available.
- **Cost:** a self-hosted custodian need not require a paid cloud subscription. Actual hardware, power, backup, maintenance and incident-response costs still apply.

The independent custodian is **not automatically approved** when a NAS comes online. An operator-appointed owner must specify isolation, security/backup authority, root custody, service/host identity, key rotation/revocation and recovery. A hardware TPM/HSM may improve key protection, but is not assumed present or sufficient by itself.

## PHASE 3 // Migration: preserve audit history without pretending local tests were trustworthy

**This is not merely copying a SQLite file to the NAS.** Moving records changes where bytes live; it does not retroactively make caller-supplied root pins or old test signatures authentic.

1. **Approve independent custody:** appoint an actual custodian and choose its hardware/network boundary, signed software release, operator-root verification ceremony, key-revocation ownership and recovery plan. Obtain DOC 1, DOC 2, Nurse 2 and operator dispositions under their existing roles.
2. **Provision new protected trust:** initialize independent authority keys and separately enroll scoped release/host-witness/denial-receipt/history roles using an operator-verified fingerprint. Existing development private keys and synthetic fixture roots **must not be promoted**.
3. **Freeze and classify local state:** stop local development-ledger writes during export. Export any useful historical diagnostics with checksums and provenance as **untrusted reference/audit data**, not as a fresh authenticated history head, already-spent production grant, real revocation authority or root enrollment.
4. **Establish a new trusted genesis:** create a new explicit independent history epoch/head/sequence and policy floor. Invalidate every outstanding local development challenge and simulated lease; revoke any inappropriate old key. Do not carry over a local sequence as proof of monotonicity.
5. **Connect real source evidence:** DOC 2's independently assessed real installed Silverblue release, running gateway process/seat and actual receipt signer must be tied to custodian-issued fresh challenges and independently enrolled keys. DOC 1's verifier checks the external current state and protected origin, with domain-separated roles.
6. **Shadow-verify first:** compare the old local test client and new custodian under read-only/deny-only conditions. Never treat agreement between two copies as independent authority if one supplied the other's root/current head.
7. **Switch authority explicitly:** only after review, configure the client to use the chosen custodian as the **sole** source of authoritative root/revocation/current history/challenge state. Keep any desktop cache diagnostic-only, or independently validate its freshness. If custodian access is lost, fail closed; **do not automatically switch back**.
8. **Test failure and recovery:** repeat real-machine process/seat/key substitution, rollback/fork, two simultaneous commits, reboot, lost ACK, partition, stale replica, backup restore, root rotation/revocation and independent storage-loss drills. A single challenge commits at most once. Any uncertain outcome remains UNKNOWN/HOLD pending authenticated reconciliation.
9. **Separate final approval:** C5 exact human consent, provider-specific authorization and Identity Center command safety are additional gates. Native CI success and a signed history receipt do **not** alone enable production Sign-In. Operator accepts installation and activation separately.

If the final host/custodian cannot preserve trusted history through restore, replacement or compromise, migration **does not pass**, even if all database rows copy successfully. A new trust epoch may require explicit re-enrollment and invalidate prior attempted operations; no silent replay or automatic carryover.

## HOW TO USE // Exact responsibilities

| Owner | Develops or decides | Must not treat as its own |
| --- | --- | --- |
| **DOC 1 · Protected C3e** | Test ledger/verifier interface, independent-current-head and challenge admission checks, source trust/revocation contract, migration/refusal tests | DOC 2's Silverblue installer/service code, real root administrator, C5 human consent |
| **DOC 2 · C4b Silverblue** | Real signed installed release, running process/SELinux/systemd/receipt key and guest kernel-observation evidence | C3e's authority to approve a self-generated guest key or custodian root |
| **Operator / appointed future custodian** | Select independent machine/NAS isolation, verify initial root fingerprint, own protected keys/history/backup, approve cutover and recovery | Assume a GitHub PR or test generated a trusted root |
| **Nurse 2** | Exact-head independent source, native/antirollback/cutover review | Operator production acceptance |
| **C5 and Identity Center owners** | Active-human consent, scoped one-use spend and safe Sign-In command/receipt lifecycle | Using host evidence alone as approval to authenticate or access providers |

For other Post-Apollo subsystems (Forest, Hospital, TimeW), sharing a protected **infrastructure service** is a possible future operator choice. It **must not** mean one universal root role, one universal grant, a shared consent capability or interchangeable signature audience. Each owns distinct authorized purposes, key delegation, requests, histories and recovery contracts.

## VERIFY // Acceptance checklist

**Local development ready for test use**
- [ ] New local ledger/protocol is explicitly labeled `DEVELOPMENT_ONLY` and all production authority flags remain false.
- [ ] Atomic one-use operations, duplicate/fork tests, stale-root and crash/backup simulation work in isolated CI.
- [ ] No production keys, real credential contents or provider sessions enter the local test database.
- [ ] DOC 1 / DOC 2 interfaces avoid hardcoding one local SQLite filesystem path as the sole future authority.

**Independent migration ready for operator acceptance**
- [ ] Custodian administrative/security/backup/rollback domains are independently verified.
- [ ] Operator root and current-history state are independently enrolled and authenticated; new epoch cannot inherit fixture authority.
- [ ] One-use challenges and head advancements are durable, atomic, replay-resistant and independently recoverable.
- [ ] Actual running gateway release/process/receipt key and seat are bound to fresh external challenge and correct purpose.
- [ ] Old local cache, disconnected NAS, stale replica, copied backup or changed guest root cannot grant Sign-In.
- [ ] Backup/restore/key compromise/fork/partition drills and independent Nurse 2 review pass.
- [ ] Operator separately approves production custody, native installation, C5 consent and Sign-In cutover.

## WATCH OUT FOR

**Operator direction is to build locally first and migrate later**, not to use the local ledger as temporarily acceptable production security. There is no automatic security promotion at migration time. No protected service, new root, real credential, local host file, NAS share or external server has been provisioned by this document. **Protected production operations remain HOLD** until an independently verified custodian and the remaining owner gates are approved.

## NEXT / DECISIONS

**Decision accepted for development sequencing:** local SQLite test-ledger and pluggable verifier interface first; independent self-hosted custodian later when NAS/additional machines are available. **Not yet selected:** actual machine, privileged root/custodian owner, transport, signed wire schema, hardware key storage, backup and recovery ceremony, timetable, and production activation. Preserve [C3e #2018](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2018) as the operator decision location and [#2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119) for cross-owner coordination.
