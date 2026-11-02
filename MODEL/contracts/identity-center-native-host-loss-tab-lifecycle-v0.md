# Identity Center // genuine Quickshell host-loss and tab lifecycle smoke v0

> **STATE:** Disposable CI-only regression. No operator desktop connection, live host, production identity, workstation edits, real company data, or user acceptance.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **DEPENDENCY:** Merged #1026 supplies an unmounted native Quickshell 0.3.2 smoke, with four successful scenarios. Earlier #1015 and #1013 contain the existing read-only Social Organizations viewer and private socket transport. No other open PR owns this seam at the checkpoint.
>
> **HOSPITAL:** External Hospital-compatible ChatGPT contributor. Staff Role, Room, Assignment, permissions, live enrollment, and local workstation attachment unverified. Operator retains final authority.

## What actually changes

Only the unmounted `IdentityNativeDisplaySmokeV0.qml` test root, its synthetic `tests/identity/native_quickshell_display_smoke_v0.py` runner, source guards, native CI workflow, and MODEL documentation/index. No production `shell.qml`, `IdentityCenterSettingsSections.qml`, `IdentityCenterOrganizationDisplayReader.qml`, Identity Center server/API, database, token vault, browser, or service launcher changes.

The disposable Debian Quickshell process still gets a temporary HOME and separate XDG runtime/config/state/cache/data; `WAYLAND_DISPLAY` and `DISPLAY` are emptied and Qt runs offscreen. The Python fixture serves only fictional company IDs with empty `scopeGrants`, over a private 0700 directory/0600 Unix socket. Nothing uses real accounts or grants.

## New concrete lifecycle evidence

```text
[real qs native CI process, isolated]
     |
[unmounted IdentityNativeDisplaySmokeV0.qml]
     |
[real settings pane -> reader -> Quickshell.Io.Process -> fixed --json CLI]
     |
[private synthetic AF_UNIX snapshot host]

Host-loss scenario:
  READY -> 2 synthetic memberships
  -> separate timer closes actual server socket (not a fake error payload)
  -> 5-second reader refresh cannot connect
  -> UNAVAILABLE + zero organizations/portfolios + switch disabled

Tab-change scenario:
  ORGANIZATIONS -> READY
  -> test changes actual settings activeSection to SECURITY
  -> reader deactivates and clears snapshot
  -> test changes section back to ORGANIZATIONS
  -> fresh Process/CLI round-trip required for next READY
  -> validated memberships return; switch remains disabled
```

An absent host is not a logged-in person. A displayed scope preview is not a record-level permission. No client can select a new organization or supply credentials through the IPC request. The test checks actual Quickshell/Qt behavior but cannot establish safe behavior across system suspend, screen lock, a full Sway compositor, or a hostile same-UID process.

The previous four scenarios remain mandatory: initial READY, SIGNED_OUT, no socket at startup, and server-side synthetic revocation followed by a refresh.

## Verification

[Native Quickshell CI workflow](../../.github/workflows/identity-center-real-quickshell-native-smoke.yml) runs six independent synthetic scenarios, each with a new temporary runtime and a fresh `qs -p` process. Source guards additionally ensure the harness never becomes part of production shell, cannot start default Quickshell, and never emits a token or enables switching.

A passing test is evidence for *isolated CI*, not for live desktop integration or security certification. Verify the **exact PR head**, all six scenario steps, the synthetic boundary workflow, and the grammar checks. A test failure must be reported and fixed in the bounded harness or contract; do not loosen the production Identity Center authentication policy.

## Rollback and handoff

Leave the draft PR unmerged, or revert only the two synthetic harness files, the test source guard, workflow, and MODEL doc/index. No database, real host, local user data, or persistent server is created.

### IMPLEMENTATION
Two additional genuine Quickshell lifecycle scenarios that close the actual synthetic IPC socket or leave/re-enter the real Organizations settings tab.

### HOW TO USE
Review PR and CI only. No local machine action is needed or authorized by this work.

### VERIFY
Require six/ six native scenarios plus exact-head repository workflows. Even then, Sway visual and lock/suspend behavior remain unverified.

### WATCH OUT FOR
Offscreen Quickshell is not a live Wayland compositor. Same-UID process isolation is incomplete. No real backend credential handling or organization-switch functionality is exercised.

### CHECKLIST
- [x] Current main/#1026 merge and open PR ownership checked
- [x] Synthetic-only actual socket shutdown path and tab-change QML path
- [x] Source guards and CI workflow updated
- [ ] Exact-head CI green
- [ ] Independent security review
- [ ] Operator-approved local read-only inspection, later live synthetic test
- [ ] Operator final acceptance

### NEXT
Verify CI. If green, prepare the exact read-only, operator-controlled live Quickshell inspection boundary without modifying or restarting the desktop; separately authorize any actual local test requiring temporary files or processes.

### DECISIONS
No deployment, merge, local restart, local write, production IdP activation, live identity data, or company switching.
