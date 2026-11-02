# Identity Center // offscreen Qt Organizations reader smoke v0

> **STATE:** Unmerged, CI-only native Qt 6 QML-engine smoke. This is **not live Quickshell**, not the operator's Sway/desktop, and not a deployed authentication host.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **DEPENDENCIES:** #1013 private read-only socket and #1015 Social Organizations reader have both merged into main. Their prior 21/21 passing workflows prove Python IPC, extracted QML JavaScript, and Social layout contracts, but not real Qt loading/bindings.
>
> **OWNERSHIP:** New test-only `tests/messaging/fixtures/identity_qml_stubs/Quickshell` and `Quickshell/Io`, `tests/messaging/test_identity_center_offscreen_qml_v0.py`, isolated CI workflow and this indexed Model contract. No production QML, host, live service, keyring, data store or security policy modified.
>
> **HOSPITAL:** External Hospital-compatible ChatGPT worker. Live Staff Role, Room, Assignment, ownership lease, operator desktop attachment and final acceptance unverified.

## Why this slice exists

QML is code executed by Qt. Node-extracting functions catches JavaScript logic errors but does not confirm native Qt component construction, property bindings, signals or teardown behavior. This smoke runs the **actual repository QML file** inside a **real Qt 6 QQmlEngine** in a disposable GitHub runner, in offscreen graphics mode.

The test **stubs only the Quickshell-specific APIs**, not Qt. Those small modules provide a fake `Quickshell.shellPath()` and an inert `Process`/`StdioCollector` with Qt properties/signals. The fake Process never forks, touches a socket, opens a browser, reads credentials or communicates with an identity provider. The same QML file will continue to use genuine Quickshell imports on the real desktop because the test stubs are located under `tests/messaging/fixtures` and are **never installed or imported in production**.

```text
[ GitHub CI, disposable Ubuntu/PySide6 with QT_QPA_PLATFORM=offscreen ]
                     |
[ real QQmlEngine loads both IdentityCenterOrganizationDisplayReader.qml
  and IdentityCenterSettingsSections.qml with actual QtQuick and ActionButton ]
                     |
[ test-only stubbed Quickshell.shellPath + Process/StdioCollector ]
                     |
[ actual Qt signals, property bindings, QML JS and lifecycle ]
   - inactive: no process, no company snapshot
   - active: fixed /usr/bin/python3 + script + --json command
   - synthetic READY: LLC/nonprofit IDs visible, no token
   - synthetic SIGNED_OUT / NO_MEMBERSHIPS: empty list
   - malformed/failed Process: old companies erased
   - expired scope / forged external portfolio: fail closed
   - close/reopen while fake process pending: ignore old data
   - real settings navigation and button state: switching stays disabled
   - dynamic LLC/nonprofit membership rows and portfolio count
   - tabs/settings closed, SIGNED_OUT and invalid responses remove rows
                     |
[ tests finish; no system process, socket or account touched ]
```

The smoke complements the earlier **real Linux IPC subprocess tests**, disposable **real Keycloak browser callback tests**, and **source-level Social settings contracts**. It does **not** combine all components in a live Quickshell process. A real Quickshell runtime depends on the actual configured components, compositing session, Quickshell.Io APIs, user permissions, runtime directory and process supervisor, none of which this offscreen Qt test can prove.

## Verification

CI workflow: [Identity Center Offscreen Qt Organizations Smoke](../../.github/workflows/identity-center-offscreen-qml-smoke.yml). The runner installs pinned `PySide6==6.9.3` and executes:

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
    -s tests/messaging -p 'test_identity_center_offscreen_qml_v0.py' -v
```

Followed by the merged Python socket/CLI and Social Settings/Node contract suites. No private organization records appear; test data are clearly synthetic IDs. The first Qt run needed a disposable-runner libEGL dependency, installed by the workflow. The later [expanded offscreen Qt run](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/41486028629) passed **11 real Qt tests** on commit `cf909c7`: seven IPC-reader cases and four additional embedded-settings-pane cases. The new pane checks real QML navigation, dynamic Repeater rows, a disabled switcher, tab closure, logout and malformed data. QtQuick's visual child tree is traversed for dynamic delegates. This is still an offscreen test using fake Quickshell process APIs, **not** a screenshot or live UI integration.

## Local/live verification gate, not authorized by this PR

A later operator-approved Quickshell session test must inspect the already-running desktop without restarting it, then explicitly test the existing `USER // SETTINGS → ORGANIZATIONS` view with an approved **synthetic-only** host. It must confirm that closing settings, switching tabs, host stop/crash, expiry, and logout clear company data; that no token, URL or subject is exposed; that existing Social Layout functionality remains intact; and that organization switching cannot activate. Changes to local files, installs, process restarts, or Quickshell reloads require separate explicit approval.

**No production tokens, real LLC/nonprofit records, or external provider accounts belong in this verification.**

## Rollback and recovery

Leave the draft PR unmerged, or revert only the offscreen fixture files, test, CI workflow and MODEL doc/index. No production file or runtime is changed and no socket/credential needs cleaning. The test's QGuiApplication/QQmlEngine are disposed after each test.

### IMPLEMENTATION
Add actual Qt 6 engine smoke for both the existing QML Organizations IPC reader and the embedded settings pane, using inert Quickshell test doubles and unmodified production QML.

### HOW TO USE
Inspect PR/CI. No desktop action or installation necessary.

### VERIFY
Exact-head GitHub CI green required. Native Quickshell/Sway visual acceptance stays pending.

### WATCH OUT FOR
The Quickshell imports are fake *only in CI*; the test does not prove Quickshell.Io process lifetime, display compositor behavior, real service deployment or production identity security.

### CHECKLIST
- [x] Current main and merged #1013/#1015 verified; open Social ownership inspected
- [x] Actual source QML loaded in offscreen Qt 6 engine through isolated stubs
- [x] Synthetic READY, deny, expiry and close/reopen edge cases
- [x] Existing IPC/CLI and Social regression checks included
- [x] Eleven native Qt cases, including real dynamic settings UI controls, passed on `cf909c7` (reverify after this handoff commit)
- [ ] Approved live Quickshell visual/suspension and host-death evidence
- [ ] Host sandbox, OS token custody, security review and operator acceptance

### NEXT
Review CI. If successful, plan a separate, explicitly approved live Quickshell synthetic-host verification with safe recovery pointers. Do not merge or deploy without operator authorization.

### DECISIONS
CI only. No real IdP vendor, actual organization, local machine write, operator UI restart, deployment, enterprise role or organization switching.
