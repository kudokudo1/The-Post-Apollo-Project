# Social PHONE P11 // Embedded PackageKit installer instead of broken Software app-details

> **STATE //** GitHub-only integration pilot. No live Fedora package installation, transaction, terminal launch, Quickshell reload, or HFP activation performed by the worker.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation, install-in-feed fix
> **STAFF //** External Hospital-compatible DOC, no verified live Room/Session registration.
> **OPERATOR EVIDENCE //** Screenshot Nov 5, 2026: Social PHONE's SET UP CALLING launched GNOME Software, which displayed “Unable to Show App Details” and failed to retrieve information for `ofono`. Operator requested the installer inside PHONE's large lower panel, as already achieved for the BlueFerry terminal, or like staged X applications.

## IMPLEMENTATION

The GNOME Software `--details-pkg=ofono` route depends on catalog/app details and has **failed on the user's system**. `ofono` is a system RPM rather than an ordinary desktop app. This pilot replaces that route rather than retrying a broken view:

1. After the existing **explicit SET UP CALLING** click and a fresh, read-only prerequisite check confirming both the `ofono` package and its system unit are missing, `PhoneCallingSetupHandoff.py` prefers installed `foot`, `python3`, and PackageKit `pkcon`. It launches an exact argv into a dedicated window tagged `post-apollo-social-phone-ofono`. The only permitted package is `ofono`. No shell, arbitrary package, `-y`, auto-approval, root terminal, or installation on widget open.
2. `PhoneOfonoInstallSession.py --interactive-ofono` checks it has an interactive terminal, displays the fixed package and scope, then runs `pkcon install ofono` **without noninteractive confirmation**. PackageKit shows its transaction and normal confirmation/Polkit authorization. The script holds the terminal after completion/failure so the user can read the result and presses Enter to close. `pkcon` returning success is not sufficient to mark oFono installed; existing read-only RPM/service checks must confirm.
3. The existing `PhoneStageDirector.py` now supports `--sync-installer` with the exact distinct app-id. It matches only a unique, visible `foot` Sway actor with matching executable PID and verified geometry inside the Social window, then moves/resizes **only that actor**. The PHONE cutout opens for input only after a subsequent exact Sway content-rect observation. The BlueFerry stage ID is unchanged. Installer `close` is **not supported** at the compositor boundary.
4. `PhonePane.qml` keeps one contextual setup button, the same contact/feed layout, and existing device/call/media controls. A staged installer uses the same verified terminal bay as BlueFerry without a new permanent menu or general X embedding framework. When the installer exits, PHONE rechecks package and BlueFerry audio status. The stage control says **RETURN TO PHONE**, not destructive CLOSE SETUP. Leaving PHONE **never kills** an in-flight package transaction. The Sway window may remain floating externally if the user navigates away while the transaction runs.
5. If foot/PackageKit cannot be launched, a supported `gpk-install-package-name ofono` graphical PackageKit client remains a native fallback when actually installed. **GNOME Software app-details is removed from fallback selection** because the live screenshot proved it unusable here. If neither path exists, the menu reports that setup is unavailable rather than quietly installing software in the background.
6. A unique visible staged installer already exists? Reuse it, **never launch a second** package transaction. Any GUI/terminal handoff reports only that launch was requested, not GUI visibility, installed packages, started oFono, a connected iPhone, or functional HFP.

## HOW TO USE

After separately approved merge and authorized deployment: **Social → PHONE → CONNECT PHONE → DEVICE → CALLS ON PC → SET UP CALLING**. When Fedora confirms oFono is absent, the interactive PackageKit terminal is requested inside PHONE's open chat-feed area. Review the `ofono` package and approve or decline its interactive transaction. Read any errors. Press Enter when done. PHONE then runs **read-only** package and service checks; it never enables calls automatically. If the terminal cannot fit Sway geometry precisely, it remains an external window rather than a fake hole.

Clicking RETURN TO PHONE or navigating away from PHONE does **not** cancel a package installation; the installer may remain as a separately floating window until finished. Do not forget/re-pair the existing iPhone or modify sound routing to solve an installer display issue.

## VERIFY

