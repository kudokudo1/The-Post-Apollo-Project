# Team 5 — Tab / Surface Provider Test Matrix

Branch family: `feature/team5-tab-surface-provider`

This matrix is a provider-level acceptance plan. It does not authorize
`AppControlW.qml` wiring or donor removal.

## Acceptance levels

### STATIC PASS
Provider and embedded-script validators pass. No runtime dependencies required.

### PROVIDER RUNTIME PASS
The standalone probe can discover/refresh/activate supported surfaces without
AppControl.

### DONOR BEHAVIOR PASS
After a future authorized host transplant, the host preserves the donor-visible
TABS behavior.

### INTEGRATION PASS
After a future authorized integration, Team 5 coexists with Team 1/6/7 contracts
without importing their ownership.

Only the first two levels are Team 5 parallel-floor work today.

---

# 1. Static contract gates

Run:

```bash
python3 services/tabs/validate_provider_contract.py
python3 services/tabs/validate_donor_parity.py
python3 services/tabs/validate_embedded_scripts.py
```

Expected:

- provider contract PASS
- donor parity PASS while the donor-local TABS implementation still exists
- embedded Python syntax PASS
- no `appControlWindow` dependency
- no AppControl mode/search/result/focus dependency
- no Favorites dependency
- no PipeWire/audio mutation dependency
- no Team 1 process/resource mutation dependency
- no DesktopEntry/canonical application identity implementation

---

# 2. Discovery matrix

## A. LIBATSPI — ordinary accessible application tabs

Setup:
- run an application exposing real PAGE_TAB accessibility objects
- keep at least two tabs with distinct titles

Verify:
- provider emits `_tabRecord`
- `provider == "LIBATSPI"`
- provider-local `id` begins with `libatspi:`
- `path` is preserved
- observed `appName`, `windowName`, role metadata are preserved
- selection/focus state reflects the accessibility tree
- no DesktopEntry ID is fabricated

Failure tolerance:
- inaccessible/rebuilding nodes do not destroy a previously good snapshot merely
  because one refresh races the application tree

## B. AT-SPI-CACHE fallback

Setup:
- exercise the fallback scanner in an environment where the persistent bridge is
  unavailable or not ready

Verify:
- provider can emit `provider == "AT-SPI-CACHE"`
- `id` begins with `atspi-cache:`
- `busName` and `objectPath` are preserved
- observed app/window/title strings remain raw evidence
- no conversion to canonical application identity occurs

## C. DEVTOOLS — Brave / Chromium / Electron

Setup:
- run Brave/Chromium/Electron/VS Code with an exposed remote-debugging port
- open multiple page/webview targets

Verify:
- `provider == "DEVTOOLS"`
- provider key includes debug port + target id
- `debugPort`, `targetId`, `webSocketDebuggerUrl` are preserved
- provider family label remains evidence only
- activation targets the requested DevTools target
- native suspend/resume is available only when port + targetId exist

Important boundary:
- Team 5 may expose the debug port as process/identity evidence
- Team 5 does not own the later debug-port -> process-tree -> resource-scope join

## D. KITTY

Setup:
- run Kitty with remote control/listen socket enabled
- create multiple Kitty tabs and foreground processes

Verify:
- `provider == "KITTY"`
- `kittyAddress`, `kittyTabId` are preserved
- direct provider-observed `processPids[]` are preserved
- activation selects the intended Kitty tab
- foreground-process PIDs remain raw provider evidence, not semantic application identity

## E. no supported surfaces

Setup:
- run the probe with no discoverable PAGE_TAB, DevTools or Kitty surfaces

Verify:
- provider remains alive
- diagnostics explain provider availability
- empty list does not become a fabricated placeholder identity
- loading eventually settles
- fallback errors are surfaced without crashing the provider

---

# 3. Snapshot/lifecycle behavior

## Stable heartbeat

Given an identical provider snapshot:
- `dataSignature` remains unchanged
- `tabs` is not needlessly reassigned
- consumers are not forced to rebuild their result model on every heartbeat

## Real surface change

When a tab is opened/closed/renamed/selected:
- a new meaningful snapshot is published
- `snapshotWillChange` precedes the assignment
- `snapshotChanged` follows it

Team 5 does not preserve AppControl scroll/selection itself. A future host adapter
may use those signals to preserve host state.

## Provider loss and recovery

