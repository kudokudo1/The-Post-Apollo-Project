# Team 6 — Application Audio Test Matrix

Baseline: `943d27310f68d9941e7b19631fbd56aa9bd633e8`

This matrix defines Team 6 validation without requiring AppControl host wiring. It
separates deterministic service-contract checks from later live/runtime checks.

## Executable guard layers

Team 6 currently carries four distinct validation layers:

```text
services/audio/validate_audio_contract.py
    static ownership/API/test-suite guard

services/audio/validate_donor_audio_anatomy.py
    pre-integration AppControl donor-anatomy guard

tests/audio/tst_ApplicationAudioContracts.qml
    isolated QtTest suite for pure audio behavior

services/audio/ApplicationAudioServiceProbe.qml
    standalone live/read-only PipeWire probe
```

These layers are intentionally different. Static or isolated passes are not
runtime certification. Operator-launched runtime evidence is routed through
T0 Manager, and T3 Overhead alone certifies a patient.

## A. Deterministic descriptor matching

### A0 — descriptor PID normalization

Descriptor PID evidence may arrive through JSON/QML as numeric strings.

Expected:

- `"4242"` and `4242` compare as the same exact PID evidence
- normalization returns positive unique integers
- PID 0/1, negative values, fractions, and non-numeric strings are rejected
- normalization does not create semantic application identity

### A1 — exact PID evidence

Descriptor:

```text
pids = [4242]
tokens = []
```

Stream:

```text
application.process.id = 4242
```

Expected:

```text
matched = true
pidMatch = true
```

### A2 — strict exact token

Descriptor:

```text
tokens = ["brave"]
strictTokens = true
```

Stream:

```text
application.process.binary = "brave"
```

Expected: match.

### A3 — strict mode does not suffix-match

Descriptor token:

```text
orgmozilla
```

Stream token:

```text
firefox
```

Expected: no match unless Team 7 explicitly supplies an exact alias that matches
the stream observation.

### A4 — fuzzy suffix mode preserves donor WINDOW/TAB heuristic

Descriptor token:

```text
orgmozillafirefox
```

Stream token:

```text
firefox
```

With `strictTokens=false`, expected: match.

### A5 — short fuzzy aliases are rejected

Descriptor token:

```text
app
```

Expected: no suffix match because the shorter normalized token is under four
characters.

### A6 — blocked generic strict tokens

Generic strict aliases such as:

```text
electron
chromium
browser
application
desktop
terminal
flatpak
```

must not become strict stream aliases by themselves.

## B. Raw PipeWire evidence

For each raw sink-input, Team 6 must preserve the original record and expose at
least:

```text
stream index
application.process.id
application.process.binary
application.id
application.name
media.name
mute
volume
raw properties
```

Expected: normalization/matching must not overwrite the raw observation.


## B2. Team 7 observation adapter

For each live sink-input, `streamObservation()` must expose:

```text
provider = PIPEWIRE
providerKey = sink-input:<stream index>
lifetimeClass = ephemeral
generation
raw observation
aliases with provenance
relationships[]
```

Expected:

- provider key is treated as ephemeral object identity
- raw PipeWire evidence is not overwritten by normalized aliases
- aliases keep their source field/kind and `provider=PIPEWIRE`
- a valid `application.process.id` produces an exact
  `EXACT_PID -> PROCFS pid:<n>` relationship
- invalid/system-like PIDs do not produce that relationship
- no canonical application key is manufactured
- every accepted live snapshot advances the observation generation

## C. Match evidence vs identity

A resolved stream must expose separate evidence:

```text
matched
pidMatch
processId
streamIndex
strictTokens
tokenMatches[]
```

Expected:

```text
stream match != canonical application identity
```

Team 6 must never manufacture a DesktopEntry/application identity from a
successful stream match.

## D. Policy namespaces

### D1 — APP and WINDOW mute scopes remain distinct

These must coexist:

```text
app:<semantic-key>
window:<semantic-key>
```

A collision in the semantic-key text must not collapse the policies.

### D2 — scope normalization

```text
APP
app
 App
```

