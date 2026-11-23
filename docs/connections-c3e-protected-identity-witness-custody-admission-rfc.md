# 🏥💜 Universal Connections // C3e protected Identity witness custody and native-admission decision

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity  
**STAFF ROLE:** DOC 1 · operator-assigned successor, external Hospital-compatible; live Hospital registration unverified  
**ASSIGNMENT:** Define a reviewable real-trust custody and verification contract after recovered signed-history source #2192  
**STATE:** **PROPOSAL / AWAITING CUSTODIAN AND OPERATOR DECISIONS / PRODUCTION HOLD**  
**BOUNDARY:** C3e owns issuer trust and verifier admission; DOC 2/C4b owns signed official Silverblue package and gateway runtime; C5 owns actual human consent; Identity Center owns native sign-in commands.

This is a **decision and implementation interface**, not an enrollment, a real signed authority, an enabled service, a new wire protocol, or a proposed relaxation of the existing fail-closed application.

**OPERATOR DEVELOPMENT DIRECTION (ACCEPTED):** Build a **Local Development Ledger** first, using SQLite and disposable test keys on existing hardware, then move to an **Independent Trust Custodian** on separately protected NAS/other Post-Apollo computing infrastructure when available. This selects the *development sequence only*. It does **not** approve local records as real production authority, a final custodian machine or root, migration cutover, or Sign-In activation. The concrete storage, roles, cutover, rejection tests and recovery plan are documented in [Local Development Ledger → Independent Trust Custodian migration plan](./connections-c3e-local-development-to-independent-custodian-migration.md).

## IMPLEMENTATION // The missing property

An Ed25519 signature proves that some holder of a private key signed exact bytes. A release manifest, a kernel/process snapshot, a signed denial receipt, and a signed history link can each be internally consistent while still being **self-issued by the same compromised guest**.

The existing concrete evidence is deliberately narrower:

- C4b's official Fedora Silverblue guest can compare its installed signed RPM/script, running service PID/UID/start/cgroup/SELinux and actual test receipt public key, rejecting guest-local substitution. Its private receipt signing key is not uploaded to GitHub. The test guest generates its own release root; this is **guest-local correspondence**, not independent enrollment.
- C3e-A/AG/AH and C3e-AF/Z perform release-policy and actual Linux observation/signed-role/one-use **fixture** checks. C3e operator enrollment #2075 rejects wrong caller-pinned roots and revoked roles, but does not authenticate the source of those pins.
- C3e signed history #2192 verifies a separately signed proposal with exact previous head, sequence, enrolled role hashes and fresh challenge digest. It does **not** own the current head, spend the challenge or store the new head. #2192 merged with 4/4 workflows and 88/88 dedicated tests; independent Nurse 2 reviewed its exact source head with **retrospective scoped PASS** ([review #6015491735](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2192#pullrequestreview-6015491735)). That review did not retroactively fulfill a pre-merge review gate.
- C4b's original C3e-N join reports `COMPATIBLE_NOT_BOUND` and the third-signer signed-host evidence still uses a disposable CI signer. Existing positive diagnostics must **never** set `hostAuthenticated`, `canBeginSignIn`, `credentialActionsEnabled`, or any C5 authorization to true.

**Missing:** a separately administered, operator-enrolled source of trust, with authoritative currently retained signing-root/revocation state, host/release/receipt-key binding, challenge issuance and one-use consumption, and rollback-resistant witness history.

## DECISIONS // Local test-ledger development can proceed; authority-bearing native code still requires custodial approval

| Decision | Candidate | Trade-off / status |
| --- | --- | --- |
| **A · Guest/local SQLite only** | Root-owned DB and signer on the same Silverblue guest | **HOLD as sole authority.** A sufficiently privileged guest rollback or restored snapshot can roll back key, nonce and history together. Useful only as a cached, read-only client or separately fenced front end. |
| **B · TPM-anchored local history** | Independently enrolled sealed key plus monotonic/rollback-resistant reference and locally persisted proof | **Evaluate, not assumed.** Must show actual hardware-backed antirollback, bounded wear/counter behavior, provisioning/ownership, migration, recovery after TPM reset/replace, revocation, and proof that a host root compromise cannot simply present an old valid current-state claim. |
| **C · Independently administered append-only authority** | A distinct protected service/host and operator-held enrollment authority with authoritative per-host history/nonce state, possibly self-hosted | **Recommended to evaluate first, not selected.** Strongest separation from guest snapshots if truly distinct in credentials, administration, backups and recovery domain. Requires availability, authenticated transport, lifecycle/backup and incident-recovery plan. No paid service is inherently required. |

**For the eventual protected production authority, required operator answers:** identify the custodian/person or protected service owner; select the independently administered authority/failure domain; approve initial enrollment root fingerprint verification ceremony and immutable role scope; choose durable history/challenge persistence and recovery policy; name authorized signed service/release, seat policy, and root rotation/revocation. The operator's decision must be recorded by an actual owner (ACCEPT / REVISE / HOLD). A CI fixture, a conversation decision proposal, or an implicit default is not enrollment.

