# Team 1 — SYSTEM monitor integration contract

This document records the prepared SYSTEM boundary. It does not authorize host
rewiring.

## Prepared shared organs

```text
SystemPresentation
    systemAccent
    systemIconAccent
    systemRateMetricParts
    systemIconFor
    systemComponentWarning
    contributorRows

SystemControl
    network disconnect/reconnect
    reboot request
    reboot execution primitive
    contributor SIGTERM via ProcessControl

SystemMonitorController
    portable SystemMonitorView controller facade
    composes:
      selectionAdapter
      optional favoriteAdapter
      SystemPresentation
      SystemControl
```

## Host-owned responsibilities

The host/view still owns:

```text
which SYSTEM row is selected
whether that row is the active SYSTEM detail
favorite-record unwrapping if needed
monitor-box favorite persistence adapter
destructive confirmation modal UI
keyboard/focus/navigation state
refresh scheduling policy
```

`SystemControl` emits `rebootRequested(entry)`; it does not own the
confirmation surface.

## systemRebootArmed classification

The certified donor still declares `systemRebootArmed`, but the live code only
initializes it false and resets it false. Nothing arms it.

Therefore it is classified as:

```text
DEAD / LEGACY HOST STATE
```

`SystemMonitorController` exposes an always-false compatibility property only
so the current `SystemMonitorView` can migrate without requiring a simultaneous
view rewrite. It must not become shared mutable state.

A later cleanup may replace the current conditional button label with the
always-correct `REBOOT PC` text and remove the compatibility shim.

## monitorResultIcon classification

`monitorResultIcon(entry)` is not SYSTEM physiology. It multiplexes:

```text
Task icon
Thermal/Fan icon
SYSTEM icon
```

It should remain host/presentation aggregation rather than becoming a Team 1
shared mega-helper.

CPU++ already has a local monitor icon fallback:

```text
thermal/fan -> local thermal glyph
SYSTEM      -> category glyph
```

For SYSTEM-specific presentation, consumers should use
`SystemPresentation.systemIconFor(entry)`.

## Future CPU++ umbilical replacement

Current CPU++ SYSTEM dependencies on AppControl can be replaced as follows:

```text
appControlWindow.systemAccent
    -> SystemPresentation.systemAccent

appControlWindow.systemIconAccent
    -> SystemPresentation.systemIconAccent

appControlWindow.systemIconFor
    -> SystemPresentation.systemIconFor

appControlWindow.systemRateMetricParts
    -> SystemPresentation.systemRateMetricParts

appControlWindow.systemComponentWarning
    -> SystemPresentation.systemComponentWarning

appControlWindow.contributorRows
    -> SystemPresentation.contributorRows

appControlWindow.runSystemComponentAction
    -> SystemControl.runComponentAction

appControlWindow.terminateSystemContributor
    -> SystemControl.terminateContributor

appControlWindow.systemRebootArmed
    -> compatibility false / later remove from view

appControlWindow.monitorResultIcon
    -> do not transplant; use consumer-local aggregation
```

## Portable SystemMonitorView shape

The prepared controller contract is:

```text
host-specific selection adapter
             \
              -> SystemMonitorController -> SystemMonitorView
             /
optional Favorites adapter

SystemPresentation ------------^
SystemControl -----------------^
```

This allows AppControl and CPU++ to retain independent navigation and selection
state while consuming the same SYSTEM physiology.

## Integration traffic law

Until T3 releases Team 1's serialized slot:

```text
NO AppControlW.qml edits
NO shell/service-lifetime wiring
NO CpuPlusW/CpuPlusMonitorHost rewiring
NO donor removal
```

The prepared files remain isolated on `team1/system-liberation`.
