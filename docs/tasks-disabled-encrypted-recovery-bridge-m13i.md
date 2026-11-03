# 🏥💜 TASKS M13i // Disabled Native Quickshell Encrypted-Recovery Bridge

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity / encrypted recovery  
**ASSIGNMENT //** First live-source QML seam for recovery *provider status only*, with all draft encryption/recovery authority disabled  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor; no live Hospital registration verified  
**GITHUB BASE //** `c8470ece9d6b315882ba9c58edb3b2b1c072246a` on November 3, 2026  
**SCOPE //** Remote repository branch, read-only status host, one disabled QML child under the existing singleton, source tests, standalone panel and CI. No local machine writes, keyring changes, Quickshell restart, production draft storage, ticket enablement, migration or PR merge.

## IMPLEMENTATION

### Evidence and ownership checkpoint

- [M13h PR #1103](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1103) merged at `768b3d558b6e1146638e341c220909947344bd93`. Its exact native disposable GNOME Keyring test passed GitHub CI. The operator subsequently ran the reviewed disposable harness on Fedora and reported **`M13H_NATIVE_ENCRYPTED_RESTART_PASS`**. That is observed synthetic actual-Fedora, same-user-session/process-restart evidence, **not** full machine reboot or live TASKS data recovery.
- The previously read-only Fedora session showed `/usr/bin/gnome-keyring-daemon --daemonize --login` owning `org.freedesktop.secrets`. No continuing PID or unlocked-state assumption is made here.
- `ApolloHubTodoStore.qml` is the **sole real TASKS FileView writer** and continues to own existing nine mutations for Hub, Details, Planner and Projects. `guardedWriterEnabled:false`, `ticketProducerEnabled:false` and `independentlyAuthenticatedTicketReceipt:false` remain unchanged. No competing TASKS PR was open at branch creation.
- M12l specifies one logical local task coordinator; M13f/M13g/M13h prove disposable encryption/keyring capability, but **do not** establish a trusted persistent key identity, consent, or complete authenticated recovery control.

### Changes made

**A. Read-only provider status host:** `services/hub/TaskRecoveryProviderHostM13i.py`.

With the explicit `--probe` argument, it calls the **D-Bus daemon** at `org.freedesktop.DBus.NameHasOwner("org.freedesktop.secrets")`, never the Secret Service object itself. It returns one fixed, bounded JSON status envelope with `SERVICE_ACQUIRED`, `SERVICE_NOT_RUNNING`, `PROBE_TOOL_MISSING`, `SESSION_BUS_UNAVAILABLE` or `UNEXPECTED_RESPONSE`. It refuses any other argument without probing. It cannot auto-activate, inspect, read or modify secrets, unlock keyrings, encrypt/decrypt drafts, or write disk files.

It always sends `keyringUnlocked:false`, `recoveryEnabled:false`, `writeAuthorized:false`, `persistAuthorized:false`, `decryptAuthorized:false` and `productionActivation:false`, even if an owner name exists.

**B. Actual QML/Process bridge:** `services/hub/TaskEncryptedRecoveryBridgeM13i.qml`.

This `Scope` contains a non-running `Process` and `SplitParser` with strict JSON reply validation. **Loading it does not execute any host or probe.** Explicit `inspectProvider()` launches only the read-only Python host in a subprocess and records whether an existing Secret Service currently owns its D-Bus name. Unexpected host fields, missing responses, malformed output, mismatched owner bit, abnormal exit or suggestions that real keys are already trusted are refused. A valid owner signal **cannot** change any recovery permission. The bridge offers no FileView, secret-tool invocation, unlock method, draft payload, export, delete or task-write method.

**C. TASKS singleton binding:** `services/hub/ApolloHubTodoStore.qml`.

This is the first intentional shared QML integration into the existing production TASKS coordinator. It instantiates **one** M13i bridge as a child, exposes read-only `encryptedRecoveryProviderStatus` and `encryptedRecoveryProviderPresent`, and provides `inspectEncryptedRecoveryProvider()` as an explicit read-only discovery call for a future UI. Its other new flags `encryptedRecoveryEnabled`, `encryptedRecoveryStorageAuthorized` and `encryptedRecoveryUnlockAuthorized` are all literal **false**.

This does **not** add a second FileView or a persistent draft store, alter existing `stage()`/ticket behavior, or trigger a check automatically. Existing consumer surfaces are not changed.

**D. Standalone inspection panel:** `TaskEncryptedRecoveryHarnessM13i.qml`.

A separate, unmounted Post-Apollo-colored Quickshell `PanelWindow` shows `RECOVERY // DISABLED`, the current provider status, and one **CHECK PROVIDER** button calling only `bridge.inspectProvider()`. It is never imported by `shell.qml` or the running Hub UI. A future explicit native smoke test may launch it from an independent repository checkout; **this PR does not run or install anything locally**.

**E. Regression verification:** `tests/tasks/test_task_encrypted_recovery_provider_m13i.py` and `tests/tasks/test_task_encrypted_recovery_bridge_m13i.cjs`, with scoped CI `.github/workflows/tasks-disabled-recovery-bridge-m13i.yml`.

The Python tests simulate presence, absence, missing gdbus, bus errors and malicious outputs, verifying exactly one read-only owner query. Node tests enforce disabled gates, one original FileView and `todoFile.setText()`, source-only allowed QML bridge operations, nonimport of the standalone panel, and unchanged nine task mutation methods.

## HOW TO USE

No desktop commands or user actions are needed for this repository milestone.

When a future operator-approved *separate* disposable native Quickshell smoke is scheduled, the standalone entry point is:

```bash
quickshell -p /absolute/path/to/isolated-checkout/TaskEncryptedRecoveryHarnessM13i.qml
```

Do not use the live `~/.config/quickshell` worktree for a checkout or reset. The panel is not needed for normal TASKS and **will never enable recovery**. The only active button is a D-Bus name-owner check. No secrets should be entered or displayed.

Programmatically a future authorized QML consumer can *read* `ApolloHubTodoStore.encryptedRecoveryProviderStatus` or explicitly invoke `ApolloHubTodoStore.inspectEncryptedRecoveryProvider()`. That is service discovery only, **not** a write, authentication or unlock API.

## VERIFY

In GitHub CI:

- `python3 -m unittest -v tests/tasks/test_task_encrypted_recovery_provider_m13i.py`
- `node --test tests/tasks/test_task_encrypted_recovery_bridge_m13i.cjs`
- Default no-action host JSON check.
- M13h disposable harness source guard and M11d sole-writer inventory.

**CI scope:** Source and Python behavior tests, not a native Fedora Quickshell parse/runtime verification. Actual desktop native startup and UI button behavior must be checked separately before the feature is claimed accepted. Owner presence does not mean the keyring is unlocked, and it never supplies a draft decryption key.

## WATCH OUT FOR

- This is **a real disabled QML integration**, not live encrypted draft recovery. A compiled but disabled component in the shared TASKS singleton is not user opt-in, full native acceptance or permission to persist drafts. It must remain inert at load time.
- The extra `Process` is read-only and dormant until the explicit status check. A `Process.exec` probe is not evidence of application-specific authorization.
- All earlier M13f/M13g/M13h encryption/keyring tests remain isolated synthetic fixtures. Reusing their scripts against actual task content is **not** authorized.
- The next native QML smoke should verify startup, provider status and abort/restart without touching the live worktree. A static test cannot prove the QML module loads correctly on this specific Fedora/Quickshell runtime.
- GNOME Keyring can provide keys to eligible same-user clients. Decide actual user-unlock requirements, keyring collection selection, app identity, key backup/loss and replay/rollback checks separately.
- Do not infer that `SERVICE_ACQUIRED` verifies the presence of a recoverable key, unlocked collection, trusted execution or valid draft snapshot.
- Do not pull/reset the operator's existing dirty Quickshell checkout, restart Quickshell, add a new FileView, enable the producer, or migrate real data for M13i.

## CHECKLIST

- [x] Recheck M13h merge, Fedora native test checkpoint, Syntagma, active TASKS ownership and GitHub main
- [x] Reuse existing D-Bus name-owner probe concept without keyring mutations
- [x] Implement dormant QML `Process` boundary with strict no-power status reply
- [x] Bind status to the existing singleton with all new and old writer gates `false`
- [x] Add unmounted read-only Quickshell inspection panel
- [x] Add Python, Node and prior-gate CI tests
- [ ] CI complete / independent source review
- [ ] Operator PR review/merge and separate native Quickshell inspection
- [ ] Native Fedora Quickshell startup and click smoke (disposable checkout, explicit approval)
- [ ] Design actual key-provider authorization, consent state, encrypted draft transaction, rollback prevention, user-visible recovery
- [ ] Production activation and final operator acceptance

## NEXT

After green source CI and operator review, perform a **disposable native Quickshell smoke** using the standalone status-only panel, without modifying the active configuration. Once the QML Process/JSON callback is verified on Fedora, design and test a **separately authorized opt-in, encrypted-draft host protocol**: explicit consent before key creation, proper stage/source owner binding, authenticated key release, checked last-confirmed source, durable encrypted checkpoint and read-only recovery review. No activation or real draft capture until that security contract and native evidence are accepted.

## DECISIONS

**Selected:** opt-in encrypted draft recovery after application restart (operator direction); GNOME Keyring verified for disposable synthetic key roundtrip on Fedora; M12l local single coordinator maintained.  
**Implemented in M13i:** read-only dormant shared QML provider seam, unmounted provider-status panel and bounded host probe.  
**Still undecided:** production app unlock, key provider permissions/collection, key backup/rotation, real encrypted draft persistence path, consent UX, replay defense, export/delete and retention policy.  
**Not authorized or performed:** local machine changes, new production writer, persistent personal draft, keyring modifications, startup probe, live UI mount, ticket enablement, production migration, PR merge or live Hospital registration.