## Protected trust/bootstrap lifecycle // proposed, version to be chosen by owners

These are *semantic phases*, **not** frozen API field names or a deployed protocol:

1. **OUT-OF-BAND ENROLLMENT:** Operator verifies an initial public root fingerprint through an independent authenticated ceremony, not from RPM/guest, browser/QML, first response, a GitHub artifact, local public-key neighbor file or C4b controller claim. A separate enrollment authority delegates **distinct** approved release, actual host-witness, denial-receipt and history-authority roles; bind exact host identity, release epoch/sequence, audience, expiry/revocation and intended service. Do not reuse Identity role material for TimeW or Hospital.
2. **CURRENT TRUST SNAPSHOT:** C3e obtains a verifier-authenticated current key roster and revocation status, release-policy floor, current history head/sequence, and issuer status from the chosen authority **outside the guest rollback domain**. Stale/unavailable/unauthenticated current state is HOLD, even when an old signed policy still verifies.
3. **ISSUE CHALLENGE:** Custodian durably records a fresh unpredictable 32-byte challenge bound to the fixed `c3e-identity-installed-gateway-readonly` purpose, exact host/release/current history head, and a finite deadline. Only the custodian can commit, expire or revoke it; an arbitrary caller-generated nonce proves nothing about who authorized the observation.
4. **C4b ACTUAL OBSERVATION:** DOC 2's installed producer exposes a bounded, protected observation for the **same running service instance**: actual signed release / installed RPM and script+unit+policy file digests, immutable interpreter/script inodes, `systemd` unit and MainPID/start, UID/GID, kernel source/packet peer, cgroup/SELinux, actual receipt public key proven by fresh signed `UNAVAILABLE` receipt, active unlocked seat/login session, boot/session identity, and the exact issued challenge. Recheck process lifetime and source origin across the observation. The signed claim's signer must already be operator-enrolled, not one minted by the observed gateway. Source evidence and signature cannot compensate for untrusted origin.
5. **READ-ONLY VERIFY:** C3e checks the signed release, independently enrolled role/custody, exact challenge, current external floor/history, verified process/seat and actual receipt key correspondence, plus all existing C3e-AF/Z/AG/AH/C4b comparison guards. Never equate a guest-local diagnostic, `SO_PEERCRED` by itself, caller-supplied process pins or a signed JSON host ID with origin authorization. Reverify time/lifetime and revocations before a final decision; no stale cache privilege.
6. **ATOMIC WITNESS HISTORY:** The independent custodian must accept one exact challenge and its observed proposal at most once, validate the current head/sequence under serialization, durably consume the challenge and append the next history head **in the same independent atomic transaction** before issuing a signed, challenge-bound terminal receipt. If source observation or commit outcome is uncertain, classify **UNKNOWN/HOLD** and query authenticated history instead of reissuing/spending again. A signed `PENDING` is not an authoritative COMMITTED result.
7. **STILL SEPARATE C5 / IDENTITY:** Even a future accepted trusted host origin must not alone initiate OAuth/PKCE, approve a provider credential, or speak for a human. C5 active-seat exact-purpose consent, provider allowlist and independently protected one-use spend, and Identity Center V5 `BEGIN/CANCEL/RECOVER` command/status rules are separate gates and separate owner approvals.

## Proposed evidence boundary // review before freezing schema

A future jointly accepted, versioned attestation must cryptographically bind at least:

| Exact evidence family | Refusal examples |
| --- | --- |
| Issuer identity and scope | Unknown/caller-chosen root, aliased role keys, revoked or superseded release, wrong audience or host |
| Runtime source | Swapped MainPID/start, restarted service, different UID/GID, signer from unrelated socket peer, wrong script or signed installed package, SELinux nonenforcing |
| Receipt correspondence | Manifest pins one Ed25519 receipt key but *actual running gateway* signs with another; substituted guest-local pubkey |
| Seat/session | Locked seat, seat switch, wrong login session or boot, compositor/process exit during observation |
| Freshness | Old signed record, wrong challenge or challenge reused after first commit, expired lease, stale external release floor/head |
| History | Guest-local head reset, restored copy of head+signature, concurrent fork from same prior head, signer's revocation after pending, missing durable terminal result |
| Failure / recovery | Crash before or after custodian commit, lost ACK, independent custodian unavailable, split state, ambiguous writer outcome |

An enrolled root cannot make a measurement true by signature alone. Real runtime measurement must come from an approved protected source. A current history head cannot be a caller-supplied string. A checked denial receipt is **not** an authorization to produce credentials.

## HOW TO USE // Owner handoff

