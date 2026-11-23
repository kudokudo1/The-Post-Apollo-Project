# 🏥💜 DOC 1 // Local read-only security-service process experiment (CI only)

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM / ROLE:** Universal Connections · Protected C3e Identity · DOC 1, external Hospital-compatible, no live Hospital registration verified  
**ASSIGNMENT:** Test an actual local process boundary around the existing development-only security ledger without installing a service, inventing a production transport or activating Sign-In.  
**REUSE:** [Local-first architecture #2217](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2217), [atomic disposable SQLite ledger #2224](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2224), [storage-independent interface #2229](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2229), [cutover-negative proof #2232](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2232).  
**STATE:** Test-only. Protected production trust, Sign-In and NAS provisioning **HOLD**.

## IMPLEMENTATION // Concrete processes, bytes and data

This milestone exercises what moving a security service into a separate process actually means:

1. A disposable root-only GitHub CI test initializes an **untrusted** local SQLite history ledger under `/run/c3er-ci-...`. It creates fake keys, an untrusted test current head and a local issued challenge.
2. The test constructs the existing DOC 1 `TrustBoundary` in either **LOCAL_DEVELOPMENT_ONLY** or **INDEPENDENT_CUSTODIAN_REQUIRED** mode.
3. Linux creates an anonymous `AF_UNIX` **socket pair**. A child process is forked with one endpoint; the parent holds the other. There is **no pathname socket, listener, port or Internet connection**. The child handles **exactly one request**, sends a bounded response and exits.
4. The test-only message is a 4-byte big-endian payload length followed by at most **4096 bytes** of JSON with an exact schema, a 16-byte hexadecimal *diagnostic* request nonce and one of three read-only operations:
   - `SNAPSHOT`: read a locally rollbackable test head and sequence.
   - `OUTCOME`: read the local `issued` or `consumed` state for a specified 32-byte test challenge.
   - `CUSTODIAN_STATUS`: get the existing storage-neutral **protected custodian unavailable HOLD** result.
5. The child calls **only** the original `TrustBoundary` operations. This does not redefine C3e signed-history verification or C4b source authority. A protected-required instance never accepts a local SQLite adapter; `SNAPSHOT` and `OUTCOME` then refuse without fallback.
6. Replies are `IPC_CI_DIAGNOSTIC_ONLY` with the original test-only result and **all protected host, history, C5, credential, Sign-In and production flags false**, or `IPC_CI_REQUEST_REFUSED_NO_AUTHORITY` with those flags false. The child never sends a grant.

**No state mutation is exposed over IPC.** The test can first advance the local ledger through the existing internal signed-history fixture, then query that outcome through the child. There is no `COMMIT`, `ISSUE`, `BEGIN_SIGNIN`, `REVOKE`, `ENABLE_CREDENTIALS` or production admission operation on the socket.

This experimental JSON and framing are **not** a selected future NAS wire protocol, transport, authentication scheme, domain-owned schema or protected issuer API. They only prove that a local second process can read a diagnostic while an absent independently enrolled custodian still produces HOLD.

## HOW TO USE

There are **no workstation instructions**. The code is under `tests/connections/`, not `services/`. The test requires a disposable hosted GitHub Linux runner and runs as root solely to reuse the existing C3e-R fixture guard. Fork and `AF_UNIX` are used only during CI. No service is installed, no socket remains available to the desktop, and no NAS, private production signing key or provider credentials are accessed.

Even a real separate child process shares the parent host's administrative and backup domain. **It is not an independent trust custodian.** Environment variables such as `GITHUB_ACTIONS` are test execution guards, not remote host identity or antirollback attestation.

## VERIFY // Source and native process failure checks

The expanded 46-case CI matrix checks:
- separate forked child reads current disposable test head and issuance/consumption state without promotion;
- protected-mode status reports HOLD while protected-mode reads refuse, with no fallback to local SQLite;
- all returned authority flags remain false and there is no production admission endpoint;
- exact schema and operation, bounded frame size, no duplicate fields, no NaN, no extra fields, malformed JSON, invalid challenge hex and unknown local challenge are rejected;
- 4-byte length split across multiple writes is reassembled correctly, with a single reply followed by child socket closure, including half-closed incomplete frames and incomplete frames left open until the child read timeout;
- **strict backend-result allowlists** for each diagnostic operation: a local snapshot, local challenge outcome or protected-HOLD status can carry only its expected fields; unexpected top-level/nested grant claims, missing denial flags, type-confused counters, malformed heads, wrong mode/status/source and inconsistent challenge states are refused and replaced with a fixed deny-only reply;
- inherited 32-case migration cutover, 28-case storage boundary, 28-case SQLite ledger and 24+22+22+20 original C3e signed-history/enrollment/AF/Z test suites remain intact.

GitHub Actions must confirm the exact PR head and independent Nurse 2 reviews must assess it **before** any operator-authorized merge. The existing RPM regression runs separately and must not be confused with a real NAS service.

## WATCH OUT FOR

1. **A process boundary is not a trust boundary by itself.** Root on the same desktop can control both processes and restore the SQLite database.
2. **No authenticated transport.** A Unix socket pair proves byte parsing and process isolation *only*, not independently enrolled service identity. The test request nonce is diagnostic, not a remotely issued one-use challenge.
3. **No frozen production API.** Future custodian protocol, role-specific authentication, current history, nonce issue/commit/terminal-recovery semantics and key custody require operator selection and independent review. This probe intentionally exposes read-only operations only.
4. **No automatic local fallback.** Unavailable protected custody remains HOLD, never “local mode until the NAS comes back.”
5. **Review debt:** merged #2229 and #2232 have 4/4 automated checks each but **no independent PR reviews recorded** at this checkpoint. Explicit retrospective security reviews remain necessary; this work does not confer approval retroactively.

## CHECKLIST / NEXT

- [x] Verify current C3e ownership, merged #2229/#2232, Syntagma authority/Hospital protocols and DOC 2's separate C4b PR #2231.
- [x] Add one disposable real process IPC probe, 28 cases, GitHub workflow and code-adjacent documentation without modifying existing runtime.
- [ ] Exact-head CI and all inherited tests PASS.
- [ ] Nurse 2 independently reviews this PR and retrospective debt on #2229/#2232; operator merge decision separate.
- [ ] Later select the actual independent NAS/other computer and its administrator, out-of-band root enrollment, protected signer/history/challenge storage, authenticated transport, cross-host crash/rollback/recovery and C5/Identity integration.

## DECISIONS

The operator's **Local Development Ledger now → Independent Trust Custodian later** sequence remains accepted. This milestone merely demonstrates a **disposable local read-only service-process seam** with no production rights. It does **not** select an independent custodian or perform native service installation, credential access, trust enrollment, merge or Sign-In activation. **PRODUCTION HOLD.**
