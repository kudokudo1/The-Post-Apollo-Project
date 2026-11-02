# 🏥💜 TASKS M12s // Isolated Native Smoke of the Actual To-Do Store

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ROOM:** TASKS JSON writer continuity  
**ASSIGNMENT:** Prepare an operator-controlled native no-regression test of the actual production store, after merged M12r #1005  
**DOCTOR / PROVIDER:** external Hospital-compatible ChatGPT / OPEN AI // CHATGPT  
**CONNECTION:** external; no verified live Hospital registration  
**BASELINE:** main aa408cac904c3a768d6879c3729c0657fdcbbdea on 2026-11-02  
**CLASSIFICATION:** unmounted, manually launched disposable native test; SOURCE CI only until operator observation

## IMPLEMENTATION

Earlier M12n's standalone native observer reused a synthetic M12i FileView and OS host. It did **not** load the actual production To-Do singleton. M12r fixed a contradiction inside the real store's *inactive* ticket admission using a Node VM, still without running native Qt.

M12s adds a small standalone root configuration **TaskNativeStoreSmokeM12s.qml** importing **qs.services.hub**, which resolves the actual shared **ApolloHubTodoStore**. It does not copy that singleton or create another FileView. It is not imported from shell.qml and launches only on explicit operator command.

The root's Quickshell pragmas override the data and state directories:

- DataDir: $BASE/post-apollo-m12s-fixture
- StateDir: $BASE/post-apollo-m12s-state

When launched using the provided *temporary* XDG_DATA_HOME and XDG_STATE_HOME, the store's built-in storagePath points to **$XDG_DATA_HOME/post-apollo-m12s-fixture/apollo-hub-todo-v1.json**, never the live shell's ordinary dataDir. The panel shows its actual resolved data directory and file path so the operator can verify before clicking.

For an explicit disposable mutation, the panel requires BOTH:

1. Quickshell.dataDir ends with /post-apollo-m12s-fixture AND the actual singleton storagePath exactly equals that directory plus /apollo-hub-todo-v1.json.
2. POST_APOLLO_M12S_DISPOSABLE=1 in the test process, with the real readonly guardedWriterEnabled, ticketProducerEnabled and independentlyAuthenticatedTicketReceipt all false, and a ready/empty store.

The panel provides three manual actions: CHECK TICKET OFF (the disabled submit must refuse), ADD FIXTURE TASK (only calls the existing legacy addTask on that disposable path), and RELOAD FIXTURE (existing reloadFromDisk). No automatic mutation occurs at startup. This does **not** activate the new ticket producer, test native *ticket* callback order, or prove fsync/OS-writer identity.

The new tests/tasks/test_task_real_store_native_smoke_m12s.cjs checks the root path/guard/static single-writer invariants and runs its actual JavaScript button-method bodies in a memory-only Node VM. It does **not** run Quickshell.

## HOW TO USE

**NO action on the operator's local machine has been performed by this PR.** Following steps are a proposal for a separately approved, deliberate native test, not permission to run them automatically.

1. After operator review/merge and an ordinary operator-controlled source update, inspect the actual installed git state and verify that the file exists. Do not replace the live store or restart the running Quickshell.
2. In a terminal inside the updated repository, prepare a fresh private disposable root. These commands create files only in a new temporary directory:

~~~sh
m12s_native() {
    local repo="$HOME/.config/quickshell"
    test -f "$repo/TaskNativeStoreSmokeM12s.qml" || {
        echo "M12s harness not installed"; return 1
    }
    m12s_tmp="$(mktemp -d -t post-apollo-tasks-m12s-XXXXXXXX)" || return 1
    chmod 700 "$m12s_tmp" || return 1
    mkdir -m 700 "$m12s_tmp/share" "$m12s_tmp/state" || return 1
    printf 'TEST ROOT // %s\n' "$m12s_tmp"
    env XDG_DATA_HOME="$m12s_tmp/share" \
        XDG_STATE_HOME="$m12s_tmp/state" \
        POST_APOLLO_M12S_DISPOSABLE=1 \
        qs -p "$repo/TaskNativeStoreSmokeM12s.qml"
}
m12s_native
~~~

The $HOME/.config/quickshell checkout is an expected installation example, **not a verified location**; use the actual installed repository directory if different. Do not paste the commands into the same shell that launches the live Quickshell. The environment variables are scoped to the isolated qs process. This should create a distinct process and data path; its actual resolved path must be inspected on the M12s panel before any mutating button is clicked.