must address the same Team 6 scope after trimming/lowercasing.

This applies to mute and volume policies.

### D3 — narrow WINDOW unmute / broad APP policy

If an APP mute policy contains PID 4242 and WINDOW 4242 is explicitly unmuted,
the host adapter may request:

```text
clearMutePoliciesWithPid("app", 4242)
```

Expected: matching APP mute policy is cleared.

Unrelated WINDOW/TAB policies remain intact.

## E. Future-stream behavior

### E1 — arm mute before stream exists

Create a mute policy for a valid descriptor when no stream matches.

Expected:

- policy remains stored
- policy worker continues probing
- first future matching stream is muted

### E2 — one-shot unmute

Removing a persistent mute policy does not itself clear an already-muted
PipeWire stream.

Expected:

- persistent policy removed
- one-shot pending mute state requests `muted=false`
- matching current stream receives explicit unmute mutation
- one-shot request is then discarded

## E2. Pure policy planners

Policy decisions must be testable without invoking live mutation APIs.

Expected:

```text
mutePolicyTargets
    returns currently-unmuted matching streams that persistent policy would mute

pendingMuteTargets
    returns only matching streams whose observed mute state differs from the
    requested one-shot state

volumePolicyTargets
    resolves overlapping APP/WINDOW/TAB rules by newest serial and clamps to
    the service volume ceiling
```

The isolated QtTest suite must exercise these planners directly. It must not call
`setSinkInputMute()`, `setSinkInputVolumes()`, `setMutePolicy()`, or
`setVolumePolicy()`.

## F. Volume behavior

### F1 — unity cap

Inputs below 0 clamp to 0.

Inputs above 100 clamp to 100.

Team 6 must never intentionally request amplification above unity.

### F2 — overlap arbitration

APP, WINDOW and TAB policies may all match one sink-input.

Expected: highest/latest policy serial wins.

### F3 — stable conflict resolution

A stale lower-serial policy must not immediately fight a newer policy on the
same stream.

### F4 — no unnecessary mutation

If the observed stream volume is within less than one percentage point of the
desired target, the policy worker should not issue another volume mutation.

## G. Provider lifetime

Provider-owned semantic lifetime remains outside Team 6.

Given:

```text
retainPolicyKeys("window", liveKeys)
```

Expected:

- WINDOW mute/volume policies absent from `liveKeys` are pruned
- APP and TAB scopes are untouched
- Team 6 does not independently decide which windows still exist
- `policyKeysOutsideLiveSet(...)` exposes the pruning decision without mutation
- `mutePolicyKeysWithPid(...)` returns only policies in the explicitly requested
  scope
- invalid/system-like/fractional PIDs do not produce cleanup targets

## H. Mutation validation

### H1 — valid sink-input index

Only non-negative integer stream indexes may reach:

```text
pactl set-sink-input-mute
pactl set-sink-input-volume
```

Reject NaN, negative values and fractional indexes.

### H2 — empty mutation set

An empty or invalid index list must return false and issue no mutation.

## I. Host-semantics boundary

`resolve()` reports stream physiology only:

```text
hasStreams
streamsMuted
observedVolumePercent
```

It must not define generic host values such as:

```text
AudioAvailable
selected
menuOpen
detail state
```

Those remain adapter/presentation decisions during serialized integration.

## J. Live fixture matrix — later runtime work

Capture raw Team 5 / Team 6 / Team 7 evidence for the same target when practical.

Required representative cases:

1. native Wayland application with audio
2. Flatpak application with audio
3. Brave/Chromium with multiple tabs
4. Electron application
5. Kitty surface with provider `processPids`
6. application with multiple Sway windows
7. application with no active audio stream
8. two windows sharing one PID, if reproducible
9. application whose display name differs from executable/app_id
10. future stream created after a mute/volume policy is already armed

For each fixture retain:

```text
Team 5 provider-local surface evidence
Team 7 identity/join evidence
Team 6 raw PipeWire sink-input observation
Team 6 match evidence
expected semantic relationship
ambiguity notes
```

Do not convert synthetic examples in this document into canonical production
identity aliases.
