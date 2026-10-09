# Hi-Fi browser-audio isolation bench (operator protocol)

**Status:** experiment, not certified tab-level targeting.  
**Owner:** Media Deck. This does **not** touch AppControlW, shell wiring, or Team 6's extracted service.

## Setup

1. Pull `main` and restart Quickshell. Play a normal YouTube video in any existing MPRIS-compatible browser. No downloaded music is needed. The Hi-Fi opens from its taskbar button.
2. In the display, choose **USE MPRIS**. If more than one external player is exposed, use **NEXT PLAYER** until the intended one is shown. The seven transport keys now act on that one MPRIS player; **LOCAL / MPD** restores the previous MPD-only controls. Browser MPRIS may represent the browser's current media session, not the individual YouTube tab.
3. Verify that the displayed title changes to the currently playing media and that play/pause works. If it does not, stop here: the transport bridge itself is unverified.
4. Open a **second tab in the same browser** playing its own audible content. Both audio sources must actually be sounding simultaneously for the comparison to mean anything.
5. Read the **AUDIO: N APP-MATCHED STREAM(S)** line in the Hi-Fi. It uses the extracted `services/audio/ApplicationAudioService.qml` `resolve()` and `pactl` observations. A candidate stream is only an *application match*: it does not prove a tab-specific route.

## Target-selection behavior (safety-gated)

The target is separate from MPRIS transport. Playback still controls the MPRIS
player/media session; audio mutations act only on the PipeWire target resolved below.

- **AUTO TARGET** removes an old manual selection and rechecks for exactly one
  candidate whose raw PipeWire `media.name` matches the current MPRIS track
  title. This is a narrow metadata correlation, **not certified tab ownership**.
  If no unique exact match exists, the panel shows `NO AUDIO TARGET` and refuses
  to arm an audio test. Never silently fall back to the first browser stream.
- **NEXT STREAM** explicitly chooses a candidate. The manual choice is tied to
  the current MPRIS player bus/title plus the selected stream index, PID, binary,
  application ID and raw media-name observation. The 2-second stream refresh
  must not silently switch that choice to another candidate.
- If the manually selected stream disappears, its evidence changes, or a
  different MPRIS media title becomes active, the audio target becomes
  unavailable. Use **NEXT STREAM** to explicitly choose again or **AUTO TARGET**
  to re-evaluate exact-title evidence.
- The `TARGET:` line explains whether the result is a manually selected stream,
  a unique title match, stale, ambiguous, or unavailable. Even a unique title
  match may still represent application-level evidence rather than a real tab.
- Brief text-to-speech output can add and remove sink-inputs during an experiment.
  Stream-count changes by themselves do not justify reassigning an audio target.

## Explicit, temporary stream tests

**CAUTION:** A stream may contain multiple browser tabs. These tests may therefore change the volume or mute of *both* tabs for three seconds. The probe attempts to restore original state, but a crash, forced kill, audio-device change, or conflicting policy could prevent restoration. Do not run it while relying on uninterrupted audio.

- **NEXT STREAM** cycles manually among matched PipeWire sink-inputs. For cases with no exact-title auto match, select a stream before arming.
- **ARM TEST** enables one next experiment, only with a resolved audio target. Selecting the action consumes the arm; tests never start automatically when the deck opens. A changed media session disarms the experiment.
- **MUTE / 3S** mutes the selected stream for three seconds and restores its previous mute state.
- **VOLUME / 3S** temporarily halves the selected stream's original channel volumes for three seconds and restores the original values.
- The experiment script validates the selected stream index against its observed PID/binary before touching it and before restoring it. It refuses to mutate streams whose identity cannot be checked. It does not claim this evidence identifies the browser tab.
- The status line reports whether the script reported `RESTORED` or a failure. If restoration fails, use the existing desktop audio controls to inspect the affected stream; don't repeat the test blindly.

The experiment is implemented in `scripts/media/temporary_audio_test.py`; it is not a new permanent volume provider and does not mutate Team 6 policies.

## Pass/fail decision

- **If both tabs change together:** isolation **FAILS for this stream/path**. The stream appears shared or incorrectly targeted. Do not wire the Hi-Fi's music-only dial to it.
- **If only the target video changes and the other tab stays audible:** the result is *promising for this particular test*, but **not yet proof of general tab isolation**. We still need a verified tab-to-stream or native browser media-element association (including a test swapping which tab is selected).
- **If only the other tab changes, no audio changes, there are no candidate streams, or restore fails:** no isolation claim; inspect source/provider identity before proceeding.
- **If the MPRIS playback controls affect the wrong video:** playback selection isn't tab-specific, regardless of audio-stream testing.

## Next implementation seam

Use AppControl's existing AT-SPI/DevTools/Kitty tab discovery as **target identity evidence**, and its extracted `ApplicationAudioService` as **stream physiology**. Add a browser-native tab-level volume/capture provider only when capabilities/permissions are verified. Never silently fall back to browser-wide PipeWire mutations for the Hi-Fi's permanent music-only dial. This proof harness does not implement YouTube catalog search, playlist browsing, or a dedicated YouTube playback engine.
