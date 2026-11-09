# CPU++ // Universal Sign-In V2: Read-only sign-in status journey

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** CPU++ Universal Sign-In visual integration (external Hospital-compatible, live attachment unverified)  
**STAFF ROLE //** DOC-compatible external visual integration worker, no claimed registered role  
**PROVIDER //** OPEN AI // CHATGPT  
**ASSIGNMENT //** V2 host-aware, token-free status and sign-in-stage presentation inside merged upper-left layout. No credential or sign-in actuation  
**SOURCE BASE //** `4edf11f7c82c9b68098ff12345bfd2e664a2c91d`  
**PERMISSIONS //** Bounded GitHub UI, pure read-only policy, test, CI and recovery documentation. No Fedora machine modification, unapproved PR merge, Quickshell reload, live accounts, credentials, protected-host worker edits, real login or production authorization.

## IMPLEMENTATION

V1 CPU++ control PR #1614 and upper-left placement PR #1619 are **merged**; operator verified that **OPEN ID MANAGEMENT** navigates correctly. The Universal Sign-In panel sits in the unused upper-left section between `CONNECTIONS // OVERVIEW` and `SHARED // STATUS` (above the divider), preserving original three bays, saved account-name editors in both ID MANAGEMENT and CONNECTIONS, and existing Social/Telegram right-side actions.

**V2 implements an actual token-free status read, not a fake login or login progress.**

- `CpuPlusUniversalSignInHeaderPane.qml` now offers **VIEW SIGN-IN STATUS** / **HIDE SIGN-IN STATUS**, expanding a bounded scrollable detail area without relocating the header or displacing the lower Social/inventory view.
- While expanded **and** the CPU++ Connections menu is actually open, reuse the **existing IdentityCenterOrganizationDisplayReader** from ID MANAGEMENT. It launches only the existing validated `--json` private Unix-context read command and receives its already bounded/read-only schema: `READY`, `NO_MEMBERSHIPS`, `SIGNED_OUT`, `NOT_CONNECTED`, `UNAVAILABLE`. No token, user ID, external URL, login command, browser redirect or secret enters the pane.
- `ConnectionsIdentityJourneyPolicy.js` is a pure, strict-schema presentation projection; output is **fixed status descriptions only**. It strips raw identity/company/portfolio data rather than repeating identifiers. Even a `READY` context status reads **CONTEXT VIEW // DATA RETURNED (UNVERIFIED)**, never an authenticated principal or permission. Invalid/extra fields fail closed.
- Four stages remain visible: **TRUSTED SIGN-IN HOST REQUIRED → SIGN-IN NOT AVAILABLE → AUTHENTICATED IDENTITY NOT VERIFIED → PROVIDER CONNECTIONS LOCKED**. These are dependencies, not claims of executing authentication steps.
- A visually explicit, **disabled** `SIGN IN // HOST REQUIRED` ActionButton has `available: false` via the policy, no `onClicked`, no direct Python/OIDC/browser launch. **REFRESH CONTEXT VIEW** is a safe live operation that calls only the existing private display reader's `refresh()`. `VIEW SIGN-IN STATUS` expands/opens; hiding it, closing CPU++ or leaving SETTINGS → CONNECTIONS clears prior view and refuses late responses.
- `CpuPlusW.qml` binds `panelActive` to `menuOpen && selectedModeIndex === 6 && settingsSubMode === 'CONNECTIONS'`. The body stays capped to 184px for readable 390px upper-left bay. No modifications to C3e/C4b/C5 security owner files, Identity Center's reader implementation, ConnectionsBroker, Telegram adapters, Social identity writer or local sessions.

This improves genuine **read-only usability**: the operator can inspect whether the existing Identity Center display service responds from the central sign-in location rather than opening ID MANAGEMENT first. A same-UID private socket or valid display schema **does not authenticate the host**.

## HOW TO USE

After operator-authorized merge/deploy:

**CPU++ → SETTINGS → CONNECTIONS → upper-left UNIVERSAL SIGN-IN // CONTROL → VIEW SIGN-IN STATUS**

The panel expands to show Identity Center's **read-only** context state and the blocked login workflow. Use **REFRESH CONTEXT VIEW** for a fresh token-free read, or **HIDE SIGN-IN STATUS** to retract and clear the data. **SIGN IN // HOST REQUIRED** remains disabled until a separately approved, protected sign-in command path exists.

