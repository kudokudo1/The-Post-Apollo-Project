# HI-FI // Guarded Radio Browser playback draft

**State:** draft PR under review. No live Fedora, MPD or Quickshell activation.
This extends the merged radio-directory browsing work from PR #458.

## User workflow

1. In Hi-Fi, set SOURCE to **RADIO** and SEARCH with an empty query, or
   \`tag:jazz\`, \`country:US\` or a station name.
2. Navigate the returned station UUIDs using the slider and TUNE encoder.
3. Press **SELECT** on one result. This stages it but does not load anything.
4. Press **LOAD** to queue the selected radio station through the controller's
   guarded localhost relay. Or press **ENTER** to queue the highlighted station
   without staging first. **Neither LOAD nor ENTER autoplays.**
5. Press **PLAY** to switch to the exact loaded station's MPD queue ID.
6. To switch again, SELECT/LOAD/PLAY another station. LOAD does not interrupt
   currently playing audio. PRESET and local MPD remain separate sources.

The upper display and cassette bay show the loaded station title, distinct
from the currently highlighted search result. Quickshell never receives
or directly opens arbitrary directory stream URLs.

## Transport and security boundary

Radio Browser catalog search uses fixed HTTPS directory hosts and still
rejects invalid, broken, unsupported or playlist-style results. Returned
results have \`{source:"radio-browser",kind:"station",id:UUID}\` refs. Their
candidate direct MP3 URLs remain private in the existing Python media
controller and are scoped to the active search batch.

An explicit LOAD starts a session-owned \`RadioStreamRelay\` lazily in the
existing controller service. The relay binds to IPv4 localhost on a random
port, registers an unguessable 256-bit token for the selected station and
returns \`http://127.0.0.1:PORT/radio/TOKEN\` to MPD. The backend rejects
unregistered relay URLs. The relay never runs on SEARCH or UI open.

The outbound fetch accepts only direct HTTPS MP3 URLs. It resolves the
hostname, rejects **every** DNS response set containing a private, reserved,
loopback or otherwise non-global IP, and connects to a pinned numeric public
IP. TLS SNI and certificate verification use the original hostname, preventing
the usual DNS-validation/re-resolution race. HTTP redirects are refused,
response must be HTTP 200 with MP3 Content-Type, and tokens expire after
12 hours. At most two concurrent audio streams and 32 outstanding tokens
are supported. No playlist fetch, subprocess player, Quickshell audio worker,
or disk cache is introduced.

The controller preserves source-qualified station identity, MPD queue ID and
the relay URI for queue ownership verification. Only selection survives the
controller restart; temporary radio relay URLs do not. A service restart
requires another explicit LOAD and PLAY to listen again. MPD transport
continues to require verified queue ownership. MPRIS remains independent.

**Limitations:** This is not a complete OS network sandbox, does not prove
broadcaster licensing, and trusts Python TLS and MPD's audio decoder.
Stations requiring HTTP, redirects, AAC/OGG, playlists, ICY-only responses,
query-string tokens or nonstandard ports can still fail. Directory health
checks do not prove MPD audio output. No automatic fallbacks that bypass
validation are allowed.

## Verification and rollout

Offline tests cover URL and DNS validation, redirect and MIME rejection,
the opaque localhost handler, MPD cue capability checks, SELECT/LOAD/PLAY
separation, multi-station switching, tampered queue IDs and ownership,
and the preserved browse-only behavior when no relay is registered.

Before merge, review the added service-owned stream relay, its network scope,
and any applicable broadcaster requirements. A green CI run does not replace
operator approval for service activation. After approved merge, the operator
updates local files, restarts the existing media-controller service, uses the
normal controlled Quickshell reload and tests two working public radio streams.

If any playback failure, keep the original PRESET as a fallback and do not
weaken the guards without a separate decision.
