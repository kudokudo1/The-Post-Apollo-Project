# 🏥 Company Network M13 // Controlled Vector Sidecar Launcher

**Patient:** kudokudo1/The-Post-Apollo-Project  
**Room:** Company Network vector renderer integration  
**Role:** External Hospital-compatible Nurse 2, no live Hospital registration claimed  
**Assignment:** Provide explicit open/close in Company Coverage while preserving its existing map  
**Scope:** Company Coverage QML, standalone launcher helper, synthetic unit tests  
**Status:** Repository implementation; native Fedora/Quickshell acceptance outstanding

## IMPLEMENTATION

The integrated Qt MapLibre v3 app is still a separate process. M12 PR #1275 is merged but its final native CI capture was in progress at this milestone's preflight; inspect that test independently. M13 adds only a **controlled launcher surface**. It does not install the renderer, change Quickshell's renderer, add data or replace Company Coverage maps.

- Inside **Company → Coverage**, a \`VECTOR VIEW ▸\` action opens an explicit consent sheet. It describes the separate Qt window, that it may not be installed, and the distinction between synthetic offline geography and online OpenFreeMap tiles.
- \`OFFLINE TEST\` starts the fixed-path native binary **without any online flag or Company data import**.
- \`ONLINE STREETS\` starts the same app with \`--styled-online\`, only after an independent click and disclosure that the viewed map area and IP are sent to OpenFreeMap. No hub names, worker, client or company records are submitted. No current Company map selection is passed to the sidecar.
- While the native child is tracked, the control becomes \`CLOSE VECTOR\`. Quickshell \`Process.running=false\` sends SIGTERM; the wrapper uses \`os.execv\` to become the native process, not a detached orphan. Hiding Company Coverage also stops the attached child.
- New \`services/company/CompanyVectorSidecarLaunch.py\` is a *fixed-path* process boundary. It finds only the normal-user-owned executable at \`~/.local/libexec/post-apollo/company-vector-probe\` and refuses symlinks, group/world writable entries, setuid/root access and arbitrary arguments. It never downloads/builds/installs. If the binary doesn't exist, a truthful \`NOT INSTALLED\` status is returned.
- The existing Natural Earth reference map, Street raster mode, consent surface and hub editor remain unchanged.
- No real \`CompanyHubMapReadOnly.py\` projection is invoked by this launcher, and no \`--owner-local-hubs\` option is accepted.

## HOW TO USE

**After the next authorized local installation/desktop test,** open the Company module on the taskbar → **COVERAGE** → **VECTOR VIEW ▸**, then choose **OFFLINE TEST** or **ONLINE STREETS**. The button becomes **CLOSE VECTOR** while the child is running. Close Company Coverage to terminate the child and restore normal navigation.

**Today:** the native binary is **not yet verified installed** on the user's Fedora machine. Without an approved installation, the control reports **NOT INSTALLED**. The old map is still available and remains the default.

Do **not** install by copying the GitHub Actions binary: native Qt, plugin, library and ICU versions must match Fedora and the host Quickshell environment. An isolated test install with a fixed-path binary/Qt library bundle is a separate task requiring operator approval.

## VERIFY

CI tests a fake executable under a disposable temporary home and asserts the only possible execution flags are empty (offline) and \`--styled-online\` (online); ensures no real Company directory/identity/record access, shell execution, arbitrary executable path, detached launches or background persistence. Also tests symlink and permissions refusal and preservation of the existing Company map.

Runtime integration, focus, responsiveness, map-window geometry, child exit and local Quickshell/SwayPX behavior must still be tested interactively on the operator's desktop. Source checks do not prove live functionality.

## WATCH OUT FOR

- **Installation is separate.** A launch button in code does not conjure a compiled native Qt/MapLibre installation onto Fedora.
- A dedicated Qt window is **not embedded** inside the Company widget. Embedded clipping, resizing, input delegation and a single in-widget vector map will need Stage Director/SwayPX and different authorized work.
- Online map requests disclose visible public map regions and IP to the tile provider; no auto-center-to-hub behavior is permitted. M12 owner-local mode must not be enabled via this button.
- No verified organization account, authorization grant, employee/client access, or business service eligibility is inferred from the map.
- Quickshell owns the attached child only while its Process remains tracked. A forced host crash may require ordinary operating-system process cleanup; this is not a daemon manager.
- The current UI signals STARTED when the subprocess begins. This **does not** mean a Qt window rendered successfully.

## CHECKLIST

- [x] Reuse existing Coverage modes and colors
- [x] Explicit online disclosure and offline option
- [x] Fixed, owner-only executable and no arbitrary args
- [x] Tracked process start/stop and fallback
- [x] Synthetic security/interaction checks
- [ ] CI M13 tests passing
- [ ] Native M12 result reviewed
- [ ] Approved Fedora native Qt dependency bundle installed
- [ ] Operator verifies launch/close, focus, and performance
- [ ] Sidecar integration or in-widget replacement explicitly accepted

## NEXT

Inspect CI M13 and M12 native render evidence. If green, test a **separate** reversible Fedora Silverblue user-local installation, examine SwayPX window/parent/input and Qt plugin discovery, then measure real pan/zoom frame pacing. Do not mutate the local machine without an approval specific to that installation.

## DECISIONS

Retain the old map and Company widget. The new button is an opt-in sidecar launcher only, not a complete geographic renderer migration or a new organization permission model.
