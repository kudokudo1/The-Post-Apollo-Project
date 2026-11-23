# 🏥💜 DOC 6 // Universal Sign-In V5 deny-only native admission diagnostic

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Identity Center / Universal Sign-In V5, external Hospital-compatible  
**STAFF ROLE //** DOC 6 · Identity native client integration  
**BASE //** `8ef2b15ac719c6458e5646d13ec32e44cbf3a3dc`  
**PRODUCTION //** HOLD  
**SCOPE //** Isolated new Identity diagnostic, negative tests, scoped CI and this handoff. No C3e/C4b/C5/CPU++ code edits, no native command activation.

## IMPLEMENTATION

The already merged Identity V5 contract (`docs/identity-center-v5-native-admission-handoff-doc6.md`, PR #2227, retrospective Nurse 2 scoped design PASS) sets out independently owned protected trust and consent prerequisites. This milestone introduces a narrow read-only *inventory* of those outstanding evidence categories without claiming to verify them.

`services/identity/native_admission_diagnostic_v0.py` accepts one exact native action (BEGIN/STATUS/CANCEL/RECOVER), a bounded mapping of **untrusted boolean claims** for seven separately owned input families, and an exact boolean identifying an unknown prior command outcome. It emits an immutable status with ordered missing claim labels and **all authorization fields false**. If the caller marks the outcome uncertain, status is `UNKNOWN_HOLD`; otherwise `NOT_READY`. Even all-true claims remain `NOT_READY`: schema validity and self-reported readiness do not prove real installed-host authority.

This module imports no gateway, client, socket, signer, C5 provider, QML or persistence component. It cannot issue or approve real commands and will never become a `canBegin` capability source. The actual production adapter must obtain independently attested evidence and an approved one-use operator-intent contract; this diagnostic must stay separate.

## HOW TO USE

No user-visible controls. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains offline/read-only. Sign In/Cancel/Retry must stay disabled.

For CI-only diagnostics:

```python
from native_admission_diagnostic_v0 import inspect_evidence_claims
report = inspect_evidence_claims(action="BEGIN", claims={})
assert report.state == "NOT_READY"
assert report.can_begin_sign_in is False
```

Run the 12-case isolated negative suite only in disposable CI or a separately authorized test environment:

```sh
python3 -m unittest discover -s tests/identity -p 'test_native_admission_diagnostic_v0.py' -v
```

## VERIFY

- Exact schema/action and boolean-only input, missing gate labels, immutable deny-only result.
- All-true claims cannot enable BEGIN, CANCEL, RECOVER, provider actions or production authority.
- Unknown command outcome remains UNKNOWN_HOLD with zero safe commands even if every claim says True.
- Extra `hostAuthenticated`, `canApprove`, token and command-related fields are rejected.
- AST/static check confirms no native actuator or command-client imports.
- Separate CI reruns `test_native_adapter_only_call_path_v1.py` and CPU++ fixed-offline source checks.
- GitHub exact-head workflow, formal Nurse 2 pre-merge security review and operator disposition must be checked independently; no PASS claimed at creation.

## WATCH OUT FOR

This is a **diagnostic of untrusted claims**, not evidence validation. It must never be wired to an authorization check. In particular, the local SQLite development ledger (DOC 1), test-signed Silverblue guest (DOC 2), and fake `approved_intent` callback (C5) are not production trust. A positive diagnostic would still be insufficient, so this diagnostic deliberately has no positive result at all.

Host-issued request IDs and real signed receipt state belong in the separately owned gateway/client. An unknown prior BEGIN/CANCEL outcome cannot be inferred from this pure diagnostic and must remain unresolved until externally trusted reconciliation. It does not offer a retry/undo.

## CHECKLIST

- [x] Review current `main` and previous merged/reviewed DOC 6 PRs #2203/#2227
- [x] Preserve existing mandatory installed adapter and offline CPU++ boundary
- [x] Add isolated negative-only evidence diagnostic
- [x] Add 12 adversarial/structural tests and scoped CI
- [ ] Exact-head workflows and fixes
- [ ] Independent Nurse 2 review before merge
- [ ] Operator merge decision
- [ ] DOC 1/2/C5 independently approved protected evidence APIs and actual native acceptance

## NEXT

Review exact-head CI. If green, request Nurse 2 review and operator acceptance **before** merge. Then reconcile real independently authenticated versioned issuer, installed-host, seat and C5 interfaces in issue #1662. A real native adapter and UI command enablement remain separate future milestones.

## DECISIONS

No C3e/C4b/C5 cross-owner code, production host, local workstation, signing keys, provider credentials, live Hospital registration, PR merge or activation. The untrusted diagnostic cannot promote itself to authorization.
