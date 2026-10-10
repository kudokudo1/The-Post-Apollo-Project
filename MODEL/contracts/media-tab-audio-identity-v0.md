# Hi-Fi / Browser Media-to-Tab-to-Audio Identity — Investigation & Integration Contract (v0)

**Status:** reconnaissance and acceptance boundary, NOT implemented automatic tab ownership.
**Baseline inspected:** `7157f32f78d9292fc8514b931571902ad28ab73d` on `main`.
**Scope:** Hi-Fi consumer of shared tab, desktop-identity, and audio services.
**Traffic:** do not modify `widgets/AppControlW.qml`, `shell.qml`, Team 5's tab provider,
Team 7's identity resolver, or Team 6's audio physiology from the Hi-Fi lane.

## Confirmed live-system evidence (2026-10-09)

The operator demonstrated two audible Brave tabs with individually addressable
PipeWire sink-inputs and independently testable three-second mute/attenuation.
`NEXT STREAM` selects a candidate; MPRIS play/pause/seek follows the browser's
current media session. This **does not** establish a deterministic connection
between the two control surfaces.

The Hi-Fi's read-only evidence panel showed two Brave-matched sink-inputs with
`media.name = Playback`. Both appeared under the same application identity and
process ID. MPRIS reported a track title different from `Playback`.

Therefore the current `MediaAudioTargetResolver.js` exact-title rule returns
`NO EXACT TITLE MATCH`; that is a correct **unresolved** result, not a reason
to pick the first or newest sink input. Brief ChatGPT/TTS streams may appear
and disappear. New stream enumeration order, loudness and focus order cannot
serve as semantic identity.

## Canonical neighboring architecture

| Component | Authority | Available evidence | Missing fact |
| --- | --- | --- | --- |
| MPRIS playback adapter | Media transport | player bus, track title/metadata, play/pause/seek | Which native browser tab and sink-input own playback |
| Team 5 `TabSurfaceProvider.qml` | Tab/surface discovery and native lifecycle | AT-SPI tab labels/selected state; optional DEVTOOLS debugPort/targetId/URL; Kitty tab/PID evidence | PipeWire output ownership; browser media identity |
| Team 7 `DesktopIdentityEvidence/Relations` | Cross-provider observation and relationship semantics | Provider-local keys, aliases with provenance, explicit relation edges, resolved/ambiguous/unresolved envelope | Verified media-to-tab and tab-to-stream evidence |
| Team 6 `ApplicationAudioService.qml` | PipeWire discovery, matching evidence, policy and mutations | Sink index, PID/binary/application fields, `media.name`, volume/mute; ephemeral stream observations | Canonical tab identity or native browser volume control |
| Hi-Fi | Selected/loaded media, control intent, evidence display | MPRIS session and candidate audio streams | Authorized route for precisely this selected media |

Team 5 source: `feature/team5-tab-surface-provider`, current inspected head
`fb5dc664a7bd3f351ed2cb34012418f4432e8d3b`.
Team 7 source: `team7/desktop-identity-recon`, current inspected head
`8e0714b12c58f8f3c63242e9f84a9d82bb6d0287`.
Team 6 service is already present on current main but has not been wired into
AppControl's donor-volume code by the authorized integration room.
These are discovery/architecture references, not instructions to merge branches.

The AppControl donor at `widgets/AppControlW.qml` explicitly says TAB volume
currently uses app/provider matching, not necessarily tab-specific sink streams.
Its DevTools implementation can discover page targets only if a Chromium-family
browser was launched with a working remote-debugging endpoint. Its AT-SPI
discovery can identify tab labels and selection without guaranteeing audio-stream
IDs. Neither should be mistaken for a cross-provider tab→sink proof.

## Separate relations; do not collapse into one inferred ID

1. **Media session → browser tab/surface.** Prefer direct provider-native
   session/target relationship when available. An exact title is an
   inspectable *hint*, not a universal unique tab ID. Multiple tabs can have
   identical titles and media can retitle without changing its tab.
2. **Browser tab/surface → actual audio-control target.** Either establish an
   exact tab→sink-input relation from trusted source evidence, **or** declare a
   supported browser-native control route with separately verified scope.
   A debugPort, browser PID, window or normalized app token does not prove
   that its individual tabs map to distinct sink-inputs.
