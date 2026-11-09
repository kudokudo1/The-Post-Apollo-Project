# 🏥💜 Connections C3e-R // Durable signed-evidence replay refusal (CI-only)

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · Protected host / release trust  
STAFF ROLE // DOC · Original protected Connections development  
ASSIGNMENT // Repair C3e-Q process-restart challenge replay gap  
PREDECESSOR // C3e-Q PR #1615 merged into main, 4/4 workflow checks passed  
PARALLEL OWNERS // C2v/C4b Silverblue and rollback, TASKS C5 human consent  
C4b HANDOFF // [Issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606)  
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-Q verifies a signed, challenge-bound guest-measurement **test document**, but its `OneUseTestChallenge` only records `consumed=True` in memory. Restarting the verifier makes an old signed response eligible for accidental acceptance if the same challenge is supplied again.

C3e-R adds explicit, limited durable *test-state* custody on a disposable GitHub Linux runner:

1. An explicitly initialized `/run/c3er-ci-*/challenge-ledger.sqlite` SQLite ledger belongs to root, mode 0600, inside a root-only mode 0700 directory. Initialization is a separately invoked CI-fixture step and **never occurs implicitly during verification**. Missing, symlinked, corrupt, untrusted or broadly writable ledger state is refused.
2. The test verifier generates unpredictable 32-byte challenges with `os.urandom`, atomically **registers each challenge digest as issued before returning the challenge to the caller**, and does not expose or store the raw token.
3. It refuses unknown or already consumed digests before cryptographic work. For issued digests, it invokes **existing C3e-Q's real detached OpenPGP signature**, independently pinned signer/RPM/script/interpreter hashes, process PID/start, unit, SELinux marker and negative-authority checks.
4. Only after every Q check succeeds does it atomically update SQLite using `BEGIN IMMEDIATE` with `WHERE digest=? AND state='issued'`. Only one of simultaneous consumers may succeed. A failed signature or wrong independent pin leaves an issued challenge unconsumed; no receipt is emitted before the consumption transaction commits.
5. Its returned receipt always has `signedGuestOriginAuthenticated:false`, `installedGuestMeasured:false`, `hostAuthenticated:false`, `canApprove:false`, `credentialActionsEnabled:false`, `productionAuthority:false`.

The 20 new cases exercise valid signed challenge consumption, fresh-verifier and **real subprocess restart replay refusal**, concurrent double consume, invalid signing key/signature/pins, unknown challenge, failure-preserving issuance, two independent challenges, disappearing/corrupt/symlinked/writable ledger, schema mismatch, unusual journal files and denial in non-CI environments. Previous C3e-Q and signed recovery tests are retained.

This is a source/test/workflow/doc-only change in the DOC lane. It does **not** modify C4b-owned guest files, the deployed QML broker, OS service accounts, credentials, or the TASKS C5 consent implementation.

## HOW TO USE

The PR's GitHub workflow `.github/workflows/connections-c3er-durable-challenge-ledger.yml` runs with a disposable Ubuntu 24.04 root fixture only. It does not run against the operator's Fedora Silverblue machine, and it never opens a network provider connection.

## VERIFY

- [ ] Exact-head 20 durable challenge tests pass, including actual second-process replay and concurrent consumers.
- [ ] Existing C3e-Q signing tests and C3e-I crash/release recovery regressions pass.
- [ ] Root-pinned release, Fedora signed RPM and Meta Apollo Grammar pass at exact head.
- [ ] Independent source/security review and operator final acceptance.

## WATCH OUT FOR

The root-owned SQLite database is **not independent rollback-resistant custody**. A privileged process or restore of all ledger backups can roll back both issued and consumed states, and explicit re-initialization by the root test supervisor is outside this test's authorization model. It is not C3e-F's independently protected release witness and has no trusted signer enrollment outside disposable CI.

A valid detached signature proves only that a key signed test data, not that real C4b Silverblue measurements were accurate. In-memory and local SQLite replay resistance are not protected operator enrollment, persistent witness authority, remotely authenticated guest provenance, secure memory integrity, human consent or real provider credentials. Any attempt to connect these receipts to `ConnectionsBroker.qml` or turn on `hostAuthenticated` must be rejected.

The C4b owner must still supply actual signed installed-host/runtime evidence inside the accepted guest, with its existing systemd/D-Bus/SELinux checks and full rollback/cleanup lifecycle. Owner-coordinated protected signing and durable external nonce custody are separate preconditions to production.

## CHECKLIST

- [x] Confirm Q's merge into main and all 4 exact-head CI checks.
- [x] Confirm C4b rollback ownership, open #1606 and Q's one-process replay gap.
- [x] Add bounded root-owned SQLite test ledger with atomic issue/consume.
- [x] Add 20 adversarial tests including restart and concurrency.
- [x] Add CI and durable handoff.
- [ ] Fix any observed exact-head CI failures within the DOC branch.
- [ ] Independent review, merge authorization and final operator acceptance.
- [ ] C4b-produced verified booted Silverblue service measurement and independently trusted signer/anti-replay lifecycle.

## NEXT / DECISIONS

Keep C3e-R main-based, draft, and unmerged pending checks. DOC's next primary integration is not another new standalone host: coordinate C4b's **real installed service measurement producer** on [issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606), and only after that consider signed service enrollment and C5 operator consent for a real provider transaction.

Production HOLD. No local machine modification or live Hospital registration claimed.
