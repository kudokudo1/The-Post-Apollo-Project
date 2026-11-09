# 🏥💜 CPU++ Universal Sign-In V5 // Owner-review-only command envelope

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Sign-In CPU++ visual integration, existing external Hospital-compatible work  
**DOCTOR //** OpenAI ChatGPT contributor · no verified live Hospital attachment  
**PROVIDER //** OPEN AI // CHATGPT  
**STAFF ROLE //** DOC-compatible UI/integration worker, not the protected host/C3e/C4b/C5 owner  
**ASSIGNMENT //** Define bounded, non-executable host command-envelope candidate and an owner acceptance handoff; keep V4 authenticating controls disabled  
**BASE //** `9fc6a588a9ea6d2d4057a37d93f1b2f19f36f861`  
**PERMISSIONS //** Bounded GitHub pure candidate, tests, CI and docs only. No local machine, auth host, production provider, credential store, security worker files, merge or activation.

## IMPLEMENTATION

V4 #1660 is merged, and the user has previously confirmed working desktop navigation and expansion (V3 screenshots). The next milestone must **not** be another synthetic fake sign-in. Instead, V5 makes the missing handoff explicit in [cross-Room issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662), addressed to the Identity Center protected-host owner with separate C3e/C4b/C5 acceptance gates.

Source `services/connections/ConnectionsSignInIntentProposal.js` is a pure, **untrusted command-shape review candidate only**. It does not create a client, transport, authenticator, browser launcher or subscriber. It proposes exact minimal UI intent keys:

```json
{"schema":"post-apollo.identity.command-intent.proposed-v0","action":"BEGIN","requestId":null}
```

For `CANCEL` and `RECOVER`, a request ID could be supplied *only if it was minted by a verified host*. The candidate validator only checks an opaque 16–96 byte ASCII identifier shape; this is NOT possession or ownership proof. The final Identity owner is responsible for deciding if `RECOVER` should refer to the old terminal request or use a different protocol. The host must always mint the **new** request ID, never trust one invented by CPU++.

The candidate **never returns a sendable command**. `review(candidate)` produces `shape: CANDIDATE_ONLY` or `REJECTED`, but `authority: NONE`, `hostAuthenticated: false`, `operatorConsentVerified: false`, `canDispatch: false`, `canBeginSignIn: false`, `canCancel: false`, `canRecover: false`, `canConnectProvider: false` in all cases. It does not echo identifiers, redirect URLs or secrets. Unrelated actions, extra input keys and credential material are rejected.

**No new user-facing controls or UI state** in this PR. The existing V4 upper-left panel still uses `HostBoundary.offline()` and the V3 synthetic flow contract remains test-only. This avoids duplicating the system or inventing another untrusted Identity Center.

## HOW TO USE

**For the Identity Center/C3e/C4b/C5 owners:** review [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662) and this candidate grammar; approve, revise or replace it with a versioned, owner-authored command/status interface. Determine operating-system command transport, independently attested sender and host identity, actual user gesture/seat proof, C5 consent semantics, encrypted protected token custody, cancellation acknowledgment, fresh recovery request, timeout and state invalidation. Provide source and exact integration acceptance tests before UI worker connects anything.

**For the operator:** no new action is required. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS continues to function as V4 read-only diagnostics. SIGN IN/CANCEL/RETRY remain disabled, as intended.

## VERIFY

`tests/cpuplus/test_cpuplus_universal_signin_intent_v5.cjs` runs 35+ positive-shape/negative-admission fixtures: BEGIN must have `requestId: null`; CANCEL/RECOVER require a non-empty opaque request ID shape; malformed/missing/extra keys, injected tokens, issuer URLs, spoofed `hostAuthenticated` or consent fields, provider-level actions and path-shaped identifiers fail. **Every** structurally valid candidate still has `canDispatch: false`, `authority: NONE` and no signed-in account status. Source and UI tests reject an added Process/FileView/HTTP/OAuth call, and check V4/V3 status still read-only. CI uses the established CPU++ V1–V4 workflow, all regression tests and Qt parser.

**This is contract/test readiness, not a real host handshake or authenticated sign-in test.** CI green cannot qualify production activation.

## WATCH OUT FOR

C4b/C4c's signed Silverblue guest verification and merged C3e-T/U work do not authenticate a real production Identity Center command channel. C4d PR #1657 remains draft and is exporting CI guest observation; its artifact is not remotely signed host identity or C5 human consent. Current `ConnectionsRequestStatus.hostAuthenticated`, `canApprove` and `ConnectionsBroker.credentialActionsEnabled` remain false. The existing V2 same-UID private context read socket cannot be upgraded into a command transport by adding a JSON string. The V3 `simulate()` never authorizes a real user.

Do not conflate **valid command shape** with **trusted sender identity**, **user approval**, **host authentication**, **ID-token verification**, **server-enforced organization permissions**, or **provider-specific consent**. Those are distinct protected checks.

## CHECKLIST

- [x] Recover merged V4 state, Syntagma/Hospital permissions, current C4d/Identity/C5 ownership
- [x] Create cross-Room integration/acceptance issue #1662 with no ownership transfer
- [x] Implement strict minimal proposed command shape, permanently non-dispatchable
- [x] Add adversarial deny-only command-envelope regression and CI
- [ ] Exact-head CI review and any test repair
- [ ] Independent Identity Center owner approval/revision of schema and protected command/status transport
- [ ] C3e/C4b independently attested actual service, C5 authenticated operator consent, secure token custody
- [ ] Operator-approved real installed host, actual human login, native desktop test, provider connection authorization
- [ ] Operator final acceptance

## NEXT

**The next real implementation is owner-delivered protected BEGIN/CANCEL/RECOVER transport**, with host-issued, authenticated receipts for the already existing V3 progress schema. Once identity/C3e/C4b/C5 owners approve its actual protocol, the visual integration room can bind the current disabled UI to a *separately protected out-of-QML adapter* and independently verify action origin, one-shot capabilities, denial/replay/host-loss behavior and no token leakage. Do not implement a second Python OIDC host or bypass the existing read-only socket while waiting.

## DECISIONS

This is a **review candidate, not a canonical wire API or an approved authentication implementation**. UI lane remains owner of presentation, tests and handoff only. No code changes to security owners, no role change, no live Hospital registration, no credentials, no local workstation mutation, no merge or production activation. Final acceptance rests with operator.

**Recovery:** this file, [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662), and V4 [PR #1660](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1660).
