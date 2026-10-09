# HI-FI // Universal Media Controller — Contract v0 (DRAFT)

**Project:** Meta Apollo Logos // Post-Apollo  
**Status:** Architecture draft — no executable implementation is certified by this document.  
**Scope:** Hi-Fi first; contracts should later be reusable by TV, media shelves, and other consumers.  
**Placement:** `MODEL/contracts/` is the architecture home. No changes to `shell.qml`, `Mediaplayer.qml`, `MediaDeckW.qml`, or existing audio services are part of this draft.

## 1. Purpose and boundaries (agreed)

The Hi-Fi is the primary **music/audio** machine. It unifies interaction with music from YouTube, owned/local files, and later Spotify, SoundCloud, Apple Music, and other services. Providers remain independently accessible outside the deck. The future TV is for intentional full-size video viewing; the separate mixer is for desktop-wide sound management.

The universal controller is a **permanent, headless, terminal-accessible** coordination layer, not a Kitty window and not the physical deck or display. A CLI/TUI is an optional client to the same API that Quickshell uses. It should not require a particular browser, nor Qt, to run.

The contract splits responsibilities into four distinguishable parties:

| Party | Owns | Does **not** own |
| --- | --- | --- |
| UI consumer (Hi-Fi, later TV/shelves) | Display, buttons, browse cursor, layout, user actions | Provider APIs, subprocess lifecycle, backend selection |
| Source/provider adapter (YouTube, local, etc.) | Discovery, search, catalog, playlists, metadata, source-specific playable references and requirements | Global backend policy; physical controls; shared audio routing |
| Universal Media Controller | Media/queue/session state, source and backend registries, capability matching, backend selection, dispatch, normalization, errors | Hardcoded provider protocols or embedded UI |
| Playback-backend adapter (MPRIS, MPD, web runtime, etc.) | Playing/cueing if available, pausing, stopping, seeking, track progression, observed state and volume controls it actually supports | Catalog browsing or choosing which backend wins globally |

**Core rule (agreed):** source adapters declare requirements and capabilities; the universal controller chooses the compatible backend; backend adapters execute and report reality. A new source or backend is added as a separate adapter, not bolted into one giant provider-specific switch statement.

## 2. Separate identities and contexts (agreed principles; field names provisional)

These are different objects, even when they refer to the same song:

- `Source`: a provider such as YouTube, local library, Spotify.
- `MediaRef`: source-qualified stable reference to a track, playlist, album, live stream, or another supported item. Keep the original provider ID and item type; never assume a YouTube ID equals a local file identity.
- `BrowseContext`: which source, query, collection, page, and row the user is inspecting. Browsing must not replace the loaded item or interrupt playback.
- `Selection`: a highlighted track, playlist, or chosen start index. Selection alone never loads or plays.
- `LoadedMedia`: the actual object inserted into the machine, and optionally its selected starting track. This is the reference expressed by the cassette, disc, or other visible loaded-media format. Loading is a distinct action from playback.
- `PlaybackSession`: the active backend instance, queue/track position, play state, transport capabilities, volume scope, and associated audio-stream evidence.
- `VisualizationMode`: `desktop` or `player`. This is **not** a media source or provider selection.

Source identity, loaded-media identity, backend instance identity, audio-stream observations, and UI selection must **not** be collapsed into a single string. A browser instance or PID is not persistent canonical media identity.

## 3. Minimum interface proposals (PROPOSED v0 names)

These are **semantic operations**, not finalized QML method signatures or a chosen IPC encoding.

### Source adapter interface

- `describe()`: ID, display name, implementation version, auth/network/offline requirements, advertised browse capabilities.
- `search(query, cursor?)` and `list(collectionRef, cursor?)`: discover media without starting playback; paging optional.
- `inspect(mediaRef)`: detailed metadata, children/track order, counts, permissions, and supported operations.
- `prepare(mediaRef, startAt?)`: return a provider-qualified playback request/requirements for the controller to route. **Do not select a backend or start playing.** A provider may decline or require sign-in.

