# Team 7 runtime identity fixtures

This directory is reserved for cross-provider runtime fixtures used to validate
DesktopEntry / SurfaceLaunch / Sway / process / surface / audio joins.

No fixture is accepted as a canonical identity map merely because it was captured
from a working desktop.

## Why fixtures come before resolver scoring

The current donor already contains several reasonable but incompatible matching
policies. A scoring table designed only from source code would harden those
assumptions before we know which relationships survive real applications,
wrappers, Flatpaks, browser subprocesses, Toolbox, and Bottles/Wine.

The fixture corpus therefore records observations first and expected semantic
relationships separately.

## Bundle shape

Each fixture should be JSON with this conceptual shape:

```json
{
  "fixtureVersion": 1,
  "label": "firefox-native",
  "captureContext": {
    "session": "manual label",
    "notes": "human observations relevant to this capture"
  },
  "observations": [
    {
      "provider": "DESKTOP_ENTRY",
      "providerKey": "desktop-entry:firefox.desktop",
      "lifetimeClass": "persistent",
      "generation": null,
      "raw": {},
      "aliases": [],
      "relationships": []
    }
  ],
  "groundTruth": {
    "knownSameApplication": [],
    "knownDifferentApplication": [],
    "unknown": []
  }
}
```

`groundTruth` is an operator annotation, not something providers infer.

## Observation sources

### DesktopEntry

Use Team 7's `desktopEntryObservation(entry)` against the relevant
Quickshell DesktopEntry record.

Preserve the full raw entry fields that are available at capture time. Do not
reduce the fixture to the normalized tokens.

### Sway

Use Team 7's `swayWindowObservation(windowInfo)` against the Sway window
record for the same visible application.

The Sway con id and PID are session/ephemeral evidence.

### Process

Use Team 1-compatible process observations, adapted through
`processObservation(entry)`.

Capture enough of the process tree to distinguish browser parent/child
relationships and wrappers.

### SurfaceLaunch instrumentation

Capture T5-domain SurfaceLaunch bootstrap/correlation output whenever the launch
used one or more discoverability capabilities.

Adapt it through:

```text
surfaceLaunchObservation(launchMetadata)
```

This produces an `application-instance` observation. Preserve correlation ID,
Kitty listen endpoint, debug address/port, and requested/applied capability
lists.

Do not treat a generated correlation ID, socket, or debug port as persistent
application identity.

### Team 5 surfaces

Team 5's standalone probe already prints:

```text
TEAM5 FIXTURE <json>
```

Each `tabs[].evidence` record can be passed to
`surfaceObservation(evidence)`.

Keep the original Team 5 fixture beside the Team 7-adapted observation when
possible so no provider evidence disappears during adaptation.

### Team 6 audio

Team 6 already exposes:

```text
observationSnapshot(inputs)
```

Those PIPEWIRE observations are structurally compatible with Team 7's
observation envelope and should be inserted directly into the fixture bundle.
Do not wrap them merely to change ownership labels.

## First required matrix

Capture these before freezing resolver precedence:

```text
brave-native
firefox
vscode-or-electron
kitty
flatpak-app
toolbox-launched-app
bottles-or-wine-app
browser-multiple-tabs-and-processes
application-with-no-live-audio
display-name-differs-from-executable-or-app-id
shared-pid-windows-if-reproducible
```

## Relationship review

For each bundle, run the observation set through
`DesktopIdentityRelations.relationSnapshot()`.

Review separately:

```text
explicitEdges
pidGroups
debugPortEdges
kittyEndpointEdges
aliasEdges
```

These are evidence families, not votes.

A single PID observed by four providers must remain one correlated PID fact, not
be multiplied into six pairwise confirmations.

## Acceptance rule

A fixture may demonstrate that a rule is useful.

It must not by itself establish a universal rule.

Resolver precedence should be frozen only after the matrix exposes:

- successful joins
- false-positive joins
- ambiguous joins
- missing evidence
- provider restarts / changed ephemeral coordinates
- native vs wrapped launch differences
