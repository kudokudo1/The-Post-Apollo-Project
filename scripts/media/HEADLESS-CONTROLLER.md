# HI-FI // Headless universal controller prototype (v0)

**Status:** standalone implementation under review. Not wired into Quickshell,
not installed/enabled automatically, not live-hardware certified.

**Intent:** The Hi-Fi is the music hub. The panel must not need to stay open,
and a user should not be required to keep a browser tab open for *local MPD*
music. This is the first backend slice, not the completed streaming hub.

See [universal controller design](../../MODEL/contracts/media-controller-v0-draft.md)
and [media/audio identity boundary](../../MODEL/contracts/media-tab-audio-identity-v0.md).

## Real process anatomy

- \`media_controller_server.py\` runs independently of the Quickshell panel;
  it listens on \`$XDG_RUNTIME_DIR/post-apollo-media/controller.sock\`.
- \`media_controller.py\` keeps browse cursor/context, selection, loaded cassette
  and observed playback separate; it dispatches to registered source/backend adapters.
- \`headless_mpd.py\` contains two adapters: \`LocalMpdSource\` for the MPD
  music library and \`MpdBackend\` for actual playback and MPD queue.
- **MPD plays the music.** This controller only issues deliberate playback
  commands. Closing the panel, CLI or controller will not kill MPD or audio.
- \`media_controller_cli.py\` is an independent command-line client of exactly
  the same JSON-lines Unix socket that a future Quickshell adapter will use.
- This first slice retains browsing/selection/loaded state while the
  controller process is alive. MPD retains actual playlist/playback according
  to *MPD's* own configuration. Cold-start restoration now preserves selected and exact queue-verified loaded
  MPD refs, but never adopts ongoing playback ownership automatically. Browsing
  context remains process-local. Push subscription, permanent volume isolation,
  and player-only CAVA routing remain **unimplemented**.

## Run a temporary developer session (no machine installation)

Use the repo root if known, or the full path below, **after pulling the PR's
eventual merged changes**. MPD must already be running with a populated library.

In a terminal:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_server.py
\`\`\`

From another terminal:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py health
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py search "artist or song"
\`\`\`

The \`ref.id\` from search is an **MPD library file ID**, often a relative path.
Selecting and loading it do **not** play:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py select "Artist/Album/song.flac"
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py load
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py snapshot
\`\`\`

Explicitly start when ready:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py play
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py pause
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py seek -5
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py queue
\`\`\`

The \`queue-add "path"\` command appends without replacing loaded media or
triggering playback. \`load --autoplay\` deliberately combines load and play,
but plain \`load\` always has autoplay **off**.

### Persistent optional user service (do not enable without approval)

The repository contains \`ops/systemd/user/post-apollo-media-controller.service\`.
It assumes the Quickshell repo lives at \`~/.config/quickshell\`, as on the
operator's current Fedora installation. It is **not** installed by the PR and
must not be enabled automatically. The user can later approve linking/enabling
it with their existing systemd user control flow. \`systemd --user\` then
restarts the controller after a crash and launches it with the login session;
MPD is a separate service that must also be available.

## API v1

One UTF-8 JSON request line over user-owned Unix socket; one UTF-8 JSON result
line. Example:

\`\`\`json
{"version":1,"id":"hifi-1","op":"search","args":{"source":"local-mpd","query":"song"}}
\`\`\`

Result:

\`\`\`json
{"version":1,"id":"hifi-1","ok":true,"result":{"browse":{"source":"local-mpd","query":"song","items":[],"truncated":false,"totalObserved":0}},"error":null,"generation":1}
\`\`\`

All failed calls use \`ok:false\` and an explicit \`error:{code,reason}\`;
unknown sources/operations never silently map to a different player.

Supported commands:
\`health\`, \`sources\`, \`snapshot\`, \`search\`, \`inspect\`,
\`select\`, \`load\` (\`autoplay:false\` default), \`queue\`,
\`queue_add\`, \`queue_remove\`, \`play\`, \`pause\`, \`stop\`, \`next\`,
\`previous\`, \`seek_relative\`.

Track references are source-qualified:
\`{"source":"local-mpd","kind":"track","id":"MPD-relative-file"}\`.
A browse highlight is *not* loaded media. \`load\` performs a true MPD \`addid\`
without autoplay. \`play\` uses the exact queued \`playid\`, not "play the first
available song." Playback observation comes back from actual MPD status.
Commands requiring owned playback reject a session changed by an external MPD
client rather than accidentally affecting it.

The controller socket is created under a private 0700 runtime directory with
0600 socket permissions. It refuses non-socket / symlink paths. No \`/tmp\`
fallback; no remote HTTP API. It does **not** implement desktop or per-tab
audio volume. No YouTube playback or downloads are performed.

## Verification / handoff

CI runs \`python3 -m unittest discover -s tests/media -p
'test_headless_controller.py' -v\` against a fake MPD backend plus real
temporary Unix/TCP socket fixtures. It never requires audio hardware.
The acceptance barrier is then an explicit operator-approved live MPD trial
and future Quickshell consumer integration, **not** immediate shell changes.

The next work phase is controller-state recovery/subscription and an authorized
Hi-Fi/QML adapter. Streaming catalogs are separately capability-gated and must
respect provider rules and approved playback methods.

## v0.2 // Durable intent recovery (source-only, awaiting real MPD trial)

When the optional user service eventually runs, the controller saves **only**
selected media reference and loaded MPD queue ID/reference under
`$XDG_STATE_HOME/post-apollo-media/controller-intent-v1.json` (defaulting to
`~/.local/state/post-apollo-media/`). The file and dedicated directory are
private, and writes replace a temporary file atomically. It does **not** save
catalog queries, API keys, or audio output policies.

On restart it reads that intent, checks that MPD still has exactly the saved
queue ID **and** matching media URI, and restores the cassette label if so.
It does **not** call `play` during startup or claim control of MPD's
pre-existing playing song. An explicit new `play` command reasserts ownership.
If the queue changed, the loaded cassette is left empty. If MPD is unavailable,
no stale loaded track is reinstated. During normal operation, every new `play`
revalidates queue ID plus URI before invoking MPD.

A filesystem failure after a successful MPD queue mutation must not be reported
as if the MPD command itself failed. `snapshot.persistence.error` exposes a
non-secret diagnostic instead. Tests cover stale IDs, changed media, symlinks,
private file permissions, offline MPD and no playback takeover. This is not
an installed service: it takes effect only after explicit user-service setup.
