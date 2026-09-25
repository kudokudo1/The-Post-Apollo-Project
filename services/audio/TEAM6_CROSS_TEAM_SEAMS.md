# Team 6 — Cross-Team Seams

Current Team 6 branch origin baseline:
`943d27310f68d9941e7b19631fbd56aa9bd633e8`

Current certified patient:
`77dcc84be51cb13acba91e9087d78ccb7142d6ef`

Team 6 is intentionally **not rebasing merely to look current**. The audio branch
will re-anchor only when T3 Overhead releases an authorized host-integration
slot.

## Traffic law

Parallel-safe Team 6 work:

```text
services
probes
tests
docs
contract work
cross-team reconnaissance
```

Serialized through T3 Overhead:

```text
AppControlW.qml
donor audio removal
shared result/detail/navigation wiring
shared selectors
service lifetime integration
```

## Team 5 — Tabs / Surfaces

Current Team 5 contract continues to expose:

```text
providerRecordKey(entry)
identityEvidence(entry)
processPids when known
provider-local surface evidence
```

Team 5 explicitly treats this as discovery evidence, not canonical application
identity.

Team 6 may consume provider evidence such as `processPids` only through a
matching descriptor or later Team 7 adapter. Team 6 must not import
`TabSurfaceProvider` or recreate Team 5 discovery.

Expected direction:

```text
Team 5 raw surface evidence
        ↓
Team 7 identity / relation adapter
        ↓
Team 6 audio matching descriptor
```

Team 5 may request/trigger an audio refresh after relevant surface changes, but
it does not own stream matching, mute policy, volume policy, or mutation.

## Team 7 — Desktop Identity

Team 7 remains semantic identity authority.

Current Team 7 recon distinguishes:

```text
persistent semantic identity
session application identity
ephemeral object identity
match evidence / aliases
```

Team 6 therefore keeps these separate:

```text
PipeWire sink-input index       = ephemeral audio coordinate
raw PipeWire properties         = observations
normalized aliases              = matching evidence
PID match                        = relationship evidence
semantic application key        = external / Team 7-owned
```

Team 6 exposes raw observations and match evidence, but never a canonical
`AudioIdentity`.

The Team 7 semantic entity schema remains unfrozen. Team 6's current
`streamObservation()` adapter is additive/reconnaissance-compatible, not a
claim that Team 7 must adopt that exact schema.

## Team 8 — APPS Core

Team 8 owns APPS-specific catalog/launch/action behavior.

Team 6 owns:

```text
sink-input discovery
audio matching
mute policy
volume policy
actual mute/volume mutations
audio probes/workers
```

APPS should eventually consume Team 6 state/actions through a host adapter rather
than rebuild APPS-local audio physiology.

## Team 1 — Process / Resource

PID/process observations may contribute to audio matching evidence.

Team 6 does **not** own:

```text
process trees
freeze/thaw
termination
resource limits
process safety policy
```

If a future audio adapter needs a process scope, that scope must come from the
identity/process providers rather than Team 6 growing a second process-control
layer.

## Team 2 — Favorites

Favorites persistence/reconstruction remains Team 2-owned.

If audio ever becomes favoriteable, Team 6 may expose provider state/actions, but
must not create:

```text
Favorites persistence
favorite JSON schema
watch/preferred-action persistence
canonical favorite identity
reconstruction ownership
```

## Re-anchor protocol for Team 6's eventual host slot

When T3 releases Team 6 for host integration:

1. read the exact certified HEAD named by T3
2. compare that patient against Team 6's current service branch
3. re-anchor/replay the isolated `services/audio/*` work onto that exact HEAD
4. reread current APP/WINDOW/TAB donor audio anatomy before wiring
5. preserve any intervening Favorites / FILES / REMOTE / Process / Tabs /
   Identity changes
6. perform only the authorized Team 6 host incision
7. run standalone audio probe
8. run donor behavior tests
9. report candidate HEAD for certification
10. do not remove unrelated host/navigation code

## Current cross-team conclusion

No present sibling contract requires Team 6 to rebase or change host code.

The current audio service boundary remains compatible with:

```text
Team 5 raw provider evidence
Team 7 semantic identity authority
Team 8 APPS consumer boundary
Team 1 process ownership
Team 2 Favorites ownership
```
