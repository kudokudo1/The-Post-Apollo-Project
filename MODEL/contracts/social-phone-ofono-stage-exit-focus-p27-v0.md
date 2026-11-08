# Social PHONE P27 // Finished oFono terminal lifecycle and exact-actor focus

> **STATE //** GitHub-only draft source fix. No local Fedora/QS changes or active phone transaction; live alignment and input remain for operator verification. **PATIENT //** `kudokudo1/The-Post-Apollo-Project`. **ROOM //** Social PHONE CALLS P25/P26 continuation. **ASSIGNMENT //** Repair the failed setup terminal's indefinite wait and provide an exact installer focus route without killing active OS package work. **WORKER //** External Hospital-compatible ChatGPT DOC, not registered in live Hospital. Operator retains final authority.

## IMPLEMENTATION

- Operator screenshots dated 2026-11-08 show the newly merged P26 Silverblue installer ran `rpm-ostree install ofono`, failed dependency resolution on `libdnf5` version conflicts between Fedora repositories and the currently booted layered system, then remained at `Press Enter to close this terminal and recheck PHONE...`. The terminal also visually overlapped the PHONE lower bay and became hard to focus.
- **Exact reason for orphan:** `PhoneOfonoInstallSession.py` indefinitely called `input()` after the transaction already exited, while `PhonePane.qml.closeStagedSetup()` intentionally does not kill the installer on widget close. Both rules are independently justified, but losing keyboard focus leaves an indefinite orphan.
- The terminal now offers a **bounded post-transaction review window** (up to 12 seconds, or Enter to exit early). The wait begins only **after** the package command has finished. A disconnected/unusable TTY fails closed instead of hanging. No automatic cancellation, Sway kill, host change, pending-deployment mutation or transaction timeout was added.
- For an active staged terminal, the existing PHONE SETUP header now exposes **FOCUS TERMINAL** next to **RETURN TO PHONE**. This is a *user-clicked* action invoking `PhoneStageDirector.py --focus-installer`. Stage Director resolves the unique exact `post-apollo-social-phone-ofono` Sway con_id, validates its `foot` process/visibility and sends only `[con_id=N] focus`. No generic terminal matching, implicit focus, close, keyboard injection, move or resize occurs.
- Preserve the existing verified Sway content rect / exact cutout contract, `stageHoleValid`, and geometry polling. The screenshot does not independently prove a numeric coordinate bug; live placement must still be checked. Focus may restore the correct foreground relationship when Social has keyboard ownership but the terminal is geometrically aligned.
- SOURCE-level message clarifies the active-transaction boundary: if the user closes Social **during** the package command, the terminal must remain alive until that operation completes; after completion it exits without indefinitely trapping the operator.
- **Out of scope:** resolving rpm-ostree's Fedora `libdnf5` dependency conflict, updating layered packages, enabling oFono/HFP, restarting services, Bluetooth adjustments or reboot.

## HOW TO USE

After operator-reviewed merge and separately approved local update: **Social → PHONE → DEVICE → SET UP CALLING**. Once installer starts, **FOCUS TERMINAL** restores focus to that exact installed `foot` window when needed; **RETURN TO PHONE** only detaches PHONE and does not interrupt an active package transaction. Following success or failure, terminal shows result briefly, exits automatically if Enter does not reach it, then PHONE runs its existing read-only package/service rechecks. Neither a failed package transaction nor the presence of the terminal indicates HFP is ready.

On the **currently installed** P26 version, the old terminal can be exited by focusing the foot window then pressing Enter. Since screenshots show the package command already ended, no package transaction should be in progress inside this terminal, but verify the prompt before attempting any external window close. Do not retry oFono until the separate dependency conflict is investigated.

## VERIFY

- Existing `tests/phone/test_phone_ofono_install_session.py`: keep injected test hook and verify bounded select/TTY review, Enter, no-focus auto exit and error tolerance; existing install approval/prerequisite guards unaffected.
- `tests/phone/test_phone_stage_director.py`: only exact installed foot actor can receive explicit focus, duplicate/wrong/nonvisible actors fail closed, existing forbidden installer kill persists.
- `tests/messaging/test_social_phone_stage_terminal.py`: header focus/return lifecycle and unchanged verified cutout geometry.
- Existing Social PHONE setup workflow covers all modified scripts and tests. **CI, live Wayland focus, compositor fit, actual failed transaction result and new deployment need separate verification.**

## WATCH OUT FOR

- The screenshot's dependency conflict is a **separate OS image/layer consistency blocker**, not a reason to weaken `rpm-ostree` deployment guards or force-remove libdnf5. No oFono install was confirmed. Need read-only package/deployment inspection before proposing any OS-level repair.
- A running install must remain visible or recoverably active even if the Social widget closes. The automatic terminal close occurs only after its subprocess returns. A long-running or hung package manager can still leave a terminal as designed.
- Exact-content Sway alignment is a **source assertion**, not proof of display pixel perfection under the user's live SwayPX/Quickshell. No unverified geometry constants or broad compositor operations were changed.
- Opening this PR does not deploy source code onto the user's machine; the old prompt will continue to wait indefinitely until the new version is approved and installed.

## CHECKLIST

- [x] Inspect operator screenshots and recover current main/P26 merge.
- [x] Recheck Syntagma/Hospital permissions and neighboring PRs.
- [x] Identify indefinite finished-terminal input hold plus non-kill-on-close interaction.
- [x] Implement bounded post-transaction prompt and exact targeted user-click focus.
- [x] Add existing-workflow synthetic regression tests.
- [ ] Exact-head CI and operator review/merge.
- [ ] Separately approved local update and live focus/cutout/close test.
- [ ] Read-only Fedora `libdnf5` dependency investigation under separate OS owner.
- [ ] Approved oFono install and subsequent HFP test.

## NEXT

Review P27 CI and the bounded source diff. After operator approval, merge/deploy and verify the staged terminal gets focus on click and automatically exits after a failed transaction without disrupting an active one. Keep actual oFono package installation paused while the displayed libdnf5 resolution conflict is diagnosed.

## DECISIONS

Preserve P26 `rpm-ostree` host installation gates and the no-kill rule while an install runs. Terminate the **finished UI holder**, not the live package operation. Focus only via exact verified Sway actor and direct user click. Do not merge, update a local checkout, restart anything or alter current BlueFerry pairing without operator authorization. Recovery: close PR before merge or revert this small patch after merge.
