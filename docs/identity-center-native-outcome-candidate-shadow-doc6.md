# 🏥💜 DOC 6 // Identity V5 one-query native outcome candidate shadow

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center / Sign-In V5  
**STAFF ROLE //** DOC 6 · external Hospital-compatible, not verified live Hospital  
**BASE //** `6f4276fab3aaf9512565b3020fd6b7ebad2002c4`  
**PRODUCTION //** HOLD

## IMPLEMENTATION

Previous merged/reviewed DOC 6 milestones [#2246](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2246) and [#2275](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2275) classify lost signed-command responses and demonstrate a **local, rollback-vulnerable** SQLite `UNKNOWN_HOLD` reference. Neither can authenticate an original host effect after a restart. This change adds a **separate non-authorizing candidate consumer** that does not silently adopt a DOC 1/2/C5 protected wire protocol that has not been approved.

`services/identity/native_outcome_candidate_shadow_v0.py` defines an immutable original command identity containing the attempt, exact action, host-issued request digest (not applicable to initial BEGIN), client nonce digest, host-instance, seat, session, challenge, history-head digests, issuer epoch and sequence floor. Every field is **caller-supplied and untrusted**; the datatype is not an attestation.

`inspect_candidate_once(original, provider)` issues **at most one callback** to the supplied source and performs an exact, bounded, strict-type semantic comparison of its untrusted outcome candidate. It refuses malformed, foreign-purpose, wrong-attempt, wrong-action, wrong-request/nonce/host/seat/session/challenge/history, wrong-epoch and stale-sequence claims. Even a structurally exact claim of `CLAIMED_NO_EFFECT`, `CLAIMED_COMMITTED` or `CLAIMED_ABORTED` returns `UNKNOWN_HOLD`. A claimed no-effect terminal event **cannot authorize a second BEGIN/CANCEL**.

The output has `state=UNKNOWN_HOLD`, `safe_actions=()`, and false for **all** retry, native Sign-In, cancel, recovery, provider, original host, operator consent, issuer settlement, protected receipt and production authority fields. Absent/unavailable source returns the same denial. No second provider or local SQLite fallback is permitted.

This is a **CI-only comparison** of adversarial fixtures. The provider is an injected Python callback, not an authenticated external custodian or installed native service. No signature is verified. No receipt, consent, signature key, protected history or host origin is created. The schema `post-apollo.identity.outcome-candidate.untrusted-v0` is deliberately NOT a frozen production wire format. The real protected issuer/host/seat/one-use C5 interface requires independent owner approval before native integration.

This source is separate from the signed command client and mandatory installed adapter; there is no command, socket, OAuth, database, provider or QML import. It cannot clear the existing local `UNKNOWN_HOLD` record or grant any retry.

## HOW TO USE

**No new desktop action.** CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains read-only; real Sign In, Cancel and Retry controls remain disabled. The negative-only shadow is exercised through disposable GitHub-hosted CI:

```sh
python3 -m unittest discover -s tests/identity -p 'test_native_outcome_candidate_shadow_v0.py' -v
```

Do not use a caller-generated matching claim as a production reconciliation receipt. This code neither knows nor proves which physical process authored the candidate.

## VERIFY

New isolated workflow checks:
- Missing or failing source results in UNKNOWN_HOLD after at most one callback, with no fallback.
- Even exact claimed NO_EFFECT, COMMITTED, ABORTED and UNKNOWN outcomes remain non-authorizing.
- Each of BEGIN/STATUS/CANCEL/RECOVER is bound to the original host request/nonce and session; cross-operation and cross-seat/session/host/epoch/history claims conflict.
- Stale sequence, wrong issuer epoch, malformed digests, authority-injection extras, wrong-purpose/duplicate/missing fields cannot become terminal settlement.
- Immutable results expose no success, retry, settlement or native command API, and do not import runtime actuators.
- Existing #2275 SQLite HOLD, #2236 admission diagnostic, mandatory native installed-adapter caller-path and CPU++ fixed-offline contracts are rerun.

All tests use synthetic caller-controlled candidate dictionaries. They do **not** exercise actual C3e custody, C4b installed host evidence, operator consent or external signed current history. Verify actual GitHub exact-head workflow results, independent Nurse 2 **pre-merge** review and operator merge acceptance separately.

## WATCH OUT FOR

**Do not confuse binding comparison with issuer authentication.** An attacker who controls both the expected command description and candidate claim can make all fields match. Even a valid cryptographic signature from a test-local key would not establish the independently enrolled original host or a protected current history.

DOC 1's newest [#2282](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2282) exercises local writer SIGKILL and rollback, still not a trusted production custodian. DOC 2's draft [#2283](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2283) proposes CI-only challenge encoding and a **signed denial**, not a signed protected command terminal receipt. Forest/Hospital/TimeW C5 lanes remain distinct; no Identity-specific C5 operator intent issuer has been accepted. Do not change `ConnectionsSignInHostBoundary.offline()`.

An external producer that claims a terminal event must eventually bind: independently enrolled source key and current release/process/seat, original client nonce and command, one-use issuer challenge/spend/revocation sequence, independently current history head, and authentic terminal receipt/outcome. That producer contract is **not implemented here**. Even if it is later supplied, additional independent security review and operator acceptance are required before any live command enablement.

## CHECKLIST

- [x] Recheck current main / #2275 retrospective Nurse 2 review / separate DOC 1 and DOC 2 ownership.
- [x] Create isolated DOC 6 pure one-lookup negative comparison and strict action/claim schema.
- [x] Add 16 focused hostile/structural test cases, dedicated CI and recovery document.
- [ ] Verify exact-head CI, repair any source/test failure.
- [ ] Independent Nurse 2 **pre-merge** review and operator merge disposition.
- [ ] DOC 1 protected external custodian and DOC 2 authenticated installed original gateway receipt contract.
- [ ] Explicit Identity-specific C5 per-command consent ownership and native crash/rollback acceptance.

## NEXT

Review the exact GitHub source head and CI. Request Nurse 2's scoped source/CI security audit **before** any merge. Coordinate the protected issuer/host/seat/C5 interface in [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662), preserving the difference between simulated local denial and independently authenticated terminal resolution.

## DECISIONS

This is a **development-only, deny-only candidate semantic shadow**, not authority, a new production schema, or permission to change another worker's contract. No local Fedora/NAS writes, production key, installed service, credentials, real browser login, native bridge, independent Hospital registration or automatic PR merge. Operator retains final approval.
