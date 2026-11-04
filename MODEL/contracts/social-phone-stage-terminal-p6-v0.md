# Social PHONE P6 // Stage Director terminal bay in the existing chat feed

> **STATE //** Repository pilot / draft review only. Live Sway/Quickshell, input mask, geometry, existing iPhone target and phone-side pairing unverified.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **ROOM //** Social Phone Bridge continuation, terminal-in-feed subassignment
>
> **WORKER //** external Hospital-compatible DOC, not verified registered in live Hospital
>
> **OPERATOR EVIDENCE //** Screenshot 2026-11-04: `blueferry pair-setup` opened in a separate `foot` terminal. Social PHONE's DEVICE view has a large blank feed region beneath setup controls. The terminal says an existing BlueFerry iPhone target is configured and prompts to **forget and start fresh** with default **N**. Preserve the bond; do not answer yes solely to position the terminal.

## IMPLEMENTATION

Uses the exact Weather Station *visual cutout + Sway actor* technique, without touching the Weather component itself or creating a different terminal infrastructure:

1. The existing `PhoneNativeSetupLaunch.py` still requires an explicit **SET UP IPHONE** click. For a backend-only BlueFerry installation using the installed `foot` terminal, add one fixed Wayland app-id `post-apollo-social-phone-setup` to the `foot` launch. A separate `stageCandidate` result is **true** only for that exact foot process. All other GUIs/terminals keep their existing external-app behavior and `stageCandidate=false`. No alternate command supplied by device metadata.
2. New `PhoneStageDirector.py` locates a **unique, visible** Social window with title `QS_SOCIAL_MENU` and a **unique** foot Sway actor with the exact new app-id, positive Sway `con_id` and a real `/proc/<pid>/exe` basename of `foot`. It bounds a PHONE-local bay to the currently observed Social window rect; any invalid, absent, ambiguous or out-of-bounds actor fails closed. Only that Sway `con_id` is resized/moved. No global window selector or generic process kill; no phone content.
3. The same Social `PhonePane.qml` calculates a terminal bay **below** DEVICE controls and above the bottom margin, with at least 200×120 logical pixels, and invokes Stage Director via a bounded status poll *only after the tagged foot process was requested*. A compositor window resize request does not authorize the cutout. The next `get_tree` observation must show the **exact** terminal client content rectangle at the expected bay before `stageState=ALIGNED`.
4. A PHONE-local `WeatherStage.StationChassisCutout` paints around that *verified* bay, keeping the current PHONE contact column, top toolbar and setup controls. The parent Social `FloatingWindow.mask` subtracts the same verified hole with Quickshell `Intersection.Subtract`, and the parent `WindowPanelFrame` alpha underlay is disabled only while this PHONE hole is active. The terminal receives mouse/keyboard input through the opening; other Social services and focus geometry remain unchanged.
5. **CLOSE SETUP**, leaving DEVICE or closing PHONE terminates only the precisely identified staged foot actor, restoring the ordinary pane and input mask. Never run `blueferry pair-setup` on automatic menu open or auto-repair an existing configured phone. If the actor cannot be verified after bounded attempts, the UI reports unavailable and **does not open a fake transparent hole**.

The Stage Director name in this milestone denotes PHONE's bounded compositor bridge. Weather Station's separate `StationTerminal.qml` controller and Sway namespace are unchanged. This is compositor *staging* of a separate native window, not literal QML embedding and not a production phone-access host.

## HOW TO USE

After explicitly reviewed/merged and separately deployed code:

- Open **Social → PHONE → CONNECT PHONE → SET UP IPHONE**.
- On a backend-only installation where `foot` and `blueferry` are present, a BlueFerry terminal is requested. The new PHONE Stage Director attempts to place it in the large blank area below the setup controls.
- If an already-configured iPhone target produces **Forget configured target and start fresh? [y/N]**, select **N** or press Enter. Pairing/forgetting is separate from compositor placement. Do not reset the bond to solve a visual issue.
- A confirmed compositor fit exposes the terminal as a click-through Sway actor. A failed fit leaves no deceptive embedded terminal; the native terminal may remain separate and the view says so.
- **CLOSE SETUP** closes only the staged terminal. Existing PHONE messages, calls and contacts remain locked pending a real authenticated content bridge.

