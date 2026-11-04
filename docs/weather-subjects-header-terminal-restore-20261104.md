# 🏥💜 Weather Station // SUBJECTS header terminal restoration

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Weather SUBJECTS / existing Kitty terminal control
ASSIGNMENT // Replace disabled CLOSE placeholder in original top-right slot with reusable TERMINAL/CLOSE action
ROLE // External DOC / Hospital-compatible, not confirmed live-registered
BASE // `main` `6903391b26e47550d302c1b676ccbb05b36401c7`
SCOPE // Header action and bounded terminal-routing regression tests only

## IMPLEMENTATION

The original `WeatherStationW.qml` root `StationTerminal` remains mounted exactly once under SUBJECTS-only mode, and the existing header `contextTerminalClose` is the unavailable `CLOSE` placeholder when no Kitty actor exists. The new header button reuses that slot before the same divider. With a valid Quickshell output and no active session, it says **TERMINAL** (cyan), is clickable, and calls `launchHeaderTerminal()`. When terminal activation is pending or `terminalView.terminalState !== "IDLE"`, the SAME button says **CLOSE** (red) and calls existing `closeContextTerminal()`.

`launchHeaderTerminal()` first verifies the station, SUBJECTS state, no active terminal, and a real output name. It routes through `subjectNavigator.chooseRoute("tools/terminal/star-map")` and then calls the already-guarded `launchSubjectTerminal("terminal")`. That call performs the one deferred `StationTerminal.openTerminal()` after mode/visibility settle, with route and session validation. Invalid route, closed station, unavailable output, or existing actor fail closed. Close restores the terminal-less SUBJECTS TOOLS route. INDEX remains separate. No CLASSIC mode, new process wrapper or second terminal was introduced.

Button width is **88px**, kept in the former CLOSE slot before `terminalHeaderDivider`. Its right edge remains at the old slot's right edge; the longer label is readable. The header background, source status, and 1000×700 chassis dimensions are unchanged.

## HOW TO USE

Weather Station → any SUBJECTS page → top-right **TERMINAL** (beside INDEX and left of the cyan divider) → existing Kitty STAR MAP in the masked terminal bay. When active, press **CLOSE** in that exact slot to close the session and return to SUBJECTS / TOOLS. The previous TOOLS → TERMINAL → STAR MAP / CONSOLES controls remain available and unchanged.

No new settings or separate browser are required. This repository change alone does not update or restart the operator's live Quickshell tree; it must be synced/deployed under separate live-state approval.

## VERIFY

- [x] Inspect canonical Syntagma rules, latest main, active PR ownership
- [x] Verify CLASSIC retirement PR #1195 was merged before working
- [x] Confirm only one `StationTerminal` controller and existing top-right inactive CLOSE slot
- [x] Add direct header-to-TOOLS STAR MAP routing with existing single actor and deferred safety guard
- [x] Extend tests for launch from non-TOOLS pages, INDEX, denied output/route, duplicate calls, stale deferred route, label/slot/color state
- [ ] Exact-head Node/Qt/Quickshell CI and merge evidence
- [ ] User Fedora/Sway live visual, pointer, Kitty, masking and close acceptance

## WATCH OUT FOR

The terminal launches the existing operator-specific Kitty `weatherstation-starmap` command and existing Sway mask path. This PR neither installs that executable nor proves it is present on a new device. When `targetScreen.name` is absent, TERMINAL stays unavailable rather than launching onto an unverified output. Launching from any SUBJECTS page intentionally selects TOOLS → STAR MAP, so after CLOSE the TOOLS STAR MAP route remains visible.

A native no-actor test is not proof of the actual operator screen click, compositor geometry or Kitty launch. Avoid using CI to spawn a nonisolated desktop Kitty process. The previous Weather worker's CLASSIC retirement is already merged; no parallel Weather-owned PR was open at base inspection.

## CHECKLIST

- [x] Preserve existing INDEX header control and divider
- [x] Restore TERMINAL action in exact unused CLOSE slot
- [x] Retain dynamic CLOSE while session exists
- [x] Preserve one native Kitty/Sway controller, matching app ID and terminal bay/cutout
- [x] Add targeted refusal and routing tests
- [ ] Green CI, bounded merge, exact master verification
- [ ] Real desktop acceptance by operator

## NEXT

Validate the branch's GitHub checks, repair issues, merge if exact head is green under user authorization, then give operator UI instructions to verify live after their workstation sync. Continue Stage Director Qt/QML paired-WATCH integration separately; this terminal header restoration is not SwayPX browser/NEWS activation.

## DECISIONS

SUBJECTS is canonical; CLASSIC stays retired. Reuse the one original root terminal. Idle TERMINAL and active CLOSE share one top-right slot, colored cyan/red respectively. Avoid browser/QtWebEngine or extra actors. Repository-only edits were authorized, local writes/reloads not attempted. Final acceptance remains with operator.
