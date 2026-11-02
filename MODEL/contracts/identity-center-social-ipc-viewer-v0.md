# Identity Center // Social Organizations read-only IPC viewer v0

> **STATE:** Staged QML display and fixed read-only CLI, NOT verified on a live Quickshell desktop. Depends on **open draft PR #1013** (private Linux IPC host prototype). Neither PR is merged/activated at creation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **BRANCH/PR:** `feature/identity-social-readonly-ipc-viewer-20261102` stacked on `feature/identity-private-desktop-snapshot-ipc-20261102`. Review and accept #1013 first; this PR must not be merged independently directly to main while its dependency is pending.
>
> **HOSPITAL:** External, Hospital-compatible contributor; no verified live Staff Role, Room, Assignment, local desktop attachment or deployment authorization.
>
> **OWNERSHIP:** New `services/identity/identity_display_reader_cli_v0.py`, `tests/identity/test_identity_display_reader_cli_v0.py`, `widgets/messanger/IdentityCenterOrganizationDisplayReader.qml`, `tests/messaging/test_identity_center_ipc_viewer_v0.cjs`, small bindings in existing `widgets/messanger/IdentityCenterSettingsSections.qml` and `AppSelector.qml`, isolated CI, MODEL document/index. All existing provider OAuth/login and runtime service launchers remain untouched.

## Source-to-display data flow

```text
[ Future privileged desktop identity host -- NOT STARTED BY THIS PR ]
    - owns browser sign-in, PKCE, signed token verification
    - owns bearer and API request inside isolated host process
    - retrieves server-verified active company memberships
    - validates through DesktopContextProjection
                  |
[ PR #1013 private IPC host, NOT YET MERGED ]
    - pre-existing private 0700 $XDG_RUNTIME_DIR/post-apollo-identity-v0/
    - 0600 identity-display-v0.sock
    - Linux peer UID checks (NOT a same-UID sandbox)
    - only operation "SNAPSHOT\n", only sanitized JSON display, no writes
                  |
[ identity_display_reader_cli_v0.py --json ]
    - resolves a fixed name under a validated private XDG_RUNTIME_DIR
    - refuses other commands, socket selection, principal/org/role inputs
    - uses existing read_private_display() strict parsing and validation
    - outputs one JSON line or empty UNAVAILABLE on host failure
    - never starts host, writes files, logs credentials or persists snapshots
                  |
[ Quickshell Process in IdentityCenterOrganizationDisplayReader.qml ]
    - starts only when existing USER // SETTINGS -> ORGANIZATIONS is open
    - calls fixed Python CLI with "--json" only
    - clears existing company data BEFORE each 5-second refresh
    - ignores output on close and erases on failed/invalid read
    - validates exact display schema and independently joined tenant IDs
    - no token, provider subject, account action, business write or URL
                  |
[ Existing IdentityCenterSettingsSections.qml ]
    - receives optional display-only organizationDisplaySnapshot
    - renders organization ID, kind, scope preview count and portfolios
    - shows no verified active company and keeps SWITCH UNAVAILABLE
    - original SOCIAL LAYOUT and local provider account editors unchanged
```

This is a *viewer* of the existing display contract, not an authentication authority. The two processes exchange a fixed SNAPSHOT request and response; describing this as fully one-way IPC would be inaccurate. The request contains no privileged action or requested tenant. The private directory/same-UID socket is NOT protection against malicious code running as the same user.

## Critical lifecycle decisions

1. The QML reader is active only while `appSelector.settingsOpen` and `sections.activeSection === "ORGANIZATIONS"`. Leaving settings or the Organizations section sets its snapshot to null and clears company data in the same QML component. A late process result is ignored if the reader is inactive. An explicit in-flight response guard also refuses the *old* result if a user closes and immediately reopens the pane before the previous subprocess finishes.
2. While active, the reader polls at five-second intervals, **clearing before each poll**. A hung command therefore cannot leave a prior READY list displayed indefinitely; if no host/socket exists the CLI returns UNAVAILABLE with empty memberships.
3. The Python CLI returns exactly one JSON line, never a token, error trace or private path. Only `--json` is permitted; extra args including company/role/token selectors exit with no output. The QML reader never uses an external URL, JavaScript fetch, dynamic command arguments, credential storage or browser opener.
4. Both the Python IPC client and the QML display validator reject malformed results. The QML validator checks exact top-level and nested keys, bounded org/grant/portfolio collections, known kind/action, duplicate org/portfolio IDs, invalid grant expiry, cross-portfolio tenant leakage and rejects any `canSwitchOrganization=true`.
5. No persistent login state, session token or credentials are stored in QML. The host session remains unimplemented as a deployed service. Rendered scope grants remain **display previews only**; they grant no record access, and organization switching stays disabled.

