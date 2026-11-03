# 🏥💜 TASKS // M13j Native Quickshell Provider-Status Smoke

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity / opt-in encrypted recovery  
**ASSIGNMENT //** Restore and verify native M13i module loading and its standalone, read-only provider-status panel without touching production TASKS  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor; no live registration verified  
**GITHUB PRE-FLIGHT //** main `ea249bfe9954cefab564f073a2298acfbb7b6dd3` on November 3, 2026  
**SCOPE //** Repository-only smoke launcher, CI, source/parser tests, native operator runbook. No local checkout changes, GUI invocation on the operator desktop, keyring mutation or production activation.

## IMPLEMENTATION

### Recovery checkpoint

- M13h [PR #1103](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1103) merged; the operator reported `M13H_NATIVE_ENCRYPTED_RESTART_PASS` from Fedora on synthetic data. This is **process-restart** key retrieval evidence, not whole-system reboot or production drafts.
- M13i [PR #1118](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1118) merged but caused an actual Fedora Quickshell startup failure because `services/hub/qmldir` failed to register `TaskEncryptedRecoveryBridgeM13i.qml`.
- Corrective [PR #1120](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1120) merged at `4b39c7fc5d2df8cbaaf020067c12140044d9c8d3`, adding exact module export `TaskEncryptedRecoveryBridgeM13i 1.0 TaskEncryptedRecoveryBridgeM13i.qml` and a registration regression. **No successful local Quickshell startup after that fix has yet been reported.** Do not assume the local worktree has synchronized every file.
- GitHub main still has one `ApolloHubTodoStore.qml` `FileView` and one `todoFile.setText()`. Production `guardedWriterEnabled`, `ticketProducerEnabled`, `independentlyAuthenticatedTicketReceipt` and encrypted recovery/storage/unlock flags remain literal `false`.
- No competing open TASKS PR at M13j branch creation. Syntagma `AGENTS.md` and `OPERATE` permissions remain unchanged.

### Current implementation

1. `tests/tasks/tools/task_m13j_native_smoke.sh`: an explicit **`--preflight`** check that reads only the local module registry and verifies that the QML bridge, Python read-only host and standalone panel files exist. It uses `awk` (not the user's grep alias) and requires exactly one correct type registration. Missing files or entries return fixed refusal markers, with no attempt to repair, reset, pull, copy, or restart the existing shell.
2. **`--run`** executes a separate `quickshell -p <path>/TaskEncryptedRecoveryHarnessM13i.qml` process, but only after a successful preflight. Before executing any QML/Python, it calculates read-only `git hash-object` values of the three runnable files and compares them to the exact reviewed GitHub blobs. A dirty or unexpected local version returns `M13J_SOURCE_NOT_REVIEWED`, rather than running unreviewed code. The standalone panel is **not** the normal `shell.qml`.
3. `tests/tasks/test_task_native_smoke_m13j.cjs`: deterministic temp-directory tests for missing files, wrong/duplicate `qmldir`, invalid command, modified QML refusal and correct `-p` invocation of a **fake executable**, not the operator's Quickshell or keyring.
4. The CI workflow also runs Qt `qmlformat` **without `-i`** on the panel, bridge and existing singleton to catch QML syntax errors (Qt parser only; not a Quickshell module-runtime load). M13i module registration and M11d single-writer/public API tests remain in CI.

This is a **bounded native acceptance tool**, not another draft persistence or keychain implementation.

## HOW TO USE

The operator can inspect the live Quickshell tree with read-only commands now; no checkout or pull is necessary:

```bash
root="${XDG_CONFIG_HOME:-$HOME/.config}/quickshell"
for f in \
  "$root/services/hub/qmldir" \
  "$root/services/hub/TaskEncryptedRecoveryBridgeM13i.qml" \
  "$root/services/hub/TaskRecoveryProviderHostM13i.py" \
  "$root/TaskEncryptedRecoveryHarnessM13i.qml"; do
  if [[ -f "$f" ]]; then printf 'PRESENT %s\n' "${f##*/}"
  else printf 'MISSING %s\n' "${f##*/}"; fi
done
awk '/^TaskEncryptedRecoveryBridgeM13i / {print}' "$root/services/hub/qmldir"
```

If and only if all four files exist, the one exact registration is present and the local runnable files are reviewed, the operator may explicitly open a separate panel:

```bash
quickshell -p "$root/TaskEncryptedRecoveryHarnessM13i.qml"
```

The source-pinned M13j script is the preferred form **once this PR's script is available in a reviewed isolated checkout**, using:

```bash
bash tests/tasks/tools/task_m13j_native_smoke.sh --preflight /absolute/safe/quickshell-root
bash tests/tasks/tools/task_m13j_native_smoke.sh --run /absolute/safe/quickshell-root
```

The first command does not launch anything. The second launches the reviewed standalone panel only; it must be **explicitly invoked by the operator**. Do not run from a live checkout if the script is absent or copied from an unreviewed source. No `git pull`, `reset`, `checkout` or Quickshell restart is needed. Standard Quickshell logs/instance metadata may be written by the separately started process, but no TASKS record or keyring entry is touched by the reviewed panel.

Once open, click **CHECK PROVIDER**. Expect `PROVIDER // SERVICE_ACQUIRED` while GNOME Keyring owns the Secret Service name, or a fail-closed status if unavailable. `RECOVERY // DISABLED` and `WRITES // DISABLED` must remain displayed. Close the standalone instance with Ctrl+C in its launching terminal, not with `pkill quickshell`.

## VERIFY

Source/CI checks:

- `bash -n tests/tasks/tools/task_m13j_native_smoke.sh`.
- Node tests exercising actual launcher with fake tree and fake executable, including the exact reviewed blob pin before `--run`.
- Qt QML syntax parser against panel, bridge and TASKS singleton; this is **not** a native Quickshell runtime assertion.
- M13i module registration regression and M11d one TASKS writer/public API inventory.

Native operator acceptance remains separate:

- Correct module loads and standalone panel appears (no `is not a type` error).
- Button clicks and transitions from `NOT_CHECKED` to `SERVICE_ACQUIRED` (or a specific fail-closed status).
- No task data or keyring modifications, no production shell stop/reload, no recovery activation.
- A restarted standalone panel defaults again to `NOT_CHECKED`.

## WATCH OUT FOR

- **No native Fedora smoke has been run by this external worker.** A green CI test does not establish the operator's current QML type resolver or that PR #1120 was locally applied.
- If local files are missing or `qmldir` is unregistered, stop rather than calling `quickshell`; do not pull/reset a dirty user checkout. Prior local repair instruction for the exact `qmldir` entry remains applicable only when the bridge file exists and after local approval.
- If `M13J_SOURCE_NOT_REVIEWED` appears, an actual local file differs from reviewed GitHub content. It could be legitimate concurrent work. **Do not overwrite it.** Preserve and review its diff or use a separate isolated checkout.
- A `SERVICE_ACQUIRED` result proves only a running owner for `org.freedesktop.secrets`, not an authenticated user unlock, key availability or permission to decrypt real drafts.
- Quickshell native runtime must be validated before assuming app integration works. Existing `Scope`/`Process` QML syntax source checks do not prove runtime import resolution.
- This does not authorize real encrypted draft persistence, keys, migration, deletion, UI recovery, or a second canonical task writer.

## CHECKLIST

- [x] Recheck M13i and fix PR #1120 merged, current GitHub main, ownership and Syntagma
- [x] Add exact `qmldir`/file existence preflight with fail-closed markers
- [x] Pin executable QML/Python content on explicit standalone launch
- [x] Test fake launcher and all negative cases without real desktop
- [x] Add CI QML syntax parsing and old writer/API checks
- [ ] CI confirmed, independent review and operator PR review/merge
- [ ] Operator confirms local files and registration
- [ ] Operator launches the panel and clicks CHECK PROVIDER; terminal evidence
- [ ] Native Fedora acceptance, then separately authorized encrypted draft integration

## NEXT

If local registry and native panel pass, report **M13j Fedora runtime accepted**. Then scope M13k: a disabled-only encrypted-draft host protocol with operator consent, keyring retrieval, authenticated stage identity, replay/rollback protection and failure isolation. Do not turn on source writes or real draft capture until security and UI acceptance are explicit.

## DECISIONS

**Accepted:** prior disposable GNOME Keyring capability and opt-in encrypted recovery as the future direction.  
**Implemented here:** safe, content-pinned standalone native verification path.  
**Not yet verified:** local post-hotfix Quickshell startup, native UI click, system-reboot recovery, production authority and actual task draft recovery.  
**No local writes made by worker;** no live Hospital registration, local git manipulation, keyring changes, Quickshell restart or PR merge authorization.
