# 🏥💜 TASKS M14c // Real Quickshell Disposable Post-Crash Review

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS Source Integrity / Encrypted Draft Recovery  
**STAFF ROLE //** DOC, Hospital-compatible external OPEN AI // CHATGPT; live Hospital registration not verified  
**ASSIGNMENT //** Execute M14b's real Quickshell test panel with actual disposable SQLite/source recovery evidence  
**BASE //** `main` `a43421f605d7aa187a092461585ba7dd0169002d`, November 7, 2026. M14b PR #1407 merged as `4ee0ea36027c28d22071127f515725c5b2c4c746`; M14a #1394 previously merged with 57/57 workflows passing.  
**SCOPE/PERMISSIONS //** GitHub-only additive test QML, ephemeral CI Python runner, tests, workflow, documentation. No changes on the operator's Fedora desktop, production TASKS writer, real saved tasks, Connections/keyring code, runtime activation, automatic PR merge or live Hospital registration.

## IMPLEMENTATION

M14b demonstrated real *disposable* JSON and SQLite source readback through Python and a strict M13z UI policy, but it only used **QML syntax checking**, not real Quickshell. M14c closes that specific test gap by reusing a CI technique already present in `.github/workflows/identity-center-real-quickshell-native-smoke.yml`, which installs **Debian-packaged Quickshell 0.3.2** in a disposable GitHub container and launches Qt on a **private Xvfb virtual X11 display**. The initial offscreen attempt failed before QML startup because `PanelWindow` requires a real window backend.

- `TaskPostCrashNativeSmokeM14c.qml` is a new **unmounted ShellRoot** that contains the actual M14b `TaskPostCrashReviewLabM14b` component. It is gated on the literal `POST_APOLLO_TASKS_M14C_NATIVE=CI_DISPOSABLE_ONLY` environment value and a fixed six-case scenario set. Unlike M14b's normal human-click interaction, only this CI root uses a bounded Timer to call the existing `inspectOnce()` method automatically. It verifies the resulting **real QML** status, redacted policy label, and denial of all replay/write/draft-clear/key authorities. It exits with a fixed marker or refuses/times out. It never mounts inside `shell.qml`.
- `tests/tasks/native_quickshell_postcrash_smoke_m14c.py` creates a fresh private `/tmp/m14c-real-qs-*/m11e-fileview-test` folder, synthetic `0600` JSON, and the existing M12h SQLite source-stage journal. It simulates **baseline**, **expected-but-unsettled**, **settled-but-UI-unacknowledged**, **unsafe symlink**, **missing source**, and **cooperating owner with an exclusive lock**. It then launches the **real `qs` binary** with its own isolated HOME, XDG_CONFIG_HOME, XDG_STATE_HOME, XDG_DATA_HOME, XDG_CACHE_HOME, XDG_RUNTIME_DIR, and no connection to the operator's Wayland/X11 session. Each CI scenario gets a fresh, local Xvfb display with Qt's `xcb` backend. The real QML runs M14b's existing Quickshell `Process` to invoke M13y's inspector and passes the frame to M13z's strict presentation projection. Python verifies the fixed native PASS marker, checks source bytes are unchanged, checks application SQLite rows are unchanged, and closes the fixture lock. It never invokes the live TASKS writer or reads a real task.
- `tests/tasks/test_task_real_quickshell_postcrash_guard_m14c.py` checks the CI-only gate, strictly unmounted test root, existing single writer and closed Connections grants, fixture-only source, and confirms a non-CI invocation is refused *before looking for Quickshell*. The workflow reruns M14b/M14a/M13y/M13z/M11d/C2a guard suites.

This uses a **real native Qt/Quickshell process** in CI if the Debian container can install and load the dependency. It is *not* evidence that the operator's exact Fedora Silverblue/Wayland/Quickshell build renders correctly, or that callback and source ownership are cryptographically authenticated.

## HOW TO USE

The new GitHub workflow runs after a PR is opened. Each native scenario is wrapped in `xvfb-run -a -s "-screen 0 1024x768x24 -nolisten tcp"`, so the real `PanelWindow` has a private X11 backend without touching the user's compositor. The native job itself is confined to disposable GitHub CI and refuses to run unless `GITHUB_ACTIONS=true` and `POST_APOLLO_M14C_DISPOSABLE_CI=1`. **Do not set those markers on the operator's live Fedora desktop**. They are process preflight gates, not real security authorization.

