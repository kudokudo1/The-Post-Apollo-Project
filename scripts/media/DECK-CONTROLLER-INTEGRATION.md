# HI-FI // First deck-to-headless-controller integration

## Scope (first usable radio cassette)

- \`widgets/MediaDeckW.qml\` keeps MPD as its default, with MPRIS as an explicit
  external-player fallback.
- New \`services/media/HeadlessMediaController.qml\` is a thin UI client: it
  launches short-lived invocations of the versioned local CLI connected to the
  **existing** persistent Unix-socket service. It never starts/stops the MPD
  daemon or server, and it never changes audio routing.
- The display observes controller-loaded media, playback state and ownership.
- The cassette bay offers a single **operator-selected** Groove Salad stream
  button. It queues media without autoplay. The existing PLAY transport button
  then sends an explicit command to the controller.
- Transport no longer bypasses session checks through \`mpc\`. The UI disables
  live-radio seek/next/previous and disables pause/stop unless the controller
  reports ownership. The CLI/backend remain the final guard if state changes
  between a UI observation and a click.
- Polling runs only with the MPD deck open. Hiding the deck does not terminate
  the controller service, MPD, or playback.

The initial station URL is a direct MP3 stream the operator previously
confirmed played via MPD on Fedora; direct-server addresses can change.

## Runtime prerequisites

The operator has already linked/enabled
\`post-apollo-media-controller.service\`. This PR deliberately does not
install, enable, restart, or reconfigure that service.

After the operator safely updates the local working tree, a Quickshell
hot-reload/restart may be needed for QML to load the new source. Do not restart
a live shell without explicit local-operation approval. The next observation
must be made on the operator's desktop to confirm QML instantiation, sizing,
key interactions, command roundtrip and audio continuing after the deck closes.

## Acceptance exercise (on device, after safe reload)

1. Open Hi-Fi using the existing taskbar dock; confirm Hi-Fi/MPD mode and the
   radio cassette appear. Inspect the status/error text.
2. Click **LOAD / GROOVE SALAD**; confirm the loaded cassette and playback
   still stopped (unless unrelated external MPD playback was already active).
3. Click **PLAY**; verify audible music and controller-owned playback state.
4. Click **PAUSE** and **PLAY**, then close/reopen the Hi-Fi window; ensure
   playback isn't stopped by hiding UI.
5. Check that **STOP** affects only controller-owned playback. MPRIS remains
   explicitly separate.
6. Avoid interpreting an accepted command as proof of audio output; inspect
   actual MPD state if playback fails.

## Explicit exclusions

This is **not** a completed multi-source radio catalog, YouTube playback,
per-player volume, dedicated CAVA source, app-tab routing, or Team 6 service
update. No changes to shared \`shell.qml\`, \`modules/Mediaplayer.qml\`,
\`services/audio/ApplicationAudioService.qml\`, or PipeWire topology.

CI provides syntax/contract Python tests for the backend and source-level
Node guardrails for this QML bridge, not a live Quickshell rendering test.