`search`, `list`, and `prepare` are separately advertised capabilities: not every provider can do all three.

### Playback-backend interface

- `probe()`: whether available now and which media requirements / command operations are supported.
- `cue(request, startAt?)`: load without autoplay **if supported**; return an explicit inability when not supported.
- `play()`, `pause()`, `stop()`, `seekRelative(seconds)`, `next()`, `previous()` and `setVolume(percent)`: each separately capability-gated; do not pretend success if unavailable.
- `observe()` / events: actual playback state, active media, position, duration where known, volume where known, and current capabilities.
- `release()`: detach/cleanup only controller-owned resources; never shut down an unrelated browser or player.

MPRIS may initially expose **remote control of an existing player** without arbitrary media loading or provider search. A browser MPRIS adapter is generic (player discovery and explicit target selection), not a Brave-only requirement. The existence of Brave on one machine does not certify all operations.

### Controller interface

- `discoverSources()`, `browse(source, ...)`, `inspect(ref)`, `select(ref)` (non-destructive to playback).
- `load(ref, startAt?, autoplay=false)`: verify source requirements, choose an eligible backend, and cue/prepare without unrequested playback. If the backend cannot separately cue, report that limitation instead of secretly autoplaying.
- `play()`, `pause()`, `stop()`, `seekRelative(±5)`, `next()`, `previous()`.
- `setPlayerVolume(percent)`: control **only deck-owned audio** when an isolated/owned volume target is known; otherwise report unavailable.
- `setVisualizationMode(desktop|player)`: change visualizer audio source only, not provider or playback selection.
- `getSnapshot()` and subscription: separate `browse`, `selection`, `loaded`, `session`, `transportCapabilities`, `visualization`, and `errors`.

The controller chooses a backend using provider requirements, available registered backends, real-time capabilities, user override (if any), and ownership constraints. Provider adapters may express preferences/constraints as data; they may not override selection policy. **Do not silently switch a running session to a different backend** or seize an unrelated tab.

## 4. UI consequences (agreed)

- The physical cassette/disc/bay depicts **loaded** media, not the current search highlight. Exact media-format-to-provider mapping is still open.
- The display is **text-first**: source, song/track, list, playlist, state, elapsed/remaining time, and quick keyboard search. No default video thumbnail, full video, transcript, or lyrics.
- A thin Now Playing strip remains visible during browsing and can expand to queue/track quick access. Expanding/collapsing it restores the prior browse cursor and query.
- Inspecting a playlist and choosing track 4 does not start playback; `load` does not imply `play`.
- The control deck owns play, pause, stop, previous, next, and ±5-second seeking initially. Navigation, source selection, and music-only volume are planned; exact physical dial/button arrangement is deliberately open.
- The deck may have a truly unloaded, quiet state; whether previously loaded media stays physically inserted after stop is still open.

## 5. Audio boundaries (agreed intent; NOT implemented by this contract)

- **Music-player volume** must affect only audio attributable to the deck's playback session, never the whole desktop or unrelated browser tabs.
- **CAVA Desktop** visualizes the actual combined desktop output; it does not categorize simultaneous sources.
- **CAVA Player** visualizes only audio routed through the deck, regardless of which provider is currently selected. Provider switching does not imply CAVA Desktop/Player switching.
- Identifying the deck's playback session and identifying actual PipeWire streams are distinct responsibilities. Reuse the existing `services/audio/ApplicationAudioService.qml` stream-discovery / mutation boundary and its Team 6 contract, rather than building a competing audio physiology engine.
- Application/tab/PID and stream matching are **evidence**, not guaranteed canonical identity. Never change another stream's volume just because it shares a browser process.
- Until isolation can be verified, leave Player-mode routing and per-deck volume disabled/unavailable rather than claiming system volume is deck volume.

