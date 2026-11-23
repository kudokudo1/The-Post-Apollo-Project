# 🏥💜 DOC 6 // Original-attempt dual read-only recovery join

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center V5 native recovery  
**STAFF ROLE //** DOC 6, external Hospital-compatible; live Hospital connection unverified  
**PRODUCTION SIGN-IN //** HOLD

## IMPLEMENTATION

Previous merged DOC 6 milestones:
- [#2364](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2364): native signed client exposes a **process-local** digest-only `AttemptedWireFingerprint` just before `sendall`, preserved through an ambiguous error.
- [#2289](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2289): inspect **one caller-controlled, untrusted** custodian-style outcome candidate and always return `UNKNOWN_HOLD`.
- [#2349](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2349): verify a **recorded** Ed25519 native command receipt with the original request, nonce, signed host instance and sequence; a valid old signature is never protected terminal settlement.

This additive DOC 6-only milestone implements a **read-only join of those three existing components** in `services/identity/native_original_attempt_recovery_join_v0.py`. The caller supplies the original attempt fingerprint, immutable original action/nonce/request digest binding, the raw original command request ID and client nonce, one optional outcome candidate provider, and an optional recorded signed receipt plus caller-provided public key.

1. First validate the original action and digest bindings. Rebuild the **exact newline-terminated signed-client request bytes** using the **existing** `build_request()` parser/serializer. Require SHA-256 equality to the original attempted wire frame. Inconsistent, absent, foreign type, malformed, or mismatched original material returns `UNKNOWN_HOLD` **before** invoking the candidate provider or attempting to verify a signed receipt.
2. If and only if that local frame correlation matches, inspect at most **one** untrusted outcome candidate using the existing DOC 6 `inspect_candidate_once()` and separately verify the existing recorded native receipt using `inspect_recorded_signed_receipt()`. No fallback source or retry.
3. Distinguish candidate conflict, signed host/sequence conflict, apparently matching diagnostic claims, and unavailable/incomplete data. **All** outputs remain `UNKNOWN_HOLD` and `safe_actions=()`, with every Sign-In, Cancel, Recover, credential, original-host, current-history, enrolled issuer, human one-use consent, terminal-settlement, and production authority bit FALSE.

A matching candidate + signed acknowledgment is not trusted original issuer history. The schema `post-apollo.identity.original-attempt-recovery-readonly-v0` is a *local diagnostic output*, not a frozen C3e/C4b/C5 producer wire format. The output is a frozen class and exposes no raw command request ID, challenge, token, receipt, or provider content.

**No native Sign-In transaction is invoked**, no socket or independent custodian query is created by this module, and it is NOT connected to CPU++, `installed_command_adapter_v1`, or a production sign-in service. The candidate source is an injected test-only Python callback. The recorded receipt pin is caller-supplied; its cryptographic correctness is not independent enrollment.

## HOW TO USE

No Post-Apollo UI action exists for this CI-only test harness. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains read-only and cannot begin, cancel or retry Sign-In.

```sh
python3 -m unittest discover -s tests/identity -p 'test_native_original_attempt_recovery_join_v0.py' -v
```

No machine changes or live provider accounts are required. The workflow runs in disposable GitHub CI.

## VERIFY

The 25-case adversarial suite includes:
- Valid throwaway Ed25519 original BEGIN/STATUS/CANCEL/RECOVER receipts and a structurally matching candidate, all permanently `UNKNOWN_HOLD`.
- Actual signed `AUTHENTICATED` and `UNAVAILABLE` host reports never becoming a credential grant or proof of no effect.
- Missing original fingerprint, wrong action/digest, altered frame hash, raw request ID/nonce drift, bad input type/case and invalid request bytes preventing any candidate lookup.
- Matching original with absent provider or absent signed receipt, a throwing provider and one lookup without retries.
- Mismatched history head, forged positive authority fields, wrong signing key, wrong signed host instance, stale signed sequence and replayed identical signed bytes staying HOLD.
- Frozen no-authority output with no raw client challenge, request ID, frame or settle API; source static checks for no network, storage or actuator code.

The dedicated exact-head CI also reruns 16 untrusted candidate cases, 19 recorded signed-receipt cases, 16 local durable-HOLD cases, 54 native signed-client cases and the CPU++ fixed-offline checks. Verify GitHub workflow outcomes and raw logs before reporting PASS.

## WATCH OUT FOR

This **does not implement independent protected reconciliation**. It only confirms that **caller-supplied** original command bytes and two caller-supplied diagnostic claims are mutually compatible *under their own local assumptions*. A compromised process can fabricate original data, duplicate a signed receipt, provide a test key, replay a local SQLite backup and invent a matching history head. Host process identity can differ from the sender on an inherited AF_UNIX stream; even separately correct packet and signature evidence do not automatically authenticate an enrolled C4b original gateway.

DOC 1 [#2369](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2369) signs correct local custodian candidates but is not a separately enrolled, independently authoritative antirollback history service. DOC 2 [#2366](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2366) observes real Linux packet senders and valid signed denials but cannot establish installed enrolled original-gateway origin. Identity-specific C5 trusted **one-use human intent / spent history** and protected terminal command receipt still have no accepted production interface.

The exact original fingerprint is **process-local** and does not survive host crash or reboot. Neither the original candidate nor the recorded signed acknowledgment is a substitute for independently current custody. Never treat this comparator as proof to retry a BEGIN/CANCEL/RECOVER or to sign in.

## CHECKLIST

- [x] Check latest Syntagma/Hospital policy, shared GitHub main, native Identity adapter/client, and nearby DOC 1 / DOC 2 / C5 ownership
- [x] Add bounded original-attempt ↔ candidate ↔ signed-receipt diagnostic join
- [x] Add 25 focused hostile tests and dedicated CI
- [ ] Verify exact-head GitHub CI and raw tests
- [ ] Independent Nurse 2 **pre-merge** review
- [ ] Operator merge decision
- [ ] Protected C3e original issuer, independently installed C4b gateway/seat enrollment, Identity-specific C5 one-use human intent and native terminal settlement

## NEXT

After exact-head CI passes, ask Nurse 2 to examine whether candidate lookup is **never** invoked for any invalid original frame; whether caller-supplied credentials are leaked; whether two apparently matching untrusted sources ever alter authorization; and whether the joined result remains strictly nonactuating.

Future **real** recovery integration requires the original issuer/gateway/C5 owners to agree on independent enrollment, original operation identity, current protected head, one-use SPENT, authentic terminal receipt and rollback/revocation semantics before any privileged read-only query or send is wired. This PR does not freeze those APIs.

## DECISIONS

GitHub-only additive DOC 6 development; no other owner's implementation modified. No local workstation/NAS changes, real credentials, live Hospital registration, Sign-In activation, root/key enrollment, protected signer, or automatic merge. **Production remains HOLD.**
