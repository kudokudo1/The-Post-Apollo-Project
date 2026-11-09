# CPU++ Universal Sign-In V4 // Legible control and protected-host interface boundary

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** CPU++ Universal Sign-In visual integration (external Hospital-compatible)  
**DOCTOR //** OpenAI ChatGPT contributor, no live Hospital registration verified  
**PROVIDER //** OPEN AI // CHATGPT  
**STAFF ROLE //** DOC-compatible *UI integration* contributor, not reassigned to C3e/C4b/C5 security ownership  
**ASSIGNMENT //** Improve actual visible upper-left Universal Sign-In UX after operator screenshot, and provide the V4 protected host integration gate without activating authentication  
**SOURCE BASE //** `0e932712e39d2c081a8641bae92a79792307c3ec`  
**PERMISSIONS //** Bounded GitHub CPU++ presentation, pure offline projection, existing UI regression, CI and documentation. No workstation write, merge, production service activation, key custody, independent release or provider action.

## IMPLEMENTATION

V1 #1614, V1b #1619, V2 #1623 and V3 #1650 are **merged**, and the operator's Nov 9 Fedora screenshots visibly demonstrate the reserved upper-left pane and expandable V3 Sign-In Status / Request Flow. Native screenshots also show severe small-text density with repeated warnings at 9px and the protected V3 flow nested inside a 184px scroller.

**V4 first treats the actual usability problem**:
- In `widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml`, retain the original upper-left location above SHARED // STATUS, 390px left-bay width, ID MANAGEMENT button and INSPECT LOCAL HOST. Increase readable title/status/diagnostic fonts to 11–13px and buttons to 10–11px.
- Default visible upper block is shorter: title, exact current host-unverified status, `SIGN IN LOCKED // TRUSTED HOST REQUIRED` and the two existing working controls. The old duplicate `Connections status / provider unavailable / batch unavailable` footnotes move **inside VIEW SIGN-IN STATUS** alongside technical diagnostics, not permanently underneath it.
- The expanded V2/V3 read-only status detail remains bounded/scrollable, now 204px high with larger text. It includes the same V2 context status and V3 proposed lifecycle, in a single details viewport rather than making the default overview a wall of security text. The technical Identity host note likewise moves inside the expandable section.
- New pure `ConnectionsSignInHostBoundary.js` returns **only offline states**: `HOST // NOT ENROLLED`, `SIGN-IN CHANNEL // NOT CONNECTED`, `CONSENT // NOT VERIFIED`. Every action flag remains permanently false, with no input that could falsely enable a login. The expanded panel presents these explicitly as **TRUST BOUNDARIES // ALL LOCKED**.
- V2 private context refresh, V3 request-flow explanation, disabled SIGN IN/CANCEL/RETRY buttons, original account-name editors (in ID MANAGEMENT and CONNECTIONS), Telegram OPEN/RECHECK, and middle/right Connections bays are preserved.

## HOW TO USE

After operator-reviewed merge/deployment:
**CPU++ → SETTINGS → CONNECTIONS**. Above SHARED // STATUS the title, unverified host state, locked sign-in status and two original controls are easier to read. Use **OPEN ID MANAGEMENT** to navigate to ID MANAGEMENT → IDS, **INSPECT LOCAL HOST** to do the original read-only Connections check.

Select **VIEW SIGN-IN STATUS** for the expanded scrollable technical section. It shows read-only Identity Center context, installed host/command/consent missing prerequisites, disabled Sign In, and **VIEW REQUEST FLOW** with synthetic contract steps and disabled Cancel/Retry. **REFRESH CONTEXT VIEW** remains the only reader refresh. Hide/collapse, close or leave Connections to clear the old view. Nothing here initiates authentication.

## V4 protected-host command handoff // proposed only, NOT authorized to enable

The user asked us to make Universal Sign-In genuinely usable; we must avoid connecting the existing read-only Context viewer or local Connections status socket to a privileged command. They are **not trusted authentication channels**. C4b/C4c signed guest and C3e process measurements prove scoped signed host execution in an isolated disposable test but do **not** enroll a production Identity Center sign-in agent or authenticate operator consent. C4d #1657 is a separate-owner draft to export real guest observation; it does not grant sign-in commands.

