# Team 8 — APPS integration readiness

Prepared from Team 8 isolated branch:

```text
branch: team8/apps-core-prep
content prepared through: 504beab36655d8e79d8fdfbb41d90371bbaf3233
certified patient observed: 8f5bb8f0cf67b526ed8cac577980e0416c176ed2
original branch base / merge-base: 943d27310f68d9941e7b19631fbd56aa9bd633e8
host file touched on parallel branch: NO
```

This packet does not authorize host surgery. It exists so Team 8 can re-read and
reconcile quickly when T3 Overhead assigns an APPS host-integration slot.

## 1. Preferred host-facing seam

The future host should consume one Team 8 composition surface:

```text
AppCoreFacade
├── AppCoreProvider
├── AppMetadataPresentation
├── AppCatalogPolicy
├── AppHiddenAdapter
├── AppSelectionPolicy
├── AppModePolicy
├── AppIdentityAdapter            -> Team 7
├── AppLaunchPlanner
├── AppLaunchCommandBuilder
├── AppBottleProvider
├── AppActionCatalog
├── AppActionPlanner
├── AppDetailActionPolicy
├── AppActionCommandBuilder
├── AppIconGlowPolicy
└── AppSelectorPresentation
```

The host should not individually reconstruct these policies.

## 2. Team 8 donor replacement map

### Catalog / source policy

Donor responsibilities represented by the isolated core include:

```text
appEntryIsFlatpak
appSourceLabel
appEntryHasLaunchCommand
appEntryMatchesSelectedSource
appEntryLaunchableForCurrentContext      host wrapper around T8 policy
appEntryLaunchableForSelectedSource      host wrapper around T8 policy
appActionsAvailableForCurrentContext     host wrapper around T8 policy
filteredApps / APPS result policy
```

Replacement organs:

```text
AppCoreProvider
AppCatalogPolicy
AppCoreFacade.resultRows(...)
```

The host still owns the live model binding, generic search box, result selection,
hover, focus and navigation.

### Source / launch mode policy

Donor responsibilities:

```text
restoreMatchingAppForSource
setAppSourceMode
setAppLaunchMode
```

Replacement:

```text
AppModePolicy
AppCoreFacade.sourceChangePlan(...)
AppCoreFacade.setSourceMode(...)
AppCoreFacade.setLaunchMode(...)
```

The donor setters currently perform generic host side effects. Those effects must remain
host-owned during transplant:

```text
selectedResultIndex
hoveredResultIndex
keyboardActive
ListView movement
detail reset
Favorites result reset
RUN refresh dispatch
```

For HIDDEN specifically:

```text
future RunService command catalog
    -> facade.hiddenCommandNames
    -> AppHiddenAdapter
    -> AppCatalogPolicy
    -> host applies generic selection/navigation
```

There must not be a second HIDDEN command catalog inside AppCoreProvider.

### Selection remembrance

Donor responsibilities:

```text
appEntryKey
rememberCurrentAppSelection
restoreRememberedAppSelection
```

Replacement policy:

```text
AppSelectionPolicy
AppCoreFacade.rememberedKeyFor(...)
AppCoreFacade.restoreIndex(...)
```

The remembered key lookup belongs to Team 8. Mutation of generic host selection and list
position remains host-owned.

### Launch planning / transport

Donor responsibilities represented by Team 8 include:

```text
bottleProgramName
appToolboxCommandTokens
appLaunchCommandTokens
appLaunchExecutableName
launchAppInBottle          policy/mechanism portion only
launchAppInToolbox         policy/mechanism portion only
launchApplication          APPS launch intent portion only
```

Replacement:

```text
AppLaunchPlanner
AppLaunchCommandBuilder
AppBottleProvider
AppCoreFacade.planLaunch(...)
AppCoreFacade.buildLaunchCommand(...)
```

Team 8 produces mechanism-specific execution descriptors. Actual process execution remains
outside Team 8.

The donor's `launchApplicationWithTabProvider()` must not be copied into Team 8. Its
discoverability instrumentation portion is the T5-domain SurfaceLaunch contract.

The required boundary is:

```text
T8 chooses launch intent/base mechanism
    -> T5 SurfaceLaunch supplies augmentation/lease/bootstrap metadata
    -> T8 transports supplied augmentation correctly
    -> host/executor performs the launch
    -> launched app owns runtime endpoint
    -> T5 discovers/activates surfaces
    -> T7 interprets identity relationships
```

Flatpak transport must preserve the repaired application boundary:

```text
flatpak run [wrapper options] APP_ID
    + argvAfterExecutable
    + existing application argv
    + argvAppend
```

Unresolved boundaries fail closed.

### APPS detail-action topology

The donor currently mixes APPS-specific action ordering/stable IDs into generic
detail navigation:

```text
detailActionStableId
detailActionCount
APPS branch of detailActionAvailable
```

Replacement:

```text
AppDetailActionPolicy
AppCoreFacade.detailActionCount(...)
AppCoreFacade.detailActionStableId(...)
AppCoreFacade.detailActionDescriptor(...)
AppCoreFacade.detailActionFacts(...)
AppCoreFacade.detailActionAvailable(...)
```

Team 8 owns the APPS provider topology and provider-owned stable IDs.

The facade composes Team 8 facts:

```text
actionsAvailable
launchable
bottleReady
toolboxLaunchable
```

Sibling facts remain injected only as booleans:

```text
audioAvailable             Team 6
resourceFreezeAvailable    Team 1
killAvailable              Team 1
```

The policy fails closed when required facts are absent. It does not import audio or
process/resource services, and it does not own Favorites persistence.

