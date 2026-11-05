# Social PHONE P12 // Real terminal bay, not a window behind the widget

> **STATE //** GitHub-only review candidate, not a live Fedora/Sway implementation acceptance.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation / staged PackageKit layout repair
> **STAFF //** External Hospital-compatible DOC; live Hospital Room/assignment registration not verified.
> **USER EVIDENCE //** November 5, 2026 screenshots: the oFono setup still opens a window underneath Social and that window cannot be used. The Social PHONE DEVICE panel is tall and mostly blank below a growing block of setup controls. Prior P11 PR #1296 merged but runtime deployment was not independently verified.

## IMPLEMENTATION

Found a concrete layout defect in the merged PHONE stage implementation: `stageHoleY` was calculated from `setupColumn.implicitHeight`. That height includes every visible PHONE setup section even when the QML `Flickable` content extends beyond the actual screen. As more calling settings and explanations were added, the requested terminal content rect could be below the Social window or too short to pass the stage-hole validation. The stage never reached the verified `ALIGNED` state, so Social kept painting an opaque surface and consumed mouse/keyboard input above the separately launched terminal.

**Fix:**

1. Reserve a lower PHONE terminal bay using only **actual `phoneChatFeed.height`**, `setupHeader.height`, and a bounded 43%-height upper workspace. Do not use scrolling `setupColumn.implicitHeight` for terminal coordinates. Keep the minimum exact compositor stage requirements (200×120, within the Social window).
2. While the terminal is requested, clamp the existing setup `Flickable` to the upper region and keep it scrollable. It must not paint its content on top of the lower terminal bay. The existing Weather Station cutout, Social `Intersection.Subtract` input mask, and exact post-Sway geometry verification remain unchanged.
3. Pin the existing **RETURN TO PHONE / CLOSE SETUP** control in the PHONE header while the stage is requested. This prevents the only recovery control from scrolling out of view. For PackageKit, Return simply detaches and never kills an active package transaction; the BlueFerry setup exit still uses its exact actor.
4. If the pane is physically too small for a real terminal bay, display an inline **enlarge Social panel** explanation **before** launching an oFono installer. A failed stage also reports `UNAVAILABLE` rather than getting stuck polling indefinitely.
5. Remove the installer's external package-manager fallback. If `foot`, `python3`, or `pkcon` is not available, or the foot launch fails, report a typed in-menu error instead of opening a graphical package window beneath Social. The staged exact-package PackageKit command, click-only trigger, user confirmation, and per-phone/no-default rules from P11 stay intact.
6. Continue to require the existing exact Sway window identity and visible geometry before opening the input/alpha cutout. **Do not** make arbitrary obscured external windows click-through or focus them speculatively.

The QML panel still looks like Social: same header, tabs, contact list/chat feed and magenta setup controls. This is a PHONE-only stage layout fix, not a new app/embed framework, root-level Sway rule or generic app shell integration.

## HOW TO USE

After owner review, operator-approved merge **and separately authorized deployment**, open **Social → PHONE → CONNECT PHONE → DEVICE → CALLS ON PC → SET UP CALLING**. If oFono is confirmed missing, the embedded `foot` PackageKit installation view should occupy the large lower section below the compact scrollable controls. Native PackageKit/Polkit approval remains required; Post-Apollo never silently installs the package. **RETURN TO PHONE** remains at top. After transaction completion/terminal exit, PHONE independently checks package and call-service status; successful GUI/terminal spawn does not prove oFono is installed or HFP works.

If the window is too small, the in-menu message asks the user to enlarge Social rather than opening an unusable window behind it. No terminal commands for ordinary users.

## VERIFY

- Extended `tests/messaging/test_social_phone_stage_terminal.py` to prove the terminal rectangle does not depend on scroll content; verify clipping above the bay, pinned return control, and representative 400, 580, 700, 950-pixel feed heights.
- Extended `tests/messaging/test_social_phone_calling_setup.py` for no installer launch when the bay is too small.
- Updated `tests/phone/test_phone_calling_setup_handoff.py` to reject an external installer fallback even when graphical package managers are installed or the staged terminal fails to spawn.
- Existing PHONE CI triggers already cover all modified source/tests, and the previous Stage Director unit tests still validate exact, scoped Sway window matching and no kill of active PackageKit transactions.

**No live Fedora terminal window, Quickshell mask, PackageKit prompt, input focus, package installation, Bluetooth connection, or HFP audio was tested by this worker.** CI cannot verify real Wayland screen coordinates or a live Polkit dialog.

## WATCH OUT FOR

- This correction is necessary but **not proof** the actual user desktop is running the newest merged code. The screenshots still show the old GNOME Software app-details error, although P11 source no longer launches `gnome-software`. That may be an old open Software window or an outdated live Quickshell installation. Verify the deployed commit before interpreting further screenshots. Do not reload Quickshell or alter a local worktree without separate explicit operator approval.
- A verified Sway content fit is still required to open the cutout. The exact actor may be externally visible if the compositor cannot position it; the UI reports unavailable instead of falsifying an input hole.
- User confirmation or a successful installer command does not mean working oFono service, D-Bus HFP access, WirePlumber routing, microphone/speaker capture or trusted message/contact access. Those are separate, owner-scoped tasks.
- **No local writes, package installations, audio changes, Bluetooth pairing resets, global default iPhone, production activation, or merge by this worker.** The native installer can change Fedora packages only following a future explicit user action in the deployed UI.
- Existing BlueFerry paired device and media routing remain untouched. No modifications to shared Social `MessagingW.qml`, Weather Station or global Stage Director.
- Return to PHONE **must not kill** an active PackageKit transaction. The existing P11 installer stage remains tagged separately from BlueFerry.

## CHECKLIST

- [x] Recheck Syntagma AGENTS and Hospital permissions, main, prior PR #1296 merged, concurrent PR list.
- [x] Trace the actual `stageHoleY` calculation and `setupColumn.implicitHeight` viewport overflow.
- [x] Reserve lower stage bay from visible feed geometry and scroll upper controls independently.
- [x] Pin Return to PHONE in the header; preserve safe PackageKit detachment.
- [x] Block installer launch on a too-small panel and remove external GUI fallback.
- [x] Add UI/launcher regression coverage and a durable recovery pointer.
- [ ] Verify exact-head CI, mergeability and no unexpected shared changes.
- [ ] Phone/Social and system-package owner review, operator-authorized merge.
- [ ] Authorized live Fedora/Quickshell deployed source and Sway geometry/input verification.
- [ ] Actual oFono installation approval, service status, HFP call and audio verification.
- [ ] Final operator acceptance.

## NEXT

Review CI and merge only with operator authority. After an authorized deployment, validate Sway `foot` positioning, terminal input, clipped upper scroll, and native PackageKit consent in PHONE. If not aligned, capture read-only Sway stage diagnostic evidence in the assigned runtime environment; **do not** circumvent the exact verified mask. Verify the user's deployed code matches this PR; old GNOME Software windows are not Stage Director clients.

## DECISIONS

Keep one inline installer and pinned return control. No external fallback when staging fails, no separate installer menu, no global OS fixups or root commands. Recovery: close the draft PR or revert the bounded changes if later merged. The operator has final authority and final acceptance.