3. **Control route.** The chosen route must explicitly identify its scope:
   `player`, `tab`, `media-element`, `application`, or `sink-input`.
   A broader route must not be silently substituted for a requested narrower
   one. Provider capability and user permission are prerequisites to
   browser-native mutation, not implied by discovery.
4. **Lifetime.** Treat sink-input index, tab target ID, and player bus/track as
   session-bound coordinates. No stale selection may silently roll over to
   another stream or tab after disappearance, title change, process reuse or
   an extra TTS stream.

## Consumer-facing correlation result (proposed; not frozen shared schema)

```text
{
  playback: { provider, playerKey, trackKey?, trackTitle },
  surface: { provider, providerKey } | null,
  audioTarget: { kind: "sink-input" | "native-tab" | "native-media",
                 providerKey, scope, capabilities[] } | null,
  joins: {
    playbackToSurface: "resolved" | "ambiguous" | "unresolved",
    surfaceToAudio:    "resolved" | "ambiguous" | "unresolved"
  },
  evidence: [{ sourceProvider, sourceField, targetProvider,
               targetField, relationKind, strength }],
  reason: string
}
```

Do **not** substitute this draft for Team 7's authority. A provider supplies
observations, Team 7 resolves/labels relations, Team 6 supplies sink physiology,
and the Hi-Fi consumes a verified control route. A title-equality test can
produce candidate evidence but cannot mark `surfaceToAudio=resolved`.

## Safe route to first implementation

1. Ask Team 5 for a **read-only snapshot** of tab evidence against the same
   running Brave instance, without changing AppControl's host wiring.
   Probe for existing DEVTOOLS endpoint support first. Do not restart the
   current browser with extra instrumentation or open remote debugging
   without operator approval and a security review.
2. Record MPRIS title/player identity, each Team 5 provider tab row and raw
   Team 6 PipeWire sink record at one consistent moment. Preserve source
   provenance; report which fields are missing.
3. Test any proposed provider-native media→tab relation independently of
   tab→audio. In the currently observed case, two streams called
   `Playback` and sharing a browser PID **cannot** be joined to two tab
   titles by the existing fields alone.
4. If tab→sink relation remains unavailable, investigate an *optional*
   browser-native media-control capability adapter for known supported
   page media. Verify permission, active audio element, scope, revocation
   and tab identity before permitting a non-test mutation. It must not
   require Brave as a core-player dependency.
5. Keep the Hi-Fi's current explicit NEXT STREAM + armed, temporary tests
   until a candidate relation passes the matrix below. Do not replace a
   missing relationship with source order, loudness or most-recent tab focus.

## Acceptance matrix

- Two simultaneously audible tabs, **same browser**, play in order A→B,
  then B→A: automatic audio controls follow the *selected media* every time.
- Third temporary ChatGPT/TTS stream appears/disappears: no target transfer.
- Two tabs have the same title / no media title / generic `Playback`:
  report ambiguity or unresolved rather than choosing one.
- One stream disappears, its index is reused, or a browser/tab restarts:
  discard stale relation and require fresh evidence.
- Browser MPRIS title changes while a test is armed: disarm the old target.
- Tab/stream mapping is absent even though app-level matching succeeds:
  **do not** expose app-wide volume as a tab-specific Hi-Fi volume dial.
- Repeat with browser-native tab volume only if its permission and scope
  are separately verified; never assume browser media-element changes cover
  all audio contexts or every tab.
- Existing MPD, MPRIS transport, 3-second test restoration and AppControl
  behavior remain unchanged until integration is independently approved.

## Ownership and next handoff

**Team 5:** expose raw existing surface evidence; do not own audio joins.
**Team 7:** evaluate media session↔surface and surface↔stream relationships,
including ambiguity and source attribution.
**Team 6:** supply raw and matched sink evidence; own audio mutation only.
**Hi-Fi:** refuse unverified narrow audio routing and present a useful
"not correlated" state; consume the eventual resolution instead of
implementing duplicate native tab discovery.
**T3/integration:** authorize any shared host-service lifetime changes.

The immediate deliverable is an observation fixture from the live Brave
session. **No new automatic routing behavior is certified by this document.**
