# HI-FI // YouTube catalog adapter (v0)

**Status:** official Data API v3 discovery and playlist browsing only. This
feature does **not** play, download, extract, or stream any YouTube media.
No YouTube API key is stored in the repository.

## Capability boundary

The Hi-Fi source registry exposes:

- \`local-mpd\` for local MPD catalog and background playback.
- \`youtube\` for Data API search, playlist listing and video inspection.

Both sources return source-qualified references, but \`youtube\` currently
advertises **no compatible playback backend**. Calling \`load\` on a YouTube
video explicitly returns \`PLAYBACK_UNAVAILABLE\`; it does not try a browser,
MPD streaming URL, downloader or hidden media player.

YouTube's published policies prohibit using the YouTube embedded player for
background playback with its player window closed/minimized or extracting an
audio-only stream from video. The official player additionally imposes player
visibility and viewport requirements. Accordingly, a compliant official player
integration will need a visible player when playback is requested. We will not
silently violate this to make the prototype appear complete.

Official sources:
- https://developers.google.com/youtube/terms/developer-policies-guide
- https://developers.google.com/youtube/terms/required-minimum-functionality
- https://developers.google.com/youtube/v3/docs/search/list
- https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list

## Optional credentials

A YouTube Data API v3 key is required for actual catalog calls. Provision it
on the **operator's host environment**, not in GitHub or Quickshell logs:

\`\`\`sh
# Example syntax only; no actual key belongs in source or shell history.
# Set the secret privately for the media-controller user-service environment.
\`\`\`

The source reports unavailable if \`YOUTUBE_API_KEY\` is absent. Do not
configure YouTube discovery without operator approval; the existing local
source works without any network or credentials.

Once enabled, the controller exposes:

\`\`\`sh
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py sources
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py search "Of Monsters and Men" --source youtube
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py playlist "PLxxxxxxxxxx"
python3 ~/.config/quickshell/scripts/media/media_controller_cli.py inspect "AbCdEf12345" --source youtube
\`\`\`

\`playlist\` takes a real YouTube playlist ID, not a full URL. Each operation
returns \`nextCursor\` if a subsequent catalog page is available; pass it with
\`--cursor TOKEN\`. YouTube search quota usage and account/project restrictions
remain the key holder's responsibility.

The terminal API uses the same private JSON-lines Unix socket and error
envelope as local MPD. Examples:

\`\`\`json
{"version":1,"op":"search","args":{"source":"youtube","query":"music"}}
{"version":1,"op":"list","args":{"source":"youtube","collection":{"source":"youtube","kind":"playlist","id":"PL0123456789"}}}
{"version":1,"op":"load","args":{"ref":{"source":"youtube","kind":"video","id":"AbCdEf12345"}}}
\`\`\`

The first two requests browse only. The last returns
\`PLAYBACK_UNAVAILABLE\`, even when MPD is already playing local music.

## Verification

\`tests/media/test_youtube_catalog.py\` exercises a fake Data API transport;
no network access or real API key is required. All default MPD controller
regressions also continue to run. **Passing unit tests does not certify a
live YouTube integration.**

No Quickshell or PipeWire file is modified by this slice.
