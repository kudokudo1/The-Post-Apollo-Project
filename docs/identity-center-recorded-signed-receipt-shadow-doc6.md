# 🏥💜 DOC 6 // Recorded signed Identity command receipt shadow

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center / Sign-In V5  
**STAFF ROLE //** DOC 6 · external Hospital-compatible, live Hospital registration unverified  
**BASE //** `6b77f068fe8d1a980fe2541c2b007f2af26fbf53`  
**PRODUCTION SIGN-IN //** HOLD

## IMPLEMENTATION

Previous merged, retrospectively Nurse 2-reviewed DOC 6 [#2289](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2289) performs **strict semantic comparison** of one caller-provided outcome claim to an original attempted command. It intentionally does not authenticate the claimant. Prior #2275's local SQLite durable HOLD record can be erased/replayed by same-UID rollback and is unconnected to the native command sender.

This milestone adds an Identity-owned, **read-only cryptographic compatibility shadow**. `services/identity/native_recorded_signed_receipt_shadow_v0.py` reuses the existing real `signed_command_receipt_v0.verify_receipt()` Ed25519 strict decoder. The caller supplies an immutable original command binding, recorded signed frame, raw original request ID (none for BEGIN), original 43-character client nonce, and public key pin. It first checks the hash commitments to the original request and nonce, then verifies signature, exact action/request/nonce, signed host-instance digest and sequence floor. Missing/oversize/noncanonical/tampered/foreign-signature/wrong-host/stale-sequence material never becomes proof.

**Every output remains `UNKNOWN_HOLD` with `safe_actions=()` and zero Sign-In, CANCEL, RECOVER, provider, retry, enrolled-host, protected-history, original-C5-intent, terminal-recovery or production authority.** Even a valid, matching, signed `AUTHENTICATED` or `UNAVAILABLE` frame cannot prove protected current history, no side effects or user consent.

No new signature format is invented. The reuse is **only** of an existing experimental command acknowledgment format: it does not contain independent C3e current history, installed C4b process/seat evidence, C5 SPENT history or an authenticated terminal outcome-query receipt. Therefore it cannot settle a prior crashed command even if its signature checks.

This reference never calls a native host, sends requests, opens SQLite, reads credentials, creates accounts, changes QML, or auto-retries. Keys and original values are **caller-supplied** and cannot be treated as independently enrolled simply because the cryptography verifies. All CI signatures come from disposable generated test keys.

## HOW TO USE

No new desktop action. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains read-only with native Sign In / Cancel / Retry disabled.

For CI-only tests:
```sh
python3 -m unittest discover -s tests/identity -p 'test_native_recorded_signed_receipt_shadow_v0.py' -v
```

Do not use this source to recover real login or copy a real OAuth credential into a log or fixture. A recorded signed status is a host-local observation, not a protected issuer settlement or provider permission grant.

## VERIFY

Nineteen adversarial tests, including:
- Real throwaway Ed25519 fixture receipts for BEGIN, STATUS, CANCEL and RECOVER remain UNKNOWN_HOLD.
- Valid signed STATUS `AUTHENTICATED`, signed `UNAVAILABLE` and replayed original frame confer no authority.
- Wrong signing key, altered body, wrong action/request/nonce, wrong signed host instance, stale sequence and malformed original input fail closed.
- Missing/oversize frames, extra authority fields, absent pin, non-ASCII identifiers and forged `productionAuthority` cannot promote.
- Immutable no-authority output, no settlement/retry API and static source absence of socket, DB, native command client or C5 provider.

A dedicated workflow runs 19 new plus 16 outcome-candidate, 16 local rollback, 12 admission and 2 adapter-only tests, along with CPU++ offline checks. **Verify exact-head GitHub CI, independent Nurse 2 review and operator merge acceptance separately.**

## WATCH OUT FOR

**Cryptographic correctness is not trusted source custody.** A caller can supply its own Ed25519 key and self-signed frame that passes the decoder. A valid previously recorded signed `AUTHENTICATED` frame is still not a current independently protected outcome after host crash/restart. Existing receipt schema lacks issuer epoch/current history, original C5 SPENT state, independently authenticated release/process/seat and durable terminal settlement.

DOC 1 C3e, DOC 2 C4b and the as-yet-unassigned Identity-specific C5 issuer must approve their independently protected interfaces before this could become a real recovery consumer. Do not claim their dev/CI-root evidence, Silverblue boot continuity, or other C5 audience's human approval as Identity authority.

## CHECKLIST

- [x] Verify current main, previous DOC 6 merger/review and adjacent owners.
- [x] Add additive Identity-only recorded signed receipt shadow, new tests, dedicated workflow and this handoff.
- [ ] Exact-head GitHub workflow PASS and raw logs.
- [ ] Independent Nurse 2 **pre-merge** security review.
- [ ] Operator merge acceptance.
- [ ] Protected issuer original-command reconciliation / C3e current history / C4b installed host / Identity C5 signed one-use consent / native acceptance.

## NEXT

Review exact-head CI, then request Nurse 2's security review **before merge**. Reconcile the actual approved C3e/C4b/C5 versioned terminal query/receipt and custody contract with the owners before any real authenticated recovery integration. The source remains standalone until that boundary exists.

## DECISIONS

**Development-only, non-authorizing, no native action.** No production login, signer enrollment, workstation/NAS mutation, other owners' files, real credentials, QML wiring or live Hospital registration. Operator controls merge and production acceptance.