- **Operator / appointed custody owner:** record a selected custody option and who can provision, rotate, revoke, backup and recover root/history material, with distinct authorization and release procedures.
- **DOC 2 / C4b:** supply the agreed read-only actual signed-guest runtime observation and fresh receipt-key evidence, maintaining its own official Silverblue two-reboot rollback tests. Do not add a second C3e guest script or ship private keys in RPM artifacts.
- **DOC 1 / C3e:** under the operator's staged-development direction, a **development-only local ledger and storage-independent read-only verifier interface** may be prepared using disposable keys and explicit no-authority outcomes. After the real custodian and producer contracts are accepted, implement a **new scoped protected admission client** that obtains independently current trust state and binds C4b's genuine evidence. It must fail closed until all required authorities exist. No rewriting existing C3e-AF/Z or C4b-owned transport by default.
- **Nurse 2:** independently review exact-head source, current custodian/producer trust, attack fixtures and native negative evidence. **Operator:** retains separate merge, installation and production acceptance.

There is intentionally **no setup command** here. This file creates no signer, root pin, machine service, DB, socket, credential, package, user approval, or native command. Runtime hosts and production policy remain unchanged.

## VERIFY // Native acceptance gate, after owner decisions

A future source PR must provide real, isolated runtime evidence rather than only synthetic signatures:

- [ ] Trust-root fingerprint originates in a separately authenticated enrollment authority and does not change when the guest replaces its own public key.
- [ ] Actual installed signed Fedora Silverblue gateway binds its *real* receipt signer to the approved release/process/session and a fresh **outside** challenge, including negative substituted receipt-key test.
- [ ] Privilege/process lifetime change, stale/replaced systemd MainPID, script bytes/inode, enforcing SELinux/cgroup/seat, wrong boot/session, and revoked root fail closed.
- [ ] Custodian concurrently receives two proposals extending the same old head; exactly one durable commit wins, the other refuses; challenge cannot be consumed twice, even after reboot/snapshot rollback.
- [ ] Power loss/crash at challenge issued, source observed, history commit, receipt emission and ACK-loss points leaves queryable durable outcome or **UNKNOWN/HOLD**; no automatic retry.
- [ ] Root/key rotation and explicit revocation block old but correctly signed records; rollback of guest-local policy/history alone cannot change current authority.
- [ ] Host verification never implies C5 human consent, provider permission, or Identity Center production `BEGIN`.
- [ ] Nurse 2 checks exact source and native test artifacts **before** operator-controlled merge/install/activation decisions.

## WATCH OUT FOR

The operator has **accepted a local-development-first, independently-custodied-later roadmap** but has **not** selected an independently trusted production custodian, enrolled a real signer, verified live Hospital registration, or authorized a local machine write or service activation. Do not label the proposed wire phases as approved protocol, use a caller's Ed25519 key as an operator-enrolled root, or treat a signed `UNAVAILABLE` as success. No protected authority-bearing implementation begins merely because this RFC is merged.

Do not combine Hospital D4 original-request custody or TimeW selected-window/consent with this Identity-specific purpose. Their independent owners must adopt any compatible shared custody architecture explicitly, not automatically inherit Identity signer roles.

## CHECKLIST

- [x] Reinspect Syntagma AGENTS and Hospital/authority protocol, C3e/C4b existing source and issue #2018.
- [x] Verify #2192 source and independent retrospective review; identify the real missing custody and native binding.
- [x] Draft C3e-only operator decision, protected trust lifecycle, receipt-origin contract and native attack matrix.
- [x] Record operator's local test-ledger → independent NAS/other-computer custodian development direction and explicit migration gate.
- [ ] Implement fixture-only local ledger and pluggable read-only verifier interface under its own reviewed development milestone; do not enable production authority.
- [ ] Independent DOC 2 / Identity owner assessment of producer and release/seat evidence shape.
- [ ] Named operator-authorized independent root/history/challenge custodian selects ACCEPT / REVISE / HOLD.
- [ ] Nurse 2 review of this proposal / future source and exact-head checks.
- [ ] Only after selected custody: protected read-only native client, real OS evidence, crash/antirollback tests and controlled rollout.

## NEXT

Use the [staged local-to-independent migration plan](./connections-c3e-local-development-to-independent-custodian-migration.md) for development-only ledger and future cutover criteria. Record the eventual operator/authorized custodian's *production* choice and key enrollment + recovery requirements on [C4b/C3e issue #2018](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2018), cross-link [C3e owner ledger #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119), and obtain DOC 2's signed installed-host proof acceptance on its own C4b resources. Do not proceed from an unselected assumption to native privilege. If custody remains HOLD, continue only isolated read-only diagnostics without manufacturing a new synthetic issuer.

## DECISIONS

The operator has selected **Local Development Ledger first → Independent Trust Custodian later** as the intended development sequence. This document still presents competing **production custody** architectures; a specific independently protected NAS/host, custodian, key enrollment and recovery mechanism have not been selected or accepted. C3e code ownership and concurrent workers remain unchanged. No local machine edits, live key provisioning, production sign-in, auto-merge or final acceptance of the real trust service are implied.