## 6. Capabilities, errors, and safety

Capability state should distinguish `supported-now`, `temporarily-unavailable`, and `unsupported`, with a human-readable reason and an optional permission/sign-in requirement. Provider catalog rights and playback backend commands are separate, not flattened into a single yes/no.

Every command returns an explicit result (`accepted` or `rejected`, reason, target session/generation) and is reconciled with subsequently **observed** backend state. Do not optimistically mark playback as successful just because a process started.

Required failure cases: missing provider, no compatible backend, network unavailable, login required, no active target, ambiguous MPRIS target, failed cue, expired playable reference, unsupported seek/skip, player exit, and stale asynchronous updates. Never take over an unrelated active player as a fallback.

Credentials and tokens stay out of repo and debug logs; adapters own their provider authentication mechanics subject to the controller's permissions policy. Distribution must not depend on Brave, on private credentials, or on unauthorized YouTube playback behavior. Official embedded YouTube playback must respect applicable player-display/API requirements.

## 7. Acceptance scenarios for the eventual v0 implementation

- [ ] Browse a YouTube playlist while local audio plays; the loaded-media identity and Now Playing strip remain unchanged.
- [ ] Highlight song 4, inspect it, and choose a starting position **without playing anything**.
- [ ] Load a compatible playlist at song 4 without autoplay. Play begins at that chosen position only after the explicit command.
- [ ] ±5 sec transport works where seekable and is visibly unavailable where unsupported.
- [ ] With multiple MPRIS players, the selected backend target is explicit and no unrelated player is controlled.
- [ ] A missing Brave installation does not prevent launching the controller or using local playback.
- [ ] A provider that cannot expose tracks or a backend that cannot cue reports limitations; the UI does not fabricate metadata or playback state.
- [ ] Adjusting player volume cannot alter unrelated applications or tabs.
- [ ] Player CAVA responds to deck-owned audio only; Desktop CAVA responds to the mixed desktop output.
- [ ] Disconnect/reconnect, stale replies, app restart, and offline local-playback behavior are predictable.

## 8. Build sequence (PROPOSED; no code authorized by this document)

1. **Contract confirmation and tests:** finalize IPC/schema and capability semantics; add stub adapters and contract tests, no shared `shell.qml` wiring.
2. **Headless controller + CLI:** provider and backend registration, playback session state, command results, manual backend-target selection.
3. **First MPRIS backend:** connect to an explicitly chosen existing browser/player to test physical controls. This is a **control-only prototype** until a source supports explicit `load`; do not claim YouTube search has been implemented.
4. **Source adapters:** local library and YouTube catalog/search/playlist browsing; separate the supported playback method from catalog browsing.
5. **UI integration:** feed actual controller snapshots into display, queue drawer, loaded-media bay and transport, preserving unrelated concurrent QS work.
6. **Audio-isolation integration:** coordinate with existing audio identity and PipeWire service owners; only enable player-only volume/CAVA once proven.
7. **Additional providers/backends:** add new independent adapter modules, not provider-specific branches inside the controller.

## 9. Decisions recorded / still open

**Agreed:** universal controller owns backend selection; provider adapters declare requirements; backends execute; adapters remain independent; no Brave dependency; text-first display; browsing/loading/playing are distinct; persistent expandable Now Playing; player-only volume; Player CAVA tracks deck session and Desktop CAVA tracks desktop mix.

**Open:** exact IPC transport, schema/versioning and persistence; packaged compliant YouTube playback; per-provider auth; source-to-physical-media format mapping; final chassis and control inventory; music-stream routing/identity contract integration; fallback/override UX; whether loaded media remains inserted after stop.

**Implementation status:** `widgets/MediaDeckW.qml` currently drives MPD directly through seven commands. The permanent controller, source adapters, audio isolation, and YouTube deck browsing are **not yet implemented**. This is a design agreement in progress, not certification that runtime features exist.