The existing **OPEN ID MANAGEMENT** button still switches directly to CPU++ → ID MANAGEMENT → IDS. The adjacent **INSPECT LOCAL HOST** checks the unrelated Connections status socket and stays clearly unverified. The lower-left section remains Social/inventory; select providers in the middle and inspect existing details in the right bay. Telegram OPEN TELEGRAM and RECHECK SESSION are preserved.

## VERIFY

`tests/cpuplus/test_cpuplus_universal_signin_journey_v2.cjs` covers closed/inactive view, null/malformed/extra-data snapshots, forbidden token/secret/host flags, every Identity Center display state, `READY` never meaning authentication, no raw organization/portfolio names in output, all sign-in/provider action gates false, lifecycle-active guard, capped scroll geometry, existing original reader reuse, unchanged account editor and Telegram routes.

Existing `tests/cpuplus/test_cpuplus_universal_signin_control_center.cjs` continues to enforce upper-left placement above divider and permanent default-deny. Workflow `.github/workflows/cpuplus-universal-signin-visual-v1.yml` now runs both tests, previous Connections C1/C2a, Telegram, account-editing/ID-context regressions, Qt QML parser and other triggered GitHub suites.

**Exact-head CI and actual desktop acceptance are separate gates; never infer them from a committed change.**

## WATCH OUT FOR

The existing IdentityCenterOrganizationDisplayReader uses the experimental same-UID AF_UNIX private display channel, not independently signed, installed host identity or a login command transport. Even when it returns `READY`, the display alone does NOT prove an authenticated current user, authorize organization switching, or grant access to any provider. The existing CLI's status `SIGNED_OUT` is also a read-only report and can be spoofed in an untrusted same-user runtime; hence all visible statuses say **context view** rather than authenticated sign-in.

C3e-O/P signed package and runtime-script measurements remain CI-only. C4b guest installed-host + protected independent witness integration issue #1606 remains separate, as does C2v rollback and C5 independent human consent. A true future sign-in requires an independently trusted and approved Identity Center host identity, pinned issuer configuration, validated user-consent intent, protected credential/token custody, session lifecycle and operator acceptance. Do not move PKCE, browser redirect or token storage into Quickshell/QML.

After merge, verify native window height, scrollability and text/button readability at actual display scaling; the detailed journey is intentionally limited to a scroll area so it does not crowd SHARED STATUS or other modes. Never treat local Social identities as verified organizations.

## CHECKLIST

- [x] Reverify V1/V1b merged and Syntagma/Hospital rules and live main status
- [x] Reuse existing token-free Identity Center display reader without modifying its owner
- [x] Add collapsible status and four fixed fail-closed host/auth/provider stages in upper-left
- [x] Add visible disabled sign-in placeholder, explicit read-only context refresh, no auth process
- [x] Clear host view on hide, menu close, or mode change; bound detailed height
- [x] Add malicious/extra-field/secret/READY denial tests and scoped CI
- [ ] Exact-head GitHub CI pass, fix failures
- [ ] Operator PR review/merge and native Fedora/Quickshell visual acceptance
- [ ] Identity owner independently approves a protected token-free sign-in **command**/status contract and installed runtime
- [ ] V3 guarded explicit Sign In command and real pending/callback/result view, with authentication proof and host ownership
- [ ] Per-provider grants, reconnect/disconnect and Connect All only after Credentials/C5 real host approval

## NEXT

**V3 // Owner-approved native Sign In intent**: define a narrow authenticated Identity Center host `requestSignIn` operation and status subscription/receipt, separate from the existing read-only context socket. The responsible Identity Center/Connections security owners must approve host identity, sender/operator authorization, OIDC issuer/client policy, one-use browser handoff and token custody. Only then enable the existing placeholder button and replace fixed blocked steps with host-owned progress/error states. Avoid adding another uncontrolled OAuth launcher, client-supplied `authenticated: true` QML flag or duplicate credential store.

## DECISIONS

Keep Universal Sign-In in the existing upper-left area, with status detail retracted by default. Retain working OPEN ID MANAGEMENT route, original Social label editors in both locations, existing Telegram controls and independent protected-host worker ownership. No real sign-in, file writes, credential values, native installer, local Quickshell restart, PR merge, production grant, live Hospital registration or final operator acceptance was performed. Recovery pointer: this file plus V2 policy/QML/CI/test on review PR.