## VERIFY

`tests/phone/test_phone_stage_director.py` covers exact actor PID/app-id/visible match, unique Social title, bounding, verified content fit versus resize requested, rejection of irrelevant window/processes, exact `con_id` close, redacted errors and no Bluetooth/message commands.

`tests/messaging/test_social_phone_stage_terminal.py` checks Weather cutout reuse, cross-window mask subtract, typed stage result, no automatic launch, unchanged Social contacts/feed and no phone messages. Native setup launcher tests verify the unique foot app-id and non-stage GUI paths. Dedicated CI workflow runs these plus existing PHONE regressions.

Tests are synthetic and QML source-level. They are **not** a substitute for real Sway tree observations, Wayland compositing ordering, resize/minimum-size behavior, scale factor, live keyboard focus or a genuine BlueFerry wizard session.

## WATCH OUT FOR

- This is a **cross-owner Social floating-window mask seam**. It requires Social integration owner review before merge, even though modifications to `MessagingW.qml` are limited to one conditional alpha fill and one conditional input-mask hole. Do not let this replace all Social window focus rules or override the Weather Stage controller.
- The implementation intentionally supports a staged **foot** wizard only. GTK/Qt/BlueFerry Quickshell native clients and fallback `kitty`/`alacritty`/`konsole` remain external until individually supported and verified. The screenshot shows `foot`, so this covers the observed use case.
- The terminal remains a separate compositor actor. It may appear momentarily outside the feed while Sway maps it; the alpha/input hole is enabled only after verified exact geometry. If Sway cannot make exact pixels (client padding, fractional scale), the bay remains painted rather than exposing the desktop. This is a pilot, not fully live-verified fit.
- The current iPhone bond is already configured according to the screenshot. **Never forget/re-pair simply because PHONE needs a hosted window.** Bluetooth audio and BlueFerry MAP/PBAP content permissions remain independent.
- Phone content, FaceTime, SMS/iMessage and contacts are not authorized by this terminal placement. Production Identity Center Gate A remains separate and no automatic Social content reads or sends are introduced.
- No Fedora host modifications, terminal launches, resets, Bluetooth restarts, Quickshell reloads or live tests were performed by the GitHub worker. Deployment and final acceptance belong to the operator.

## CHECKLIST

- [x] Read Syntagma Hospital entry, inspect current main, Phone, Social floating-window and Weather Station cutout/terminal.
- [x] Verify no active PHONE/Social implementation PR collision at branch creation.
- [x] Implement scoped foot app-id and typed launch receipt.
- [x] Implement narrow Sway Stage Director with verification-before-exposure and exact `con_id` operations.
- [x] Wire conditional PHONE alpha + input hole into existing Social window.
- [x] Add synthetic unit and QML static tests, extend workflow.
- [ ] Run and verify exact-head GitHub CI.
- [ ] Shared Social owner review and operator merge authorization.
- [ ] Fedora live Sway geometry/input-mask, foot app identity and stage focus acceptance after authorized deployment.
- [ ] Production Phone Bridge/Identity Center trusted user/device/line and content integration.

## NEXT

Evaluate CI and review shared-window effects. For a live acceptance pilot, confirm a single `foot` app-id actor appears, matches the PHONE bay on the real Social floating window, remains interactive through the mask, and is cleaned up only when the operator leaves PHONE or closes setup. Keep existing BlueFerry bond intact, then continue independently on the actual message/contact transport and authorization.

## DECISIONS

Implement operator-requested terminal **inside the existing PHONE feed area** by reusing Weather Station's compositor-cutout pattern. No new Post-Apollo menus/passwords or copy of the Weather terminal. Keep Social contacts/chat layout; no production authorization or phone permission inference. Repository-only proposal, final DONE remains operator acceptance. Rollback: close draft branch/PR; if merged, revert the bounded commits and restore PhonePane/MessagingW mask behavior. No local rollback required.
