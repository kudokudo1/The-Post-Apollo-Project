# Weather StationW // MAGICK Normal-Launcher Auto-Discovery Fix

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backend
ASSIGNMENT // Make existing JPL/Skyfield installation available through ordinary Quickshell startup without injected environment variables
ROLE // External Hospital-compatible development worker; no verified live Hospital registration
PERMISSIONS // GitHub-only bounded fix; no user-local writes, shell changes, launcher edits, restarts or production activation
BASE // main at 2e64bed87acfc4c3afd3a97fe2e1f7ffa40e6306, after M5c
BRANCH // fix/weather-magick-auto-discovery-20261103
PHASE // Draft code / CI verification and operator acceptance pending

## IMPLEMENTATION

Observed operator behavior: MAGICK's zodiac wheel displays calculated data only when Quickshell is started from a special terminal command setting POST_APOLLO_CELESTIAL_KERNEL and POST_APOLLO_CELESTIAL_PYTHON. When launched normally, Quickshell lacks these environment variables, CelestialVisualService.configured is false, and the existing CALCULATE ActionButton is disabled even though the backend has been installed once.

The existing installation instructions use:

- $HOME/.local/share/post-apollo/magick/de440s.bsp
- $HOME/.local/share/post-apollo/magick/venv/bin/python

New `services/weather/CelestialVisualInstallPolicy.js` provides a pure path resolver: if the appropriate explicit environment override is nonempty, use it; otherwise derive the canonical home-local path. This avoids requiring launcher changes and keeps developer-specific overrides. `services/weather/CelestialVisualService.qml` now reads the inherited HOME environment variable and passes it through this resolver.

This change only resolves candidate paths. It does **not** assert that files exist, install Skyfield, fetch ephemerides, create directories, start a second process or enable automatic calculation. The existing one-click CALCULATE flow, M4 data validation, single process owner, result-gating and failure messages remain intact. If the installation does not exist, a CALCULATE attempt may show an error. That limitation is intentional until the separate production Backend Manager provides installation-state probing and provisioning.

No changes to WeatherStationW root ownership, SUBJECTS/MAGICK layout, COSMOS sources, weather provider diagnostics work, Stage Director, CPU++ settings, CLASSIC migration, personal journals, or the live Fedora system.

## HOW TO USE

Once this change is merged and deployed through the operator's normal local update process, launch Quickshell **normally** using the existing launcher. Open:

    SUBJECTS -> MAGICK -> ASTROLOGY -> CALCULATE

The original locally installed kernel and virtual environment will be used without requiring a specially prefixed Quickshell command.

Optional advanced overrides continue to work:

    POST_APOLLO_CELESTIAL_KERNEL=/absolute/path/to/other.bsp
    POST_APOLLO_CELESTIAL_PYTHON=/absolute/path/to/python

No installation or action is required from the operator while reviewing this GitHub-only PR, and a merge by itself does not update an already-running local Quickshell instance.

## VERIFY

Dedicated GitHub workflow and Node tests cover:

- Ordinary startup with HOME=/var/home/mapple and no POST_APOLLO_CELESTIAL_* overrides resolves the expected kernel and venv interpreter paths.
- Explicit override precedence, independently for each setting.
- Unknown, relative or malformed HOME does not fabricate a kernel path.
- Root still owns one CelestialVisualService; no extra Process, timer, downloads or local file writes.
- Prior M5a/M5b/M5c button and visual contracts, and W2a HOME navigation protection.

Initial local observation from the user screenshot: the M5b wheel works in Quickshell when the old environment-injected launch is used. The new ordinary-startup fallback has not yet been exercised in the operator's Quickshell runtime and must not be called live-verified from GitHub tests alone.

## WATCH OUT FOR

- The fallback root exactly matches the one-time developer installation path documented in previous tasks, not an arbitrary global search. If the operator installed files elsewhere, the explicit override remains necessary until a future Settings++ Backend Manager can store the chosen installation path.
- The policy cannot verify that a candidate path exists without a separate safe file-existence mechanism. Thus configured means usable-looking paths are known, not a successful installation check. Errors must remain truthful.
- No automatic package installation or JPL download for fresh end-user devices is provided here. That is a separate product milestone.
- An already-running Quickshell process will not acquire new GitHub code until the operator-approved deployment/restart. Do not kill, duplicate or restart the user's live Station without authorization.
- Because only service/policy/tests/workflow are touched, open SUBJECTS migration PR #1150 remains independently owned.
- This does not change the scientific precision, limitations or interpretation status of MAGICK; source-backed astronomical data is still required to draw.

## CHECKLIST

- [x] Confirmed root cause in current GitHub source and one-time install location
- [x] Read-only current main and concurrent work preflight
- [x] Isolated default-path resolver and root service integration
- [x] Preserve environment overrides and manual calculation semantics
- [x] Unit/contract tests and CI workflow
- [ ] PR-head CI green after handoff commit
- [ ] Operator acceptance and authorized merge
- [ ] Ordinary launcher Quickshell runtime verification on operator system
- [ ] Future automatic dependency provisioning through separate Backend Manager

## NEXT

After CI and review, merge only with operator authorization. The operator can use the existing launcher after a separately approved local code update. Verify CALCULATE is enabled, produces source-stamped data, and still fails clearly when required files are missing. Then continue M5d visualization work and the distinct Settings++ MAGICK Backend Manager plan.

## DECISIONS

This is a small compatibility fix for already-installed users. Full automatic first-time setup, installer UI and filesystem detection remain future scoped work. No local files/processes were changed here.
