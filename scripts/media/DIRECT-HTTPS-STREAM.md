# HI-FI // Direct HTTPS audio stream source

**Status:** first source for background network-audio playback, independent of
browser tabs and an MPD music library. This is not YouTube playback, music
search, arbitrary media downloading, or certified PipeWire stream isolation.

## Operation

The \`direct-stream\` adapter takes a manually supplied HTTPS direct audio
stream endpoint, validates it as an explicitly chosen public-looking target,
and routes it to MPD as \`mpd-https-stream\`. MPD handles actual downloading
and decoding while the headless controller retains loaded-media state.

- \`inspect\`: validates and describes the URL without opening a connection.
- \`select\`: records a selected source-qualified live-stream reference.
- \`load\`: adds the stream to MPD's queue with \`addid\`. It does **not** play.
- \`play\`: starts the exact queued ID using \`playid\`.
- \`pause\`/\`stop\`: require controller-owned playback. A changed MPD queue
  item fails closed.
- \`queue\`: shows direct HTTPS streams as \`direct-stream\` references, not
  local files. After service restart, saved queue ID and exact URL are checked
  before restoring the *loaded* cassette. Ongoing playback is never adopted.

Local \`mpc listall\` and \`mpc stats\` can show zero tracks and this source
can still work, since it does not rely on the MPD music database.

## Initial operator live test

After Git Control **PULL FF**, restart the separately enabled user service
to load the new Python source without reopening Quickshell:

\`\`\`sh
systemctl --user restart post-apollo-media-controller.service
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py sources
\`\`\`

A real broadcaster publishing MP3 direct stream links is SomaFM. For example,
its Groove Salad station presently advertises the following **direct MP3**
endpoint for individual/personal listening:

\`\`\`text
https://ice5.somafm.com/groovesalad-128-mp3
\`\`\`

SomaFM warns that direct-server URLs change and recommends its playlist links
for greater stability. Use official current links at:

https://somafm.com/groovesalad/directstreamlinks.html

Load without autoplay:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py \
  load --source direct-stream --uri "https://ice5.somafm.com/groovesalad-128-mp3"
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py snapshot
\`\`\`

Only the next explicit command starts playback:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py play
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py audio-evidence
\`\`\`

To stop:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py stop
\`\`\`

MPD must have outbound internet connectivity and a compatible decoder;
HTTP errors, unavailable streams and codecs are runtime observations, not
guarantees from unit tests. The controller process can remain online even
if playback fails, and the Hi-Fi panel may remain closed.

## Limits and safety

The source accepts explicit HTTPS URLs at the normal HTTPS port with a
normal public DNS hostname. It refuses local hostnames, IP literals,
credentials, query tokens, nonstandard ports, control characters, common
video/streaming platform pages and unsupported URL schemes. It does **not**
resolve DNS, follow redirects itself or guarantee that a hostname cannot
resolve to a private address. **Never automatically import untrusted remote
catalog references as direct-stream URLs** without a separate network-policy
review. Input in this phase is operator-supplied only.

No audio stream routing, Team 6 service, CAVA monitor, YouTube playback
authorization, or Quickshell surface is modified by this change.
