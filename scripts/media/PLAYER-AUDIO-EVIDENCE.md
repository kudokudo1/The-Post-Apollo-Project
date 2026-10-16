# HI-FI // Player-only audio readiness probe

**Status:** read-only evidence, not routing, playback or volume support.

Use this after local MPD is available and the controller is running:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py audio-evidence
\`\`\`

The controller queries:
1. MPD's \`outputs\` operation: names, enabled flags and backend plugins.
2. \`pactl -f json list sink-inputs\`: the already exposed live audio streams.

It reports candidate sink-inputs that explicitly advertise
\`application.process.binary == mpd\`, alongside stream index, PID, sink,
mute and media name. It does not call \`pactl set-*\`, switch an output,
create a monitor, alter the MPD config, or start/stop playback.

Important limitations:
- MPD's configured outputs and PipeWire streams are distinct layers.
- An MPD-looking stream may be shared among multiple sources or disappear.
- One observed MPD stream is **not** proof of dedicated route ownership.
- A PipeWire sink-input is not necessarily a unique monitor source for CAVA.
- Therefore \`isolated\`, \`playerVolumeAvailable\`, and
  \`playerCavaAvailable\` remain **false** regardless of candidate count.
- Desktop CAVA currently visualizes the combined default output and stays
  unchanged.

This deliberately respects Team 6's ownership of shared audio physiology.
The next implementation is a separately verified MPD-only output route and
CAVA monitor with an unambiguous lifetime/cleanup policy, not a guess based
on a PID.

No live-mixer or output mutation is authorized by this diagnostic.
The tests use faked MPD outputs and PipeWire input data and never change
running user audio.
