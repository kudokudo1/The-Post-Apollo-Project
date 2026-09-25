# Team 5 — Tab / Desktop Surface Provider Contract

Baseline: `943d27310f68d9941e7b19631fbd56aa9bd633e8`

This directory is Team 5 territory. It provides cross-application surface discovery,
provider-native activation, diagnostics, refresh lifecycle, and true provider-native
tab lifecycle. It is intentionally independent of AppControl host state.

## Provider API

`TabSurfaceProvider.qml` exposes:

- `active: bool` — consumer-controlled provider lifetime request.
- `tabs: var[]` — discovered surface/tab records.
- `controls: var[]` — provider-native surface controls discovered alongside tabs.
- `loading`, `errorText` — fallback discovery state.
- `diagnostics`, `bridgeReady`, `bridgeError` — persistent bridge health.
- `refresh()`, `warmRefresh()` — discovery refresh requests.
- `activate(entry)` — activate a discovered tab/surface.
- `activateControl(entry)` — activate a discovered provider control.
- `hasNativeLifecycleControl(entry)` — true only for provider-native lifecycle.
- `setLifecycleFrozen(entry, frozen)` — native DEVTOOLS suspend/resume.
- `providerRecordKey(entry)` — current provider record identity only.
- `identityEvidence(entry)` — raw provider evidence for Team 7 identity mapping.

## Provider record evidence

Current donor providers expose different evidence:

### LIBATSPI
- `id` / provider key
- `path`
- `appName`
- `windowName`
- accessibility role / role name
- selected state

### DEVTOOLS
- `id` / provider key
- `appName`
- page title / URL-like window name
- `debugPort`
- `targetId`
- `webSocketDebuggerUrl`

### AT-SPI-CACHE
- `id` / provider key
- `busName`
- `objectPath`
- `appName`
- `windowName`

### KITTY
- `id` / provider key
- `kittyAddress`
- `kittyTabId`
- `processPids`
- tab title / window identifier

These values are discovery evidence. They are not canonical application identity.

## Team 7 handoff

Team 7 owns semantic identity. Its reconnaissance contract currently requires
Team 5 to preserve provider, provider-local key, appName/windowName exactly as
observed, provider-native parent/process metadata, processPids when known,
debugPort/targetId, busName/objectPath, and Kitty address/tab id.

Team 5 requires an adapter that can consume the raw evidence above and relate a
surface to the future canonical graph:

`DesktopEntry ↔ Application ↔ Sway Window ↔ PID/process scope ↔ Tab/Surface`

Team 5 must not fabricate missing DesktopEntry, application, Sway-window, or PID
relationships. Temporary provider record IDs remain valid until Team 7 supplies
canonical mappings.

Team 7's semantic entity/observation schema is not frozen yet. This Team 5
contract therefore freezes only preservation of raw observations and ownership
boundaries, not the final cross-provider identity schema.

## Team 6 handoff

Team 6 owns APP/WINDOW/TAB audio. Team 5 does not build audio tokens or mutate
streams. Once Team 7 provides canonical/derived descriptors, Team 6 may consume
those descriptors together with provider evidence such as `processPids`.

## Team 1 handoff

Linux process freeze, process trees, memory limits, protected-process policy, and
resource scope remain Team 1 territory.

The only lifecycle mutation Team 5 owns is a provider-native surface mutation. In
the current donor that is DEVTOOLS target suspend/resume. A UI label saying
"freeze tab" is not sufficient to classify an operation as Team 5-owned.

## Host integration boundary

The integration room owns AppControl wiring. A future host adapter may:

1. Set `active` when TABS should be live.
2. Read `tabs`, `controls`, loading/errors, and diagnostics.
3. Preserve host selection/scroll state around `snapshotWillChange` /
   `snapshotChanged`.
4. Close or retain the menu after activation according to host policy.
5. Trigger Team 6 audio refresh after relevant surface changes.
6. Route Team 1 resource actions separately from Team 5 native lifecycle actions.

The provider must not acquire knowledge of:

- AppControl mode indices
- `menuOpen`
- `searchInput`
- result selection / scroll state
- Favorites storage
- Sway window policy
- audio policy
- process/resource policy

## Current integration status

Provider/service work exists independently on the Team 5 branch. AppControl still
uses its donor-local implementation. No donor block has been removed and no
service lifetime has been integrated yet.
