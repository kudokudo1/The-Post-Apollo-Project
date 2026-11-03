# 🏥💜 TASKS M13l // Native Quickshell Encrypted-Draft IPC Acceptance

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS writer continuity / opt-in encrypted draft recovery  
**ASSIGNMENT //** Native Quickshell `Process` → stdin JSON → isolated GNOME Keyring Node host → stdout JSON → QML verified exit  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor; no live Hospital registration verified  
**BASELINE //** GitHub `main` `30289136998b9fb388180694c6d90e487724835a` on November 3, 2026  
**PERMISSION //** Repository-only tests/docs/CI; **no local workstation modifications**, actual user keyring access, global desktop restart, live TASKS mutation, or PR merge.

## IMPLEMENTATION

### Recovered verified state

- M13h [PR #1103](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1103) is merged and operator reported `M13H_NATIVE_ENCRYPTED_RESTART_PASS` from the actual Fedora login session using disposable fake data. This validates fresh-process retrieval, not full reboot.
- M13i [PR #1118](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1118) is merged. The unregistered QML type initially blocked Quickshell startup; corrected by [PR #1120](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1120).
- M13j [PR #1141](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1141) is merged. Native Fedora `Configuration Loaded` and screenshot of `PROVIDER // SERVICE_ACQUIRED` confirmed the read-only QML → Python → D-Bus status path.
- M13k [PR #1151](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1151) is **merged** at `554cfe7ec293b1332f5cffe6f4c0e94f5474f52f`; its 47/47 GitHub checks passed. The real one-shot Node host encrypts/decrypts synthetic drafts via a private GNOME Keyring/DBus and returns only status JSON. But M13k CI only simulated QML stdin; it did not launch native Quickshell.
- The authoritative real TASKS source is still `services/hub/ApolloHubTodoStore.qml` with one `FileView`, one `todoFile.setText()`, unchanged public TASKS methods and literal-false `guardedWriterEnabled`, `ticketProducerEnabled`, `independentlyAuthenticatedTicketReceipt`, `encryptedRecoveryEnabled` and `encryptedDraftHostEnabled`.
- No competing open TASKS PR found on GitHub preflight. Syntagma `AGENTS.md` and Hospital OPERATE permissions were rechecked.

### M13l implementation

1. `TaskEncryptedDraftAutoHarnessM13l.qml`: a **standalone, windowless Quickshell `Scope`** that has only the already-reviewed M13k bridge. On load it checks the existing private-test environment flags, explicitly starts the **synthetic** QML Process and waits for one strict status response. It prints a fixed `M13L_NATIVE_QML_IPC_PASS` marker **only after** `busy=false`, `syntheticVerified=true`, the exact M13k encryption status and all real task-write/persist/activation flags remaining false. Otherwise it prints `M13L_NATIVE_QML_IPC_REFUSED`; it has a 45-second fail-closed timeout and then calls `Qt.quit()`. It does not instantiate the real TASKS singleton, a `PanelWindow`, or actual personal data.
2. `tests/tasks/tools/task_m13l_native_ipc.sh`: a read-only `--preflight` validates all fixture files, exact `qmldir` registration, and pinned Git blob hashes for the reviewed M13k QML bridge, M13l test scene, M13k Node host, M13g encryption/Secret Service fixture and M13f AES-GCM fixture. It refuses missing, symlinked or locally edited files; it never tries to repair or pull the user's local Quickshell checkout.
3. **Operator-initiated `--run`** calls `dbus-run-session` and `--inside-private-test` to create a separate D-Bus session. The private runner insists on a newly started `unix:path=/tmp/dbus-...` socket, not `/run/user/<uid>/bus`, uses a new 0700 private `/tmp/postapollo-m13g-m13k-XXXXXXXX` HOME and private XDG data/config/cache directories, starts GNOME Keyring with a **synthetic test-only password via stdin**, then starts `quickshell -p TaskEncryptedDraftAutoHarnessM13l.qml`. It keeps the user's normal `XDG_RUNTIME_DIR` for the existing Wayland compositor but never invokes `shell.qml`, live TASKS, real user keyring or personal draft.
4. The runner accepts success only if the **actual native QML** prints `M13L_NATIVE_QML_IPC_PASS`, the separate Quickshell instance exits successfully, the synthetic encrypted file no longer exists and the exact M13g disposable test Secret Service item is absent. It reports `M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS` only then. Other returns are refusal. A private log stays only in newly created disposable HOME; the wrapper cleans that directory on exit.
5. `tests/tasks/test_task_native_ipc_m13l.cjs`: CI uses copied synthetic source files to test preflight PASS, wrong registration, missing files, source hash mismatch, and direct `--inside-private-test` refusal on a real-login-style bus. It enforces zero production writer/file changes.
6. The GitHub workflow performs Qt QML **syntax parsing**, the full deterministic source/guard tests, a **fake-shell-only** isolation plumbing test (marked `M13L_FAKE_SHELL_ISOLATION_ONLY_PASS`), and reruns M13k's real private keyring encrypted IPC independently. The fake Quickshell result does **NOT** count as native QML acceptance.

All M13l additions are source and test-only. No existing M13k bridge, host, production singleton or `qmldir` changes are made. This milestone must not accidentally repeat the M13i missing type registration issue.

## HOW TO USE

**No desktop test has been performed by this browser worker.** If the operator approves a disposable native Fedora test, use a separately reviewed source snapshot or a temporary checkout, not a `git pull`/reset of the dirty `~/.config/quickshell` tree.

From a reviewed checkout of the M13l commit (or after a separately authorized merge):

```bash
bash tests/tasks/tools/task_m13l_native_ipc.sh --preflight .
```

This only reads source files, checks the existing M13k `qmldir` registration and hashes. It produces `M13L_REVIEWED_SOURCE_READY` or a fixed refusal. It makes no local writes or process/keyring changes.

**Separately, only after explicit local-test approval**, execute:

```bash
bash tests/tasks/tools/task_m13l_native_ipc.sh --run .
```

This actually creates a temporary directory, D-Bus session, disposable GNOME Keyring item and encrypted fake file, starts an independent windowless Quickshell test instance, and removes only its generated temporary files. It does not touch the normal keyring or TASKS.

Expected final line if native Quickshell/Node/Keyring/cleanup all work:

```text
M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS
```

If `M13L_REFUSED_UNREVIEWED_SOURCE` appears, leave the local files alone and compare the differences or use a clean isolated checkout. If the launch fails, post only the fixed refusal marker; do not print the private log without reviewing its contents. This test requires existing `quickshell`, Node, Git, `dbus-run-session`, `gnome-keyring-daemon`, `secret-tool`, the standard Linux tools and an active Wayland session. No package installation is performed by the script.

## VERIFY

**CI scope:** Qt parser and fake executable launcher, not actual Quickshell Process callbacks. The real M13k host/keyring flow is independently re-exercised using a private bus. All source/negative cases must pass.

**Native acceptance scope:** actual QML `Scope` loads, starts the M13k Process and sends the fixed request; QML parses the returned JSON; independent process encrypted fake recovery succeeds; test key/file are absent after cleanup; panel/task source stays unchanged. The test is windowless, so terminal markers are the required visible proof. The QML process must exit instead of hanging or leaking a child.

A successful native M13l result would **not** prove a real TASKS draft can be persisted, authenticated user opt-in, whole-machine reboot retention, per-app keyring authorization, or rollback protection.

## WATCH OUT FOR

- The M13k `CI_ONLY` literal and environment variables are **test guards, not credentials or trusted authorization**, even if the native IPC passes.
- Quickshell can still produce normal runtime logs/instance metadata in `XDG_RUNTIME_DIR`; the test intentionally does not change the operator's compositor or log-in session D-Bus.
- `dbus-run-session` and private GNOME Keyring are ephemeral. Do not start this test directly on a normal `/run/user/<uid>/bus` session.
- A PASS marker from a fake Quickshell executable in GitHub CI is **not a native acceptance**. Native testing on Fedora must be separately observed.
- Do not run test harness against real drafts, task data or a previously created home directory; it must generate its private test home.
- This test does not grant native key-release or source-write authority. Remain on a draft PR until operator review; no production activation.
- The user has a dirty local Quickshell tree with several concurrent workstreams. No `git pull`, reset, checkout or automated source replacement in that directory.

## CHECKLIST

- [x] Recheck M13k merged, actual M13j native evidence, Syntagma, main and no competing open TASKS PR
- [x] Windowless autonomous QML acceptance scene with explicit status-only result
- [x] Separate private D-Bus/HOME/Keyring operator runner and read-only preflight
- [x] Pinned reviewed fixture sources, real-login-bus refusal, no live TASKS API or new writer
- [x] QML syntax/negative tests and fake launcher plus independent M13k host regression in CI
- [ ] M13l CI green, independent review and operator merge
- [ ] Operator approval and **actual native Fedora test**
- [ ] Native Quickshell status + test cleanup verified by terminal evidence
- [ ] Production draft authority, opt-in consent/permission, replay and rollback policy
- [ ] Separate production integration and final user acceptance

## NEXT

Complete CI, request operator review of M13l, then obtain explicit local test authorization and run the isolated Fedora acceptance test from a separate checkout. If native QML succeeds, scope M13m to a **disabled-only real-draft transaction design**, including explicit opt-in consent, trusted key release, a durable last-confirmed TASKS source revision, no stale restoration, atomic encrypted draft checkpoint, backup/recovery and retention/clear UX. Do not enable real draft writes in M13l.

## DECISIONS

**Verified:** M13h real Fedora disposable keyring, M13j QML read-only provider status, M13k real isolated Node host encryption.  
**Created:** M13l windowless QML native acceptance test and isolated runner in remote repository only.  
**Still unverified:** native M13l QML Process invocation, authenticated persistent user key access, real draft persistence or reboot recovery.  
**Not authorized/performed:** local machine modifications, live Quickshell restarts, real user keyring changes, second TASKS writer, production activation, PR merge, live Hospital role registration or operator final acceptance.
