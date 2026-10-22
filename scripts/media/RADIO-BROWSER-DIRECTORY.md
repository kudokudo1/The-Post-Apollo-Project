# HI-FI // Radio Browser directory integration

**Status:** Development PR #458. No deployment or live MPD playback test yet.

## Purpose

Make the physical slider and tuning knob useful without downloaded local music.
Browse station directory listings, then deliberately SELECT, LOAD, and PLAY
a station using the existing controller and MPD backend. The directory
does not create or control a second player.

## How the first iteration works

- In the Hi-Fi control bay, press SOURCE until it reads **RADIO**.
- Press **SEARCH** with the field empty for a page of popular MP3 stations.
- To filter a station name, enter text (example: `ambient`).
- To search a genre, enter `tag:jazz` or `genre:downtempo`.
- To filter country code, enter `country:US`; language: `language:en`.
- Results are displayed above the controls (up to 50 filtered hits per page).
  The vertical slider and right TUNE knob navigate the current result page.
- **NEXT 50** fetches another page when the directory has more rows.
  The value is the NEXT PAGE button label, not a claim of exactly 50
  returned stations.
- SELECT chooses the highlighted source-qualified direct HTTPS stream.
  LOAD cues without autoplay; PLAY begins afterward. ENTER directly cues a
  highlighted station without autoplay. This retains distinct states.
- **PRESET** remains the existing operator-chosen Groove Salad station.
  Local MPD and YouTube catalog stay separate; YouTube remains catalog-only.

## Directory and filtering

Uses the free Radio Browser community directory API:

https://docs.radio-browser.info/

Requests go only to a fixed HTTPS directory hostname from the existing
persistent controller service. Queries fetch at most 150 rows with
`hidebroken=true`, `is_https=true`, and `codec=MP3`. We further filter
for the existing direct-stream validation: HTTPS, default port, no user info,
no query/fragment, no local/short/IP/restricted hosts, valid DNS-looking name,
no playlist extension, no repeated URL, name present and successful directory
health check. Display at most 50 rows and page in bounded 150-row offsets.

**No playable-station guarantee:** A directory's last check is not proof
that MPD can decode the stream now. Results can be fewer than 50. Stations
may be unavailable by geography, change URLs, disallow embedding,
redirect to other services, or require codecs/HTTPS URL forms outside this
first implementation's safe subset.

**Security boundary:** Directory data are untrusted. The existing URL-shape
validation does not resolve DNS or prove redirects stay public. No autoplay
or background probing occurs. A user must explicitly select/load a station.
Before enabling arbitrary directory-fed playback in a production configuration,
review network redirect/DNS egress restrictions and provider permissions.
If that review blocks, use browsing only until an approved playback route is
available. Never silently relax the MPD direct-stream validator.

## Runtime acceptance / recovery

After approved merge, first update the Python user controller service, then
use the normal controlled Quickshell restart; a QML-only reload cannot change
an already-running Python media controller registry.

Check popular radio results, genre, name and country queries, NEXT PAGE,
loading distinct station URLs, no autoplay, pause/play/stop, preserving a
currently loaded local item while searching, timeout/offline response,
and no regressions in ApolloHub MPD/MPRIS snapshots.

The branch has source and mock-network tests; a live Fedora/MPD/Radio Browser
station count and playlist playback are not verified.