Verify:
- persistent bridge loss clears `bridgeReady`
- fallback scan can continue while bridge is unavailable
- bridge recovery resumes persistent snapshots
- a momentary empty refresh does not automatically discard a known-good nonempty
  snapshot

---


## Activation result integrity

Verify:
- provider activation JSON `{"ok": true}` emits success
- provider activation JSON `{"ok": false, "error": ...}` emits failure
- malformed/empty activation output is failure, not success
- stderr is surfaced diagnostically without converting failed JSON to success

This protects the standalone provider from treating "the worker printed
something" as proof that the target actually activated.

# 4. Native lifecycle vs Team 1 process control

## DEVTOOLS native suspend/resume

Verify:
- `hasNativeLifecycleControl(entry)` is true only for a DEVTOOLS surface with
  a positive debug port and nonempty target id
- `setLifecycleFrozen(entry, true)` performs provider-native target suspend
- `setLifecycleFrozen(entry, false)` performs provider-native target resume
- optimistic state rolls back when the provider mutation fails
- a second lifecycle request is rejected while one mutation is running
- pending rollback state is cleared after the authoritative JSON result
- stderr diagnostics alone do not roll back an otherwise successful mutation

This operation belongs to Team 5 because it mutates the surface through its
provider-native API.

## Linux process freeze

Explicit negative test:
- Team 5 does not send SIGSTOP/SIGCONT
- Team 5 does not expand process descendants
- Team 5 does not own protected-process policy or memory limits

Expected future route:

```text
Team 5 raw surface evidence
        +
Team 7 identity/relation adapter
        ↓
root PID(s)
        ↓
Team 1 ProcessScope / safety / mutations
```

A UI label such as "freeze tab" must not collapse these two mechanisms into one
owner.

---

# 5. Team 6 audio boundary

Verify:
- Team 5 emits no PipeWire stream discovery
- Team 5 emits no audio matching tokens as canonical truth
- Team 5 performs no mute/volume mutation
- surface changes may later cause a host/adapter to request Team 6 refresh, but
  the provider itself does not import Team 6

Expected route:

```text
Team 5 raw surface evidence
        ↓
Team 7 relation/identity adapter
        ↓
Team 6 matching descriptor
        ↓
ApplicationAudioService
```

---

# 6. Team 7 identity fixture matrix

The standalone probe emits:

```text
TEAM5 FIXTURE <json>
```

Capture representative fixtures for:

- Brave native
- Chromium if available
- VS Code / Electron
- Kitty
- an AT-SPI-only application
- multiple tabs with identical human titles
- one surface whose app display name differs from executable/app_id
- browser with several tabs/processes
- provider with no direct `processPids`
- provider with direct `processPids` (Kitty)
- DevTools provider with debug-port evidence

For every fixture, Team 7 should be able to see the original provider coordinates
without Team 5 having converted them to semantic truth.

---

# 7. Provider identity hazards

## Duplicate titles

Two surfaces may have the same `tabTitle`.

PASS condition:
- provider-local IDs remain distinct
- title is never used as the sole provider key

## DevTools restart

A browser restart may change debug port/target coordinates.

PASS condition:
- Team 5 reports the new provider coordinates
- Team 5 does not claim persistence across that restart

## AT-SPI object recreation

Accessibility object paths may change during application rebuild/restart.

PASS condition:
- Team 5 reports current observations
- Team 7 decides whether two observations belong to the same semantic entity

## Kitty tab reuse/session change

PASS condition:
- Kitty tab ID/socket coordinates remain provider-local
- cross-session semantic persistence is not asserted by Team 5

---

# 8. Future host-integration acceptance

Not executable until T3 releases Team 5's serialized slot.

Before incision:
1. re-anchor to the exact certified HEAD named by T3
2. rerun donor-surface comparison
3. preserve every intervening Favorites / FILES / REMOTE / Process / Audio /
   Identity host integration
4. reread current TABS donor anatomy

Authorized incision should eventually:
- instantiate/receive the provider through the approved lifetime architecture
- replace donor-local discovery state with provider state
- leave shared search/result/detail/focus behavior host-owned
- preserve host selection/scroll around provider snapshot changes
- route audio through Team 6
- route Linux process/resource actions through Team 1
- route semantic identity through Team 7
- remove only the donor physiology proven redundant after runtime PASS

Certification traffic:
- Team 5 submits candidate packet to T0
- T0 verifies and launches runtime evidence
- T3 alone advances certified HEAD