**Owner-delivered trust prerequisites for integration**:
1. **Identity Center owner** defines an independently installed, locked-down host service, pinned approved OIDC issuer/client and per-session seat ownership. The service, not CPU++ QML, owns browser PKCE callback, tokens and secure key storage.
2. **C3e/C4b owners** complete independently verifiable package → actual installed executable/script → same PID/start tick/systemd D-Bus/SELinux identity and protected-witness binding, and approve what production host can actually attest. The current C4d guest export is *evidence*, not credential admission.
3. **C5 owner** defines verifiable operator intent, consent approval/denial, one-use scope and provider-specific grants, with an independently authenticated sender/channel.
4. **Interface owner** establishes authenticated command and status transports with source binding and request IDs. Proposed commands are `BEGIN`, `CANCEL`, `RECOVER`. `BEGIN` is only from a direct operator click on a host-issued capability; `CANCEL` must be acknowledged by the same request owner; `RECOVER` must require a fresh host-issued request and not reuse terminal IDs. A signed/enrolled host could expose a bounded token-free UI receipt using V3's phase grammar; schema validity **without authenticated origin** is never adequate to enable a button.
5. **CPU++ integration worker** independently verifies trusted enrollment, explicit host-authorized action capability and current active desktop seat before allowing controls to emit any command, and treats host loss/revocation/timeouts as deny/revoke. No secrets, tokens, URLs or login actor are added to QML.

These are proposed responsibilities and acceptance gates, *not* unilateral approval of an implementation contract. Until all are met, `ConnectionsSignInHostBoundary.offline()` must be used unconditionally.

## VERIFY

`tests/cpuplus/test_cpuplus_universal_signin_host_boundary_v4.cjs` verifies all host/action flags permanently false, exactly fixed offline status, no auth/credential processes or methods in QML, token-free existing reader remains, readability and layout refactor keeps diagnostic detail inside expanded viewport, original buttons and read-only refresh remain, upper-left anchoring still above SHARED // STATUS.

Existing V2 test's capped viewport geometry expectation moves from 184 to 204 pixels. The dedicated workflow now runs V1/V2/V3/V4 suites, original C1/C2a broker denial, Telegram, Social editor, ID context and Qt6 QML parser. GitHub exact-head and actual Fedora visual acceptance remain separate gates; do not label the source CSS/QML font change as operator-accepted until verified on desktop.

## WATCH OUT FOR

- The original protected-host gate still has `ConnectionsRequestStatus.hostAuthenticated === false`, `canApprove === false` and `ConnectionsBroker.credentialActionsEnabled === false` at inspected base. Do not copy an unrelated C3e process observer's `PASS` into any of these booleans.
- The `VIEW SIGN-IN STATUS` reader remains unauthenticated private same-UID AF_UNIX display, so its `READY` means **context display**, not an authenticated principal.
- Existing DOC/C4b/C5 workers own their files. No host service was installed, no remote provider login run, and no temporary OAuth or keyring bypass was created.
- Larger text means more scroll in expanded detail. Keep height bounded to preserve the lower SHARED STATUS and Social inventory; operator visual review on actual screen remains required.

## CHECKLIST

- [x] Recheck current `main` and canonical Syntagma/Hospital permissions, C4d ownership and `ConnectionsRequestStatus` deny values
- [x] Refactor top-level visual hierarchy and technical details into expanded status
- [x] Increase text/action readability in the operator-observed narrow upper-left bay
- [x] Add fixed offline protected-host boundary; no fake host adapters
- [x] Add V4 deny/UX contracts and update V2 viewport test/CI
- [ ] GitHub exact-head CI, Qt parser and native regression
- [ ] Operator merge/deploy and **actual Fedora visual acceptance**
- [ ] Identity owner approves authenticated `BEGIN / CANCEL / RECOVER` native host command/status interface
- [ ] C4d installed same-host evidence and C5 real consent acceptance
- [ ] Implement separately authorized true command bridge, user sign-in and provider-specific connection flows

## NEXT

**Owner-approved protected host command transport first**, then a bounded out-of-process authenticated adapter that can issue the V3 `BEGIN / CANCEL / RECOVER` requests, receive verified host-owned progress and convert to UI state without exposing credentials, tokens or authorization capabilities to QML. The adapter and consent integration must be independently reviewed before this fixed offline status is replaced. In parallel, operator visually verifies readability and the position of the SHARED STATUS divider.

## DECISIONS

Implement the readability/workflow preparation *now* while C3e/C4b/C5 continue their distinct protected-host assignment. Keep the existing three-bay layout, ID button, Social account editor and Telegram action owners unchanged. No local workstation modification, production or credential action, live Hospital staffing claim, automatic merge or operator final acceptance.

**RECOVERY //** `docs/cpuplus-universal-signin-host-boundary-v4.md`, V4 branch and PR, existing merged V3 checkpoint #1650.