The six native CI scenarios are launched individually:

```sh
python3 tests/tasks/native_quickshell_postcrash_smoke_m14c.py --scenario baseline
python3 tests/tasks/native_quickshell_postcrash_smoke_m14c.py --scenario expected
python3 tests/tasks/native_quickshell_postcrash_smoke_m14c.py --scenario settled
python3 tests/tasks/native_quickshell_postcrash_smoke_m14c.py --scenario unsafe
python3 tests/tasks/native_quickshell_postcrash_smoke_m14c.py --scenario missing
python3 tests/tasks/native_quickshell_postcrash_smoke_m14c.py --scenario locked
```

These commands are documented for reproducibility of the GitHub runner, **not instructions to run in a personal shell**. No user-installed app, live desktop restart or task data copy is needed to inspect the PR.

## VERIFY

Successful native CI must prove:
- Actual Quickshell loads an unmounted, gated QML root and instantiates the genuine M14b review component.
- QML `Process` starts M13y's existing **read-only** Python inspector and parses one redacted fixture frame.
- The M13z projection shows the exact three synthetic recovery labels, or refuses missing/symlink/locked sources. It always denies draft deletion, replay, restore, saved ACK and key release.
- Application SQLite journal rows are unchanged during inspection; synthetic JSON source bytes are unchanged. SQLite may still manage transient WAL `-shm` metadata.
- Existing production TASKS continues to contain exactly one `FileView`, one `todoFile.setText()`; no new production reader/writer, secret action or Connections control.
- Native PASS is corroborated by independent post-run Python source/journal comparison, not by a test-only QML claim alone.

Native proof applies only to a **disposable CI Xvfb virtual X11 environment**. It does not cover a user clicking the manual M14b panel on Fedora, native Wayland focus behavior, same-UID malicious writers, full disk durability after power loss, or authenticated live-source provenance.

## WATCH OUT FOR

The M13y inspector and M12h journal remain **test-only**. The source and journal are separate files with an intervening crash window. A hostile same-UID writer can potentially forge bytes, metadata and callbacks. Matching hashes do not prove an application identity, user approval or a durable task save.

This test uses a second `Scope` and `PanelWindow` **only in a separate Quickshell process**. No second production TASKS `FileView` exists. The real TASKS recovery screen still reports source verification **NOT CONNECTED**, and its M14a callback observation remains a non-authoritative hint.

A Debian Quickshell 0.3.2 CI PASS cannot be called Fedora native acceptance. If the Debian package, Qt module, `ShellRoot` or panel fails at runtime, report the actual blocker and fix only the isolated CI harness rather than enabling production storage features.

## CHECKLIST

- [x] Verify M14a and M14b merges and review current main/Syntagma/PR ownership
- [x] Reuse existing M14b native component and M13y/M13z evidence pipeline
- [x] Create gated, standalone real Quickshell CI root
- [x] Create disposable Python launcher for six source/journal/lock scenarios
- [x] Add negative security guards and CI workflow
- [x] Real native Qt/Quickshell **six-scenario execution** verified in CI on the Xvfb-enabled PR head (rerun required on final documentation-only commit)
- [ ] Independent Nurse 2 review and operator merge
- [ ] Separately authorized local Fedora/Wayland acceptance
- [ ] Independently authenticated live source owner and opt-in encrypted draft recovery

## NEXT

Review the real native CI evidence and resolve any QML/Process/runtime mismatch. After merge and separate authorization, native-verify the standalone M14b panel on Fedora under an isolated fixture. The next production-shaped change must establish a well-defined source ownership and conflict model without another writer or making FileView callbacks into trusted receipts.

## DECISIONS

Retain M12l single local TASKS logical writer, disabled producer/recovery gates, preserved drafts, no user content read, no real keyring, no automatic replay or draft clearing. This is isolated acceptance of the *test interface*, not permission to activate encrypted recovery or deploy to the operator's desktop. PR merge and final operator acceptance remain separate.
