# Weather Station // M28-V Classic root retirement

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station CLASSIC → SUBJECTS  
STAFF ROLE // External Hospital-compatible recovery worker; no verified live registration  
SOURCE BASE // `main` at `86483b95037099484e27bc37d177a3589dd0d290`  
STATE // Isolated GitHub implementation; desktop not updated; operator acceptance pending

## IMPLEMENTATION

M28-V removes *Classic-only presentation code* in `WeatherStationW.qml`: the eight-button `railColumn`, CLASSIC/SUBJECTS toggle, original separate `weatherContentLoader` and seven obsolete root `Component` declarations, legacy keyboard cursor, old NEWS → MAP bridge, Classic fallback and `currentView` branches. It also removes dead INDEX Classic buttons and relay signals while retaining the M0 103-control provenance and native links.

The persistent actual component engines `StationHome`, `StationGround`, `StationSky`, `StationSpace`, `StationDiscovery`, `StationNewsHub`, `StationRadio` and `StationTerminal` **remain** in Subjects and are not deleted. Root weather/service owner count stays one. No changes to stored favorites, location caches, history, archives, MPD, feed fetchers or video execution.

The old shell Weather notification `view` tokens now resolve into native routes via `openNotificationView()`. `sky` enters **WEATHER → NOW + AIR**, since the former mixed SKY was deliberately separated into terrestrial and astronomical domains by M28-R; `terminal` selects TOOLS → STAR MAP without autoplay.

## HOW TO USE

After separate, authorized workstation deployment, open Weather Station to HOME. Use left family rail, bottom page row and INDEX to navigate. There is no Classic switch. Test `HOME`, `WEATHER` GROUND/NOW+AIR/FORECAST, `COSMOS` ASTRONOMY/SPACE // ALL, `EARTH` MAP // ALL, `MEDIA` NEWS/RADIO // ALL, `MAGICK`, `TOOLS` source/storage and terminal. Test Escape, Tab, close/reopen, notification deep links, Kitty close and map wheel/drag.

## VERIFY

Source tests assert 103/103 old control IDs retain native routes, root has one service owner each, one Kitty actor and input-mask geometry, and shell notifications are no longer routed to CLASSIC. GitHub CI and actual Fedora desktop runtime must be verified separately.

## WATCH OUT FOR

- This is an intentional one-way UI source cleanup. **Rollback:** restore the prior `main` commit `86483b95037099484e27bc37d177a3589dd0d290` in a new GitHub branch/PR if parity fails; do not reset a user's local desktop.
- The old terminal app-ID modes remain valid in `StationTerminal.qml` because existing contexts and Sway identity depend on them. They are **not** Classic UI.
- M0 source provenance and historical milestone docs remain historical, not executable Classic fallback.
- Stage Director's unsafe embedded video remains disabled. This cleanup does not authorize video playback or production activation.

## CHECKLIST

- [x] Recheck Syntagma and current main, prior M28-U and open PR ownership
- [x] Replace root Classic presentation and notification navigation
- [x] Preserve single data source, terminal and persistence ownership
- [ ] Exact-head CI and regression tests all pass
- [ ] Operator separately authorizes local update and performs workstation acceptance
- [ ] After acceptance begin SUBJECTS information architecture and visual improvements

## NEXT

Do not reorganize buckets or graphics in this PR. After source cutover and live verification, review the HOME/WEATHER/COSMOS/EARTH/MEDIA/MAGICK/TOOLS information hierarchy and redesign clickable surfaces, circular instruments and high-density panels without changing underlying service owners.

## DECISIONS

Operator's sequence remains migrate, verify, retire Classic, then reorganize Subjects. No local-machine file writes, Quickshell reloads, merges, or production activation have been performed.