## Test and verification

[Social read-only IPC viewer CI](../../.github/workflows/identity-center-social-ipc-viewer.yml) runs:

```bash
python3 -m unittest discover -s tests/identity \
  -p 'test_identity_display_reader_cli_v0.py' -v
node tests/messaging/test_identity_center_ipc_viewer_v0.cjs
python3 -m unittest discover -s tests/messaging \
  -p 'test_identity_center_settings_sections.py' -v
python3 -m unittest discover -s tests/messaging \
  -p 'test_identity_center_desktop_display_v0.py' -v
```

The CLI suite creates a disposable Linux private XDG-runtime directory and IPC socket from PR #1013, runs the actual Python CLI in a separate subprocess, and checks real READY/non-READY JSON, missing host, shutdown, forged token field, runtime directory permissions and same-user socket path constraints. The Node test extracts and runs the **actual QML JavaScript functions**, checking schema validation, forbidden role/token fields, revocation-style SIGNED_OUT output, duplicate/missing members and clear-before-refresh. It also checks that the existing settings window gates the reader and that the switcher remains disabled.

**Limits:** These tests do not load native QML, render a Quickshell window, observe OS lock/suspend, verify a production sandbox, or connect a real desktop Keycloak user. Real Keycloak's disposable login proof remains in merged #1011. PR #1013 is not merged or deployed. A real runtime must supervise/cancel hanging processes, handle locking/suspension, and use an approved process sandbox before sensitive accounts are enabled. No claim of visual acceptance or production session availability is made.

## Recovery and handoff

Rollback: leave this stacked PR unmerged or revert its own new files and two bounded QML bindings/Model index, without touching #1013 or the previous merged identity foundations. No desktop installation or long-lived files exist; CI temporary directories and sockets are cleaned up after each test.

### IMPLEMENTATION
Fixed tokenless snapshot CLI plus existing-settings-only QML reader, bounded 5-second polling, fail-closed no-cache display, and real IPC/JS tests.

### HOW TO USE
Review the stacked PR and CI. On the current live desktop this source is not installed by ChatGPT. The interface still has no real company connection unless an independently approved host creates the private socket.

### VERIFY
Exact-head GitHub CI, then separately approved live Quickshell visual tests using synthetic organizations (no real credentials). Recheck #1013 merge status before any promotion.

### WATCH OUT FOR
Do not merge the dependent PR before accepting the IPC base, do not treat same-UID socket permissions as process sandboxing, do not pass access/refresh tokens or auth codes to QML, and do not enable company switching.

### CHECKLIST
- [x] Current #1013 and main/other PR ownership inspected; external Hospital-compatible
- [x] No-credentials fixed CLI reader, private runtime path, read-only socket
- [x] QML visibility/clear lifecycle, data-schema validation, disabled switcher
- [x] Real subprocess IPC, QML JS logic and existing Social settings tests authored
- [x] Exact-head CI passing (21/21 GitHub Actions runs on pre-handoff revision)
- [ ] Independent security / UI lifecycle review
- [ ] Operator acceptance and actual Quickshell visual proof
- [ ] Approved real host, isolation, OS vault and server-side authorization

### NEXT
Verify CI, review #1013 then the stacked viewer PR. With separately authorized local testing, validate native Quickshell loading and automatic clear on logout/host stop/expiry/lock. Only after independent security review and real HTTPS IdP host deployment may the Social Organizations panel consume actual company memberships.

### DECISIONS
No user desktop changes, production host, saved secrets, account onboarding, real organization switching, local process restart, merge or production activation. QML remains a non-authoritative read-only consumer.
