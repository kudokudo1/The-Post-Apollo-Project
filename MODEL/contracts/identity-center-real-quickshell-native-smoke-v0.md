# Identity Center // disposable genuine Quickshell Organizations smoke v0

> **STATE:** Test-only native Quickshell CI, not a live desktop change. No user account, production host, token, real LLC/nonprofit, company switching, local restart, installation or activation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **UPSTREAM:** Merged #1019 now verifies full Organizations settings pane with a real Qt 6 engine but fake Quickshell.Io Process, as well as merged #1015 QML viewer, #1013 Unix IPC, #1011 disposable Keycloak and #1007 state-machine contract.
>
> **SCOPE:** New top-level, **unmounted** `IdentityNativeDisplaySmokeV0.qml` (never imported by `shell.qml`), `tests/identity/native_quickshell_display_smoke_v0.py`, source guard tests, isolated CI and this indexed contract. No production QML/service/credential/CI workflow is modified.
>
> **HOSPITAL:** External Hospital-compatible contributor only. Staff Role/Room/Assignment/live attachment unverified; operator maintains final authority.

## What genuinely executes

```text
[ GitHub Actions container: official Debian unstable Quickshell 0.3.2-1 ]
  QT_QPA_PLATFORM=offscreen, no DISPLAY or WAYLAND_DISPLAY
  temporary HOME + XDG_RUNTIME_DIR + CACHE/CONFIG/STATE/DATA directories
                          |
[ real qs -p repo/IdentityNativeDisplaySmokeV0.qml ]
  - only starts with explicit CI_DISPOSABLE_ONLY environment gate
  - uses actual Quickshell ShellRoot, Process and StdioCollector
  - embeds the real IdentityCenterSettingsSections component
  - opens only the Organizations section of the test instance
  - never loads the default workstation shell.qml configuration
                          |
[ actual /usr/bin/python3 identity_display_reader_cli_v0.py --json ]
                          |
[ synthetic 0600 Unix socket / private test XDG_RUNTIME_DIR ]
  - only fake LLC A / nonprofit / portfolio IDs, scopeGrants = []
  - no principal, access token, refresh token or real company
  - host callback returns read-only READY / SIGNED_OUT
                          |
[ actual QML JSON whitelist + real QtQuick repeater and settings bindings ]
  - READY: exactly two synthetic memberships and portfolio
  - SIGNED_OUT: empty list; switching remains disabled
  - MISSING: no socket, UI shows UNAVAILABLE, no stale organizations
  - REVOKE: first READY, next poll SIGNED_OUT, no stale organizations
                          |
[ qs exits test root; temp socket, process and XDG data removed ]
```

The CLI never receives a token, principal, organization selection or IPC command except `SNAPSHOT\n`. The test's Python host simulates a server-verified display, **not** actual Keycloak access. Real-Keycloak tests in merged #1011 separately verify signed tokens and the API; this CI is about the final genuine Quickshell.Process and QML integration.

The harness has no `PanelWindow`, Sway layer-shell request, OAuth browser, login, actual user records, or production service. Test isolation includes wiping `DISPLAY` and `WAYLAND_DISPLAY` and replacing `HOME` and all relevant `XDG_*` directories with a disposable temporary directory. The QML root is never imported or mounted by production `shell.qml`. File watcher is disabled within that test instance. The Python runner starts no default `qs` instance and does not use `qs kill`.

## How to verify

The [CI workflow](../../.github/workflows/identity-center-real-quickshell-native-smoke.yml) uses the Debian-packaged `quickshell=0.3.2-1` binary in a disposable GitHub Actions container. It tests each scenario in a fresh isolated process:

```bash
python3 tests/identity/native_quickshell_display_smoke_v0.py --scenario ready
python3 tests/identity/native_quickshell_display_smoke_v0.py --scenario signed-out
python3 tests/identity/native_quickshell_display_smoke_v0.py --scenario missing
python3 tests/identity/native_quickshell_display_smoke_v0.py --scenario revoke
```

Each case must emit an exact `IDENTITY_NATIVE_SMOKE_PASS_*` marker from actual Quickshell QML, return process exit status zero, and never print a timeout marker. A separate CI source guard ensures no production root import, no unsafe process controls, no tokens, and an exact dummy-only activation gate. On failure the runner emits only a bounded error-category summary, never any stdout payload from the test child.

**Verification:** [real Quickshell container run](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/41490131413) passed all four native cases with Quickshell 0.3.2 and the source guard passed, on commit `3a49849`. The first CI attempt failed because the minimal Debian container omitted `Qt5Compat.GraphicalEffects`, required by the production `ActionButton`; the workflow now installs Debian's `qml6-module-qt5compat-graphicaleffects`. This establishes genuine Quickshell.Process execution in the disposable offscreen runner, not the operator's Sway session. Backend authorization and real desktop/lock/suspend lifecycle remain separate. Even a green result is *not* the operator's Sway session. Backend authorization and real desktop/lock/suspend lifecycle remain separate.

## Recovery and decision boundaries

Recovery is to leave this draft PR unmerged or revert only the unmounted QML test root, runner, guard, workflow and MODEL document/index. CI uses `TemporaryDirectory` and stops the child after a bounded timeout; there is no local rollback or persisted credential.

### IMPLEMENTATION
Disposable real Quickshell test for the existing read-only Organizations pane, with synthetic Unix socket fixture and four lifecycle scenarios.

### HOW TO USE
Review the PR and GitHub CI. No local installation or command is needed for the operator to inspect. Do NOT run the harness against a user's real `XDG_RUNTIME_DIR` or default shell.

### VERIFY
Check exact-head workflow, process exit code and four pass markers, then independent security/lifecycle review.

### WATCH OUT FOR
Real Quickshell in offscreen CI does not equal visual verification on Sway/Wayland, host sandboxing, token vault, real key rotation, provider onboarding or operator acceptance. The user has reported their desktop running, but this session does not have a verified connection to that process.

### CHECKLIST
- [x] Current main, open ownership and Syntagma/Hospital rules rechecked
- [x] Unmounted genuine native ShellRoot and isolated Python fixture
- [x] No tokens/real company records and no production setting modification
- [x] Four smoke cases, guard tests and isolated container workflow created
- [x] All four native Quickshell scenarios and source guards passed on `3a49849` (recheck exact head after handoff edit)
- [ ] Security review and operator final acceptance
- [ ] Separate approved live desktop test and real host deployment

### NEXT
With container CI green, the next stage is an operator-approved observation of the real Quickshell pane with synthetic records, while leaving organization switching disabled. Check lock/suspend and compositor behavior separately; the container does not prove those.

### DECISIONS
No production process/root modification, merge, device installation, local service mutation or real account sign-in. Test-only Debian 0.3.2 native Quickshell does not select a production runtime version.
