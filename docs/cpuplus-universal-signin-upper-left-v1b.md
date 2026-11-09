# CPU++ Universal Sign-In // Upper-left control area V1b

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // CPU++ Universal Sign-In visual integration (external Hospital-compatible continuation; live registration unverified)  
STAFF ROLE // External DOC-compatible; no asserted live Hospital Staff attachment  
PROVIDER // OPEN AI // CHATGPT  
ASSIGNMENT // Move the now operator-confirmed Universal Sign-In control into CPU++'s unused upper-left identity area above SHARED // STATUS, continue honest integration without provider authentication  
BASE // `e087994e288a3d1ccbc98068cf06ba49fab9864a`  
PERMISSIONS // Bounded GitHub visual components, pure policy consumers, tests, CI, documentation. No real provider login, host permission enablement, credentials, Fedora machine writes, QML reload, PR merge or production activation. C3e/C4b/C5 and Identity Center backend work remains separately owned.

## IMPLEMENTATION

Operator confirms **OPEN ID MANAGEMENT** from V1 #1614 works perfectly. V1 is merged into main. Operator requests using the previously unused small upper-left area **above the SHARED // STATUS divider**, instead of stacking everything below the line.

The current `widgets/CpuPlusW.qml` left instrument bay has:
- Top title `CONNECTIONS // OVERVIEW` and the first `sharedHeaderLine`.
- A reserved `selectedMonitorIdentity` position for TEMP/SYSTEM that is **invisible and zero-height** for SETTINGS → CONNECTIONS.
- `sharedStateHeader` with the `SHARED // STATUS` caption and its divider.
- A scrollable lower `CpuPlusSettingsConnectionsOverviewPane`, which originally held both V1 Universal Sign-In controls and Social/inventory detail.

This change reuses that **reserved upper section**:
- New `widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml` mounts under the first title line, *above* SHARED // STATUS. It includes **UNIVERSAL SIGN-IN // CONTROL**, the honest unverified Identity Center status, the operator-confirmed **OPEN ID MANAGEMENT** action, existing **INSPECT LOCAL HOST** operation, and explicit CONNECT / RECONNECT / DISCONNECT and CONNECT ALL unavailable statuses. Uses original `ActionButton`, `GohuText`, `QuietText`, colors and existing `ConnectionsUnifiedSignInPolicy.project()`; no extra auth store or process.
- CPU++ mounts that component **only** when SETTINGS → CONNECTIONS is selected, anchors SHARED // STATUS below it, and leaves the selected TEMP/SYSTEM monitor identity section intact for their modes. Button navigation preserves the exact working `selectMode(5)` followed by `selectLocalManagementSection("IDS")` and the original menuOpen/mode guard.
- The lower `CpuPlusSettingsConnectionsOverviewPane.qml` returns to **CONNECTIONS // SHARED CONTROL**, Social metadata and connection inventory below the divider, without duplicated Universal Sign-In controls or alternate sign-in owner.
- The middle provider selector and right detail pane remain unchanged. Saved account names remain editable through the original Social single store from both ID MANAGEMENT and CONNECTIONS; Telegram OPEN TELEGRAM and RECHECK SESSION still use the one original owner.

## HOW TO USE

After operator-authorized merge/deployment:

**CPU++ → SETTINGS → CONNECTIONS**. The **upper-left** region above the line labeled **SHARED // STATUS** now presents Universal Sign-In's status and two side-by-side controls:
- **OPEN ID MANAGEMENT** switches to the same CPU++ ID MANAGEMENT → IDS view the operator already confirmed works.
- **INSPECT LOCAL HOST** calls the existing read-only local status inspector and updates only its unverified observation.
Below SHARED // STATUS remains Social account data, RELOAD SOCIAL STATUS and the existing inventory. Choose providers in the middle and use the established right-side controls.

## VERIFY

Updated `tests/cpuplus/test_cpuplus_universal_signin_control_center.cjs` asserts Universal Sign-In is inside the new upper-left component and never duplicated in the lower overview, the new component is visibly anchored under `sharedHeaderLine`, `sharedStateHeader` moves below it **only** in Connections, TEMP/SYSTEM use the original `selectedMonitorIdentity.bottom` path, and all authentication/credential actions remain strict default-deny even for synthetic all-true input. Existing Telegram, Social editor and identity host context checks remain in the V1 dedicated workflow.

Updated workflow adds the new QML component to trigger paths and the Qt6 parser. Exact-head GitHub CI and native Fedora visual geometry still require verification. This is repository UI implementation, **not** evidence of a running Quickshell update.

## WATCH OUT FOR

Upper-left layout uses a content-sized block to avoid clipping the future host-state detail. This decreases the lower overview's available vertical space only when Connections is active; that overview is already scrollable. On native desktop, verify readable 390px left-bay text and the two ActionButtons without overlaps. TEMP/SYSTEM left-bay identity heights and control flow must be unchanged.

V1, C3e-O #1605 and C3e-P #1610 are merged, but the C4b protected running-host/witness join at issue #1606, C2v rollback, real Identity Center sign-in service and C5 human-approved provider grants are still pending. No authentication/login can be declared available because this visual section exists.

## CHECKLIST

- [x] Confirm V1 #1614 merged and operator-tested ID MANAGEMENT navigation
- [x] Inspect actual left-bay reserved upper position and SHARED // STATUS divider anchor
- [x] Move Universal Sign-In status and existing control buttons above that divider
- [x] Restore original Social and inventory content under the divider
- [x] Preserve TEMP/SYSTEM monitor positions and existing right-side providers
- [x] Extend fail-closed UI/geometry test and Qt parser workflow
- [ ] Exact-head CI and any necessary repairs
- [ ] Operator review/merge and native visual check for two-button fit, scroll and divider
- [ ] Identity host owner publishes independently authenticated token-free sign-in status/command
- [ ] Complete approved universal user sign-in, then provider-specific Connect/Reconnect/Disconnect

## NEXT

**V2 // Readiness and sign-in progress interaction** within the newly positioned upper-left component. When the Identity Center owner supplies an approved **token-free, authenticated** status/intention channel, show real host enrollment, sign-in state, progress, denial/expiry and verified identity; enable SIGN IN only from the trusted host's guarded command capability. The display must never initiate direct Python OIDC login, browser redirect or trust a local saved label. Provider-specific activation remains independently gated by protected Connections host and per-provider authenticated consent.

## DECISIONS

Use existing unused **upper-left** space, do not add a fourth bay or new side menu. Maintain the previously operator-verified OPEN ID MANAGEMENT behavior and both saved account-name editor locations. No real credential mutations, new identity writer, local machine changes, cross-owner C3e/C4b/C5 edits, automatic merge or claimed live Hospital registration. Operator retains final acceptance. Recovery: this file, PR, and `tests/cpuplus/test_cpuplus_universal_signin_control_center.cjs`.