3. On the standalone M12s window, confirm **ISOLATION VALID**, **GATES DISABLED**, and SOURCE ending in **post-apollo-m12s-fixture/apollo-hub-todo-v1.json** under the freshly created temporary root. If anything differs, **do not click ADD or RELOAD**; stop this separate test instance.
4. Press **CHECK TICKET OFF**. Expected: PASS / TICKET ADMISSION REFUSED; no fixture file should be created by that action.
5. Press **ADD FIXTURE TASK** once. Expected: REQUESTED then the real store changes from empty to ready, TASKS total 1; do not interpret REQUESTED alone as saved. Press **RELOAD FIXTURE**, confirm the count remains 1.
6. After exiting the separate qs test instance, from the original terminal inspect the private fixture (not real tasks) with:

~~~sh
fixture="$m12s_tmp/share/post-apollo-m12s-fixture/apollo-hub-todo-v1.json"
test -f "$fixture" && sha256sum "$fixture"
python3 - "$fixture" <<'PY'
import json,sys
with open(sys.argv[1], encoding="utf-8") as f:
    doc=json.load(f)
print("VERSION",doc.get("version"),"TASK COUNT",len(doc.get("tasks",[])))
PY
~~~

Observe/redact logs and path if needed. **Do not run rm -rf, reset, quit all Quickshell processes, change production flags, or copy fixture data into the real store.** Any cleanup of the temporary directory is a separate local-write action under operator control.

### What this native test can and cannot establish

Passing proves that the actual singleton can load and perform the old FileView-backed add/reload path in a separate native Quickshell instance. It also shows that the *disabled* ticket submit refuses in that instance. It does **not** test enabled ticket writing, crash-safe persistence, exact-source baseline checks, backup restoration, callback identity or producer/consumer cutover.

## VERIFY

- Source-scoped tests: Node VM guards, path, no automatic write, manual route behavior, no second production writer, old M12r and M12q safety regressions.
- Pending: GitHub CI on final head and independent review; **actual native Quickshell run by the operator** and its observed fixture hash/count; production source-baseline and crash/recovery evidence.
- The Quickshell root data directory pragmas and qs -p syntax are documented by upstream Quickshell, but the operator's installed version and actual test file path must be checked directly.

## WATCH OUT FOR

- New QML is not mounted. Merely merging it does **not** perform native acceptance or change the current To-Do window.
- Starting the test instance writes Quickshell state/log files and ADD writes a synthetic JSON file under the new temporary XDG root. This local action must be explicitly approved and initiated by the operator.
- A separate process does not magically enforce OS-level protection against a malicious same-UID process. This is benign-fixture isolation only.
- The existing single store still has watchChanges:false. The future enabled ticket path needs a pre-write source identity check, backup/recovery strategy, and separately authorized durability/acknowledgment contract.
- If the test exposes a Qt import, path or native callback problem, report and correct that specific issue; do not adjust the live shell just to make the test pass.

## CHECKLIST

- [x] Verify M12r merged; inspect current Syntagma, TASKS source and ownership
- [x] Reuse the real singleton rather than introducing a duplicate FileView
- [x] Isolate Quickshell data/state paths and gate every manual fixture write
- [x] Add extracted-function source guard tests and scoped CI
- [ ] CI green, independent review, mergeability confirmed
- [ ] Operator review and merge
- [ ] Operator-approved native test with a fresh disposable root
- [ ] Verify actual path, ticket refusal, legacy save/reload and fixture hash
- [ ] Separate source-baseline, backup/recovery and native-ticket acceptance
- [ ] Explicit approval before any production ticket/Hub enablement

## NEXT

Review source CI and merge only with operator approval. Run isolated native fixture observations. After successful source and native evidence, move to an **M12t local source-baseline and recovery contract** without assuming that a privileged broker is justified or activating any new production writer.

## DECISIONS

**Preserved:** M12l local-first single logical writer, the existing Quickshell FileView, the nine live mutation methods, legacy behavior and hard-disabled ticket/guarded gates.  
**Added:** a test-only explicit standalone native observation window and source CI.  
**Not authorized:** local install/restart, live task-data read/write, a second writer, new broker, SQLite migration, GitHub sync, activating tickets, PR merge or final production acceptance.