Automated tests:
- `tests/phone/test_phone_calling_setup_handoff.py`: exact-package, fixed-argv staged foot launch, duplicate actor, Fedora/missing-package preflight, no GNOME Software fallback, PackageKit GUI fallback, no untrusted argv or private data.
- `tests/phone/test_phone_ofono_install_session.py`: interactive-only CLI, no `-y` or silent approval, exact package, success/error wording and held results, no service/Bluetooth/phone action.
- `tests/phone/test_phone_stage_director.py`: distinct installer Sway identity, verified-only hole, never close in-flight installer.
- `tests/messaging/test_social_phone_calling_setup.py`: stage purpose, conditional in-panel cutout, no kill on tab/menu exit, status refresh after installer termination, one setup control.
- Existing PHONE, Social and Stage regressions included in `.github/workflows/social-phone-one-action-setup.yml`.

GitHub CI uses synthetic Sway and PackageKit fixtures. This does not prove a live Sway panel will accept the terminal geometry, a Polkit agent is present, PackageKit repositories resolve `ofono`, keyboard focus works, or the user's selected iPhone has HFP working. These need operator-approved runtime acceptance.

## WATCH OUT FOR

- **The real authorization happens inside PackageKit** after the user clicks the menu action. The in-menu launcher is not system installation permission on its own. If Fedora Polkit allows the current local admin account to install without extra authentication, PackageKit still uses the explicit interactive CLI confirmation; the helper never supplies `-y`.
- Navigation while installation is in progress does not cancel it. Closing the installer itself may interrupt the command; PackageKit transactions could still continue in the backend. Always recheck package state rather than assuming cancellation or success. Never call `--close-installer`.
- The handoff checks only exact `ofono` package absence. If it is installed but the service is stopped/failed, do not try to reinstall. oFono start/enable, D-Bus policy, WirePlumber HFP ownership, and BlueZ plugin changes are **separate OS audio owner work** requiring explicit operator approval.
- No live machine modifications, package installs, terminal windows, sound routes, Bluetooth bonds, service reconfiguration, PR merges or production activation by this worker. This is source code awaiting review.
- Neither the user's existing BlueFerry iPhone pairing nor per-phone audio preferences are shipped as Post-Apollo defaults. Content grants (SMS/iMessage/contacts) are independent and remain behind Gate A.
- The existing Social window's mask and Weather Stage Director were **not modified**. This uses only PHONE's already established cutout.
- Actual user-facing improvement is scoped to Fedora/Sway with `foot` and `pkcon`; future portable installer work needs a separately scoped assignment.

## CHECKLIST

- [x] Recheck Syntagma AGENTS/Hospital and current GitHub main/PRs.
- [x] Confirm previous stage and P9/P10 setup code merged, avoid concurrent file ownership.
- [x] Treat GNOME Software error as a failed app-details path, not Bluetooth failure.
- [x] Add exact package PackageKit session with native interactive consent.
- [x] Reuse verified PHONE Sway terminal cutout with installer-specific actor ID.
- [x] Forbid killing installer on pane/tab navigation.
- [x] Tests, workflow and durable handoff.
- [ ] Verify exact-head GitHub CI and mergeability.
- [ ] Social/Phone and OS package-management owner review, operator merge authorization.
- [ ] After separately authorized deployment, live Sway input/focus and native PackageKit confirmation, then oFono package/service verification.
- [ ] Real non-emergency HFP call audio acceptance.
- [ ] Final operator acceptance.

## NEXT

Review CI and bounded diff. With operator authorization, deploy and test the one in-panel PackageKit transaction without changing the paired phone. Confirm package installation only by independent RPM/service checks. Coordinate oFono/BlueZ/WirePlumber service configuration separately; never infer call readiness from package presence.

## DECISIONS

Use the already accepted PHOTO? No: **PHONE** Stage Director compositor cutout, not an additional installer UI. Replace broken GNOME Software app details with exact interactive PackageKit. Keep approval with Fedora, protect active transactions from kill-on-tab-change, and preserve personal phone and audio state. Repo-only proposal, operator final authority and acceptance. Recovery: close PR, or revert bounded commits after any later merge. No local rollback needed.
