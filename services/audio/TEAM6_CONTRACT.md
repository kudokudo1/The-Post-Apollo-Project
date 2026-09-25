# Team 6 — Application Audio Service Contract

Baseline: `943d27310f68d9941e7b19631fbd56aa9bd633e8`

This directory is Team 6 territory. It owns shared APP / WINDOW / TAB audio
physiology while leaving semantic desktop identity to Team 7 and host
presentation/routing to the serialized integration room.

## Service

`ApplicationAudioService.qml` owns:

- PipeWire/PulseAudio sink-input discovery through `pactl`
- raw sink-input snapshots
- descriptor-to-stream matching
- match evidence reporting
- mute policies
- one-shot mute synchronization
- volume policies
- last-touched volume conflict arbitration
- actual sink-input mute/volume mutations
- policy refresh workers/timers

It does **not** own:

- DesktopEntry/application canonical identity
- Sway enumeration
- tab/surface discovery
- provider-native tab lifecycle
- process/resource mutation
- Favorites persistence/reconstruction
- AppControl navigation/detail/result state
- service lifetime integration into `shell.qml` or `AppControlW.qml`

## Target descriptor

Team 6 accepts provider/identity evidence rather than inventing identity.

Current descriptor shape:

```text
{
    pids: [number, ...],
    tokens: [string, ...],
    strictTokens: bool
}
```

Meaning:

- `pids` are exact process observations supplied by a provider/identity adapter.
- `tokens` are matching aliases supplied by the caller.
- `strictTokens=true` performs exact normalized token matching.
- `strictTokens=false` preserves the donor's exact-or-suffix heuristic.

The descriptor is **matching evidence**, not canonical semantic identity.

## Semantic key and scope

Policies are keyed by two independent values:

```text
scope + semantic key
```

Expected scopes include:

```text
app
window
tab
```

The semantic key must come from the owning provider/identity adapter. Team 6 does
not define what makes two applications, windows or surfaces the same entity.

Separate scopes are required because the donor already has distinct APP and
WINDOW mute-policy namespaces. A WINDOW unmute may deliberately clear a broader
APP mute rule containing the same PID without erasing unrelated WINDOW policies.

## Raw stream evidence

Team 7 requested preservation of raw PipeWire properties. The service retains the
full `pactl -f json list sink-inputs` records in `sinkInputs`.

Important fields include:

```text
application.process.id
application.process.binary
application.id
application.name
media.name
stream index
```

Do not replace those observations with normalized aliases.

## Pure policy planning boundary

Policy matching/arbitration is separated from mutation.

Pure planners:

```text
mutePolicyTargets(inputs, policies)
pendingMuteTargets(inputs, policies)
volumePolicyTargets(inputs, policies)
```

Side-effect layer:

```text
applyMutePolicies(inputs)
applyPendingMuteStates(inputs)
applyVolumePolicies(inputs)
```

The planners never call `pactl`. They make future-stream matching, one-shot mute
synchronization, and overlapping volume arbitration testable without touching
the operator's live audio session.

The volume planner preserves donor semantics: when multiple APP/WINDOW/TAB
policies match the same sink-input, the highest/latest policy serial wins and
the target is clamped to the 0–100% unity range.

## Stream physiology vs host availability

`resolve(...)` intentionally reports:

```text
hasStreams
streamsMuted
observedVolumePercent
```

It does **not** define a generic `AudioAvailable` value.

The fused donor uses availability differently by host surface:

- WINDOW treats the selected live window as audio-controllable even before a
  matching sink-input exists.
- APP availability depends on the selected application having live Sway windows.
- TAB availability is a host/provider presentation decision and is not identical
  to "matching PipeWire stream exists."

Those decisions remain with the future host adapters. Team 6 reports the stream
facts only.


## Team 7 observation adapter

While Team 7's exact semantic schema is still unfrozen, Team 6 exposes an additive
`streamObservation(...)` / `observationSnapshot(...)` adapter with the shared
reconnaissance fields:

