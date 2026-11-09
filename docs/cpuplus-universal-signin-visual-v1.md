# CPU++ Universal Sign-In // Visual Control Center V1

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // CPU++ Universal Sign-In visual integration (external Hospital-compatible, no verified live registration)  
ASSIGNMENT // Deliver an immediately navigable, honest single Connections entrypoint that integrates existing owners without enabling untrusted authentication  
STAFF ROLE // External DOC-compatible visual integration worker; assignment-specific Hospital registration not verified  
PROVIDER // OPEN AI // CHATGPT  
BASE // `a7d9a85f11778895cdd2d254d11db4ab6576a131`  
PERMISSIONS // Bounded GitHub UI/pure policy/test/docs/CI implementation only. No local desktop modification, host installation, live credential/auth provider, source writer, active worker-owned C3e/C4b/C5 changes, merge or production activation.

## IMPLEMENTATION

Operator explicitly authorized implementing **the visual portion and integration of Universal Sign-In now**, without waiting for protected Connections services to be complete. This milestone uses the current real CPU++ SETTINGS → CONNECTIONS three-bay surface, not a fourth menu or independent login overlay.

The left overview now has **UNIVERSAL SIGN-IN // CONTROL**, alongside the existing Social metadata and service inventory. It clearly distinguishes:
- **Identity Center owner:** No verified CPU++ sign-in host binding exists. Current entry is the working **OPEN ID MANAGEMENT** button, routed through the existing CPU++ mode selector; users can expand its existing **CHECK HOST CONTEXT** read-only organization view there.
- **Connections host owner:** **INSPECT LOCAL HOST** calls the existing local host inspection function, with its explicit unverified status. This does not use a new Process, server, socket, inspector or authority flag.
- **Provider actions:** **CONNECT / RECONNECT / DISCONNECT // UNAVAILABLE** and **CONNECT ALL // UNAVAILABLE** remain visible but unarmed while the actual protected host, operator consent and provider session ownership are incomplete.

A pure `ConnectionsUnifiedSignInPolicy.js` protects the visual projection. It accepts only exact boolean flags. Even when malicious test fixtures provide *every* success flag, all actual action flags stay permanently false in this V1 UI. The rendered CPU++ overview deliberately sets the Identity Center host evidence to false because there is **no approved live host binding** yet, and reads Connections flags only from existing `ConnectionsRequestStatus`, `ConnectionsBroker` and `ConnectionsHostObservation`. No fake sign-in, credential or account state is created.

`CpuPlusSettingsConnectionsOverviewPane.qml` adds the view in the existing left bay with ActionButton semantics and existing color palette, while `widgets/CpuPlusW.qml` binds only the **OPEN ID MANAGEMENT** navigation to `selectMode(5)` + `selectLocalManagementSection("IDS")`, without switching the underlying Social identity.

The middle service selector and existing right details pane remain unchanged: Telegram's operator-verified OPEN TELEGRAM route, safe RECHECK SESSION, saved Social account-name editor and existing provider setup are preserved. Both ID MANAGEMENT and CONNECTIONS continue to use the one original Social store for local account-name editing.

## HOW TO USE

After authorized merge and desktop update:

**CPU++ → SETTINGS → CONNECTIONS → left UNIVERSAL SIGN-IN // CONTROL.**

- **OPEN ID MANAGEMENT** switches CPU++ to its existing ID MANAGEMENT screen; use **CHECK HOST CONTEXT** to inspect the currently available read-only host-owned organization display. This does not start a login or authorize company switching.
- **INSPECT LOCAL HOST** checks the existing optional local status socket and renders **OBSERVED // NOT AUTHENTICATED** if it responds, or the existing offline/unsafe/unavailable state. No provider credentials are read or shared.
- Choose an existing provider in the **middle** list to inspect its existing **right** details pane, including the operator-confirmed Telegram route.
- The unavailable Connect/Disconnect/Connect All statuses are intentional; no misleading working-looking buttons have been added.

## VERIFY

`tests/cpuplus/test_cpuplus_universal_signin_control_center.cjs` checks strict input handling, missing/faked state, permanently disabled auth actions, no exposed secrets, existing owner reads, actual CPU++ ID navigation, original Telegram and account editor preserved, and no new files/processes or provider mutations. The dedicated CI reruns the actual C1 Connections list, C2a broker deny-only, Telegram status/navigation, CPU++ verified Identity pane, layout contracts, account-name editing and QML parser.

GitHub exact-head CI pending; native Fedora/Quickshell visual acceptance not performed. A passing visual contract would not establish a working host login or production permission grant.

## WATCH OUT FOR

Upstream C3e-O #1605 and C3e-P #1610 are merged and independently audited **within CI-only scope**. The signed installed C4b Python host, independent root witness and actual running same-process evidence are not yet cryptographically bound. Cross-Room handoff: [issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606). C2v rollback remains separately owned, and C5 synthetic consent is not authenticated user approval. No edits were made to any security worker-owned files or to their host/CI.

This first UI is **useful for navigation and truthful readiness inspection now**, not usable for logging in. A green status for a local socket, stale `READY` provider observation, saved account label, Keycloak CI success, or signed RPM in disposable guest must never enable Connect or override operator consent.

A single Post-Apollo identity login cannot silently sign into unrelated external providers. Future provider Connect will still require explicit provider-specific authorization (Telegram QR/phone, others OAuth, etc.) while using the shared, protected UI.

## CHECKLIST

- [x] Read current Syntagma AGENTS and relevant Hospital and control-surface protocols
- [x] Verify merged C3e-O/P, C4b issue and live existing CPU++/Connections owner boundaries
- [x] Preserve current three-bay CPU++ design, local account-name editors and Telegram native navigation
- [x] Add first-class Universal Sign-In view under CPU++ Connections without fake login
- [x] Add actual ID MANAGEMENT route and existing local host inspect control
- [x] Add strict default-deny UI status policy and adversarial regression + workflow
- [ ] Exact-head CI pass, repair any test/QML failures
- [ ] Operator review, authorized merge/deploy, native visual acceptance
- [ ] Identity owner supplies trusted, protected, host-registered sign-in start/status contract
- [ ] Connections owner supplies signed/installed origin, C4b/witness attestation and independent consent
- [ ] Provider owners supply authenticated Connect/Reconnect/Disconnect and recovery
- [ ] Only then enable distinct, consent-queued CONNECT ALL, after per-provider operations pass

## NEXT

**V2 // Identity Center host-aware sign-in:** continue **UI** in the same CPU++ Connections chassis: implement a strict host-provided, token-free sign-in capability and progress model, a real identity selection/context view, and one guarded explicit **SIGN IN** intent routed to an independently trusted host once its owner publishes/approves a narrow command contract. Until the host is installed, authentication status and button must remain unverified/disabled, never backdoor a local Python login, access keyring or trigger a browser by itself. Add connection lifecycle states for provider-specific consent, then integrate the protected C4b/C3e witness and C5 grants only after independent owner/technical acceptance.

## DECISIONS

Operator approves starting visual integration **now** and preserving all secured boundaries. This branch owns only the CPU++ Overview, small CPU++ navigation hook, new read-only policy, test, CI and this recovery document. No new architecture-level authentication decisions, local workstation writes, host grants, credential changes, Social store writer, task reassignment, merge or live Hospital registration. Operator retains final acceptance.