Generic detail index state, focus, scrolling, widgets and activation dispatch remain host-owned.

### APPS actions

Donor policy represented by Team 8:

```text
appEntryBrowserKind
appendBuiltinAction
appDesktopActions
browserShortcutSequence
runBrowserBuiltinAppAction     policy portion
runBrowserLaunchAction         launch-argument policy portion
```

Replacement:

```text
AppActionCatalog
AppActionPlanner
AppActionCommandBuilder
AppCoreFacade.actionsFor(...)
AppCoreFacade.planAction(...)
AppCoreFacade.buildActionCommand(...)
```

Team 8 may describe browser shortcut and launch descriptors. It does not focus Sway
windows, invoke wtype, execute DesktopEntry actions or launch processes directly.

### APPS metadata / presentation

Donor responsibilities:

```text
appOverride
appDisplayName
appDisplayDescription
appLongDescription
appDisplayIcon
appIconSource
safeActionIconSource
cachedIconGlow
rememberIconGlow
classifyIconGlow
APPS source-selector constants
APPS launch-selector constants
HIDDEN face presentation
APPS result source badge
APPS selector glow/fill/text/shadow policy
```

Replacement:

```text
AppMetadataPresentation
AppIconGlowPolicy
AppSelectorPresentation
AppCoreFacade display/presentation API
```

The host continues to own actual widgets, MouseArea, image capture/readback, timers,
animation lifetime, generic layout and navigation.

## 3. Explicit non-Team-8 donor tissue

The following donor areas must not be absorbed into Team 8 during APPS integration.

### RUN / host execution

```text
hiddenPersistentCommand
launchHiddenKitty
launchHiddenGeometry
launchHiddenToolbox
terminateHiddenCommand
launchHiddenCommand
```

Team 8 adapts externally supplied HIDDEN rows. It does not discover RUN commands or own
RUN process execution.

### Team 5 — surfaces/tabs

```text
appTabBridgeScript
appTabScanScript
appTabActivateScript
refreshAppTabs
activateAppTab
appNeedsForcedAccessibility
appTabDebugPort
appIsKitty
discoverability part of launchApplicationWithTabProvider
```

These belong to TabSurfaceProvider / SurfaceLaunch contracts.

### Team 6 — application audio

```text
appAudioIdentityTokens
appIdentityMatchesAudioSink
appMutePolicy*
applyAppMutePolicies
appVolumePolicy*
applyAudioVolumePolicies
selectedApplicationAudioKey
appMatchesAudioSink
scheduleAppAudioProbe
toggleSelectedApplicationMute
setSelectedApplicationVolume
```

Team 8 must not recreate sink-input discovery, matching, mute or volume physiology.

### Team 1 — process/resource

```text
selectedApplicationKillPids
selectedApplicationSourceEntry
selectedResourceScope*
resource limit/freeze/terminate functions
```

APPS may be a consumer of shared process/resource services after those contracts land.

### Team 7 — semantic identity / joins

```text
normalizeAppToken
appMatchTokens
windowMatchesApp
windowsForApp
appEntryForWindow
appEntryForTab
```

Team 8 owns DesktopEntry catalog coordinates, not the cross-provider resolver.

### Team 2 — Favorites

```text
favoriteSourceMode
favoriteSourceItem
favoriteRecordForApp
isFavorite*
Favorites UI/persistence/reconstruction
```

A preference predicate may influence Team 8 ranking, but Team 8 does not own Favorites
storage or reconstruction.

### Host-owned UI state

Examples that remain host-owned:

```text
selectedModeIndex
selectedResultIndex
hoveredResultIndex
keyboardActive
detailFocused
selectedDetailActionIndex
ListView positioning
scheduleHiddenFaceBlink
sampleRenderedIcon
generic selector widgets
generic result/detail routing
```

## 4. Pre-integration gates

Before any host cut:

1. T3 assigns Team 8 the serialized APPS host slot.
2. Re-anchor to the exact certified patient named in that order.
3. Re-read the APPS donor on that patient; do not assume this packet's line positions.
4. Reconcile current T1/T2/T5/T6/T7 contracts.
5. Run Team 8 isolated contract tests and validators.
6. Confirm `AppCoreFacade` remains the preferred single host-facing seam.
7. Confirm no donor behavior was added after this packet that belongs to Team 8.
8. Preserve all already-certified Favorites / FILES / REMOTE / hardware work.

## 5. Intended transplant shape

Conceptually:

```text
AppControl APPS host UI/state
        |
        | host-owned inputs + sibling-team contracts
        v
AppCoreFacade
        |
        +-- catalog/search/source/mode/selection
        +-- metadata/presentation
        +-- actions
        +-- launch planning + supplied SurfaceLaunch transport
        +-- Bottles state
        +-- T7 evidence delegation
        |
        v
host executes permitted descriptors / applies generic navigation
```

Donor removal should be serialized by responsibility. Do not delete a large contiguous
APPS block merely because it is adjacent in the file.

## 6. Certification boundary

Parallel-floor completion is not runtime certification.

A future APPS certification request should prove:

- normal Native launch parity
- Flatpak launch parity, with and without existing application argv
- Toolbox launch parity
- Bottles simple-argument launch parity
- HIDDEN dispatch remains RUN-owned
- source/launch selectors preserve presentation and mode behavior
- remembered selection parity
- browser/desktop action parity
- T5 SurfaceLaunch carriage parity
- T7 evidence handoff preserved
- no Team 1/2/5/6/7 physiology reintroduced
- no AppControl callback from Team 8 organs
- generic host focus/navigation remains host-owned