```text
provider        = PIPEWIRE
providerKey     = sink-input:<index>
lifetimeClass   = ephemeral
generation
raw
aliases[]       = kind / value / normalized / provider
relationships[] = evidence edges
```

This is deliberately an **observation**, not an `ApplicationEntity`.
`providerKey` is only an ephemeral PipeWire coordinate. Aliases preserve their
source kind and raw value; normalization is included only as matching evidence.

Team 7's frozen evidence envelope requires every alias to retain its provider.
Team 6 therefore emits `provider: PIPEWIRE` on each PipeWire alias.

When `application.process.id` is a valid PID, Team 6 also emits one explicit
relationship:

```text
kind           = EXACT_PID
targetProvider = PROCFS
targetKey      = pid:<n>
strength       = exact
sourceField    = application.process.id
```

That relationship is exact provider evidence about process attachment. It is
**not** a declaration that PID equals persistent application identity.

## Match evidence

`descriptorMatchEvidence(descriptor, sinkInput)` returns a separate evidence
record:

```text
matched
pidMatch
processId
streamIndex
strictTokens
tokenMatches[]
```

`resolve(...)` returns both:

- the untouched matching sink-input records
- separate match-evidence records

This follows Team 7's rule:

> identity != matching heuristic

A successful stream match is evidence that can support a semantic join. It is not
itself permission for Team 6 to declare canonical application identity.

## Team 5 handoff

Team 5 owns tab/surface discovery and provider-native lifecycle.

Team 6 may consume provider observations such as `processPids`, but should prefer
Team 7 canonical/derived descriptors once available.

Team 5 must not build audio matching tokens or mutate sink-inputs.

## Team 7 handoff

Team 7 owns:

- semantic application identity
- alias vocabulary/provenance
- DesktopEntry ↔ Application ↔ Sway ↔ PID ↔ Surface joins
- ambiguity handling
- identity adapters consumed by Team 6

Team 6 owns only the final relation from supplied evidence/descriptors to audio
streams plus the audio mutations/policies themselves.

## Team 8 handoff

APPS Core consumes Team 6 audio state/actions through a future host adapter.

Team 8 must not reintroduce application-specific sink-input discovery, matching,
mute policy or volume policy into APPS.

## Donor behavior preserved

The service intentionally preserves these current donor rules:

1. Audio volume is capped at 100%.
2. APP / WINDOW / TAB controls may overlap the same sink-input.
3. The most recently touched volume policy wins for an overlapping stream.
4. A mute policy can be armed before a matching stream exists.
5. Removing a persistent mute policy does not itself clear an existing stream mute
   bit; a one-shot requested mute state handles immediate synchronization.
6. APP and WINDOW mute policy namespaces remain distinct.
7. Narrow WINDOW unmute may clear the broader APP mute policy that contains the
   same PID.
8. Provider-owned lifetimes decide when semantic policy keys disappear.

## Provider lifetime pruning

`retainPolicyKeys(scope, liveKeys)` lets the owning provider tell Team 6 which
semantic identities still exist.

Team 6 does not decide provider lifetime. This mechanism only removes audio
policies after the owner declares an identity gone.

## Host integration boundary

Current status:

```text
service/provider branch exists
AppControl donor implementation remains intact
AppControlW rewiring has NOT happened
donor audio block has NOT been removed
service lifetime has NOT been integrated
```

Serialized integration must happen through T3.

A future host adapter may:

1. obtain semantic keys/descriptors from Team 7/provider adapters
2. call `resolve()` for APP/WINDOW/TAB presentation state
3. set/clear Team 6 mute and volume policies
4. issue direct mutations through Team 6
5. refresh after Team 5 surface changes
6. retain live policy keys when provider snapshots change

It must not duplicate the donor mutation backend beside the service after the
serialized donor cut is approved.
