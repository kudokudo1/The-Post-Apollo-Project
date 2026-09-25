# Team 5 → Team 7 Identity Handoff Note

Status: parallel-floor contract reconnaissance  
Team 5 branch: `feature/team5-tab-surface-provider`

## Confirmed compatibility

Team 5 now preserves the raw surface evidence required by Team 7's frozen
observation/evidence envelope input:

- provider
- provider-local key
- appName
- windowName
- path
- accessibility role
- accessibility roleName
- busName / objectPath
- processPids
- debugPort / targetId / webSocketDebuggerUrl
- kittyAddress / kittyTabId

Team 5 does not emit a competing semantic envelope, alias vocabulary,
relationship graph, lifetime classification, resolver score, or canonical
application identity. Team 7 remains responsible for wrapping raw provider
evidence through `DesktopIdentityEvidence.surfaceObservation(...)`.

## One implementation mismatch to reconcile in Team 7

Team 7's current written contract says the Surface/Tab adapter preserves:

```text
path / role
```

Team 5 now exports both:

```text
role
roleName
```

However, the current Team 7
`DesktopIdentityEvidence.surfaceObservation(...)` implementation copies
`roleName` into `raw` but does not copy numeric `role`.

This is not a Team 5 blocker and does not justify host surgery. It is a sibling
contract/implementation mismatch for Team 7 to reconcile in its own territory.

## Why numeric role is worth preserving

The provider observes role directly from AT-SPI and currently uses it to
distinguish page tabs and provider-native controls. Keeping numeric role in the
raw evidence envelope preserves provenance and avoids forcing later consumers
to reverse-map localized/human role names.

Team 5 will continue preserving both values as raw observations.


## SurfaceLaunch correlation evidence

The resolved SurfaceLaunch seam adds launcher-neutral bootstrap evidence that
Team 7 may consume later:

```text
correlationId
kittyListenOn
debugAddress
debugPort
lease source (generated / caller-supplied)
```

These are transient launch/application-instance coordinates.

Team 7 may use them to explain joins such as:

```text
launch transaction
    ↔ running process
    ↔ Kitty socket / DevTools endpoint
    ↔ discovered surface
```

They must not become persistent semantic application identity.

Team 5's SurfaceLaunch layer does not perform those joins itself.
