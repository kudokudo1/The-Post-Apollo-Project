# Weather StationW // TOOLS T1 final subject integration

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / TOOLS Subject Migration T1
ASSIGNMENT // Read-only source health/provenance/storage and safe original terminal handoff
PROVIDER // OpenAI / ChatGPT external Hospital-compatible worker
STATE // GitHub implementation until CI and merge; local runtime unchanged

## IMPLEMENTATION

The sixth Weather Station subject, TOOLS, now has eleven working QML
destinations under the exact canonical tree. No source, storage writer,
terminal process, provider request or settings store is created.

- TOOLS / OVERVIEW: Six live shared core product states and four
  read-only storage owner status/revision rows. Terminal entry is
  available in the sibling TERMINAL section.
- TERMINAL / STAR MAP: explicit OPEN CLASSIC STAR MAP BAY handoff to
  the original CLASSIC TERMINAL mode. The existing header STAR MAP
  button launches the sole Kitty instance. No process from this pane.
  TERMINAL / CONSOLES: OPEN CLASSIC HOME CONSOLE handoff to CLASSIC
  HOME, where the existing header HOME button launches a Bash console
  with the original app-id and exact window ownership. No new Sway
  geometry contract, terminal lifecycle, or duplicate Kitty actor.
- SOURCES / SOURCE HEALTH: six actual read-only service status rows
  for wttr weather, Open-Meteo AQI and four NOAA SWPC products, built
  using original StationSourceHealthPolicy. Space age comes from
  NOAA product sample timestamps; receive timestamps remain separate.
  No new polling or request retry.
- SOURCES / PROVENANCE: source-of-truth catalog from
  services/weather/WeatherRuntimePolicy.js, 37 source/view specs;
  each row shows label, owner, mode, cadence, retention, contract note.
  These do NOT represent 37 distinct pollers or asserted live uptime.
- STORAGE / SOURCE CACHE: existing WeatherPersistentCacheStore
  storageState, revision, and record count; this is last-good
  operational fallback, not event history.
- STORAGE / LIVE HISTORY: existing WeatherLiveHistoryStore state,
  revision, bounded series count; no chronology writer here.
- STORAGE / EVENT ARCHIVE: existing WeatherEventArchiveStore's
  read-only eventCount(), revision, status plus the independent
  WeatherDossierArchiveStore status/revision. Archive and dossier
  captures remain in the original EARTH investigation view and
  require explicit operator action.
- STORAGE / FRAME CACHE: three runtime retention specs (NOAA
  nowCOAST lightning, NOAA MRMS and RainViewer), clearly marked
  as temporary frame profiles, not a persistent archive of frames.
  No new Weather frame-cache database is invented.
- SETTINGS / LOCATION: read-only provider-resolved coordinates
  rounded to three decimals, and Open-Meteo AQ timezone when
  available. This is neither a GPS fix nor the NWS pinned alert-point.
- SETTINGS / UNITS AND DISPLAY: current Fahrenheit/MPH/US AQI and
  NOAA space units shown as read-only documentation. No new
  preference writer, location override, timezone editor or conversion
  engine is claimed.

The pane uses the existing GohuFont, magenta/cyan semantics, original
components and NeonScrollBar star indicator. Existing five working
subjects and CLASSIC remain untouched. In particular, terminal
cutout/Wayland session identity and WeatherStationW.launchContextTerminal
are NOT modified by this integration.

## HOW TO USE

Once GitHub is merged and local installation is separately approved:
Weather Station > SUBJECTS > TOOLS.
Select OVERVIEW, TERMINAL, DATA SOURCES, STORAGE or SETTINGS, then
a leaf route. SOURCE HEALTH reports live/aging/error statuses. SOURCE
PROVENANCE is an inventory, not live availability. STORAGE is only
readback; it does not provide save/delete controls.

For Star Map: TOOLS > TERMINAL > STAR MAP >
OPEN CLASSIC STAR MAP BAY, then use the existing header STAR MAP button.
For Bash: TOOLS > TERMINAL > CONSOLES >
OPEN CLASSIC HOME CONSOLE, then use header HOME to open its Bash
context console. Existing CLOSE still owns exact actor lifecycle.

## VERIFY

- Canonical Syntagma AGENTS.md and Hospital protocol rechecked.
- Latest main and open PRs/ownership reviewed before branch creation.
- T1 node tests cover all 11 leaf routes, source health age calculation,
  37 source specs, cache/history/event/dossier status, frame specs,
  accurate unavailable/readonly semantics, and terminal handoff.
- Prior M0/M1/WEATHER/COSMOS/EARTH/MEDIA/MAGICK contract tests in
  dedicated T1 workflow. Full Weather teardown must also pass.
- No local Fedora/Quickshell visual test or live provider fetch.

## WATCH OUT FOR

- The original terminal is a compositor-managed actor with a verified
  exact app-id, kitty geometry and close contract. Do not instantiate a
  second StationTerminal from TOOLS.
- Storage status is not permission to edit files. No record payloads
  or secrets are displayed.
- Provider/retention catalogue entries are definitions; source health
  reads only the six shared mounted core products, and none of the
  other 31 specs is misrepresented as actively online.
- One single persistent source cache serves last-good fallback while
  live-history and event/dossier archives remain separate writers.
- FRAME CACHE has *three* runtime retention specs, not a new disk
  archive. Retention labels are policy definitions, not measured
  current frame availability.
- Settings routes remain read-only by design. Location values come
  from the weather response and may be absent/stale.
- No local Fedora changes, service restarts, package installation or
  Sway/Kitty changes in this milestone.

## CHECKLIST

- [x] Protocol and latest GitHub state / role scope / ownership checked
- [x] Eleven TOOLS routes mapped to actual existing infrastructure
- [x] Terminal handoff guarded; no duplicate Kitty actor
- [x] Read-only six source state rows and 37 contract/provenance entries
- [x] Cache/history/event/dossier storage readback only
- [x] Frame retention, provider location and display conventions labeled
- [x] Focused test and CI workflow
- [ ] Final CI all green
- [ ] Merge into main (operator standing authorization)
- [ ] Local Fedora/Quickshell visual and operator acceptance

## NEXT

After CI verification, merge if safe. All six primary subject
families will then have real navigable workspaces. Separate future
assignments remain for in-station embedded video, real TOOL settings
editors, MAGICK calculations, and local Stage Director integration.
Do not imply the Weather Station is production-accepted simply because
these source/UI contracts pass.

## DECISIONS

TOOLS T1 is a read-only operational inspection and explicit handoff
surface. Reusing the existing processes, runtime policies and stores
is a design requirement. No live Hospital registration is claimed.
