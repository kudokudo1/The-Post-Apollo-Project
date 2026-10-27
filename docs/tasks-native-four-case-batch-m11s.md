# 🏥💜 TASKS M11s // Four-case native acceptance preparation and read-only summary

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room:** TASKS JSON writer continuity, successor to M11r PR #865  
**Worker:** OPEN AI // CHATGPT, external Hospital-compatible, not live Hospital-registered  
**Starting source:** main at `02dcea8b3aebc7970f174d95837de6421f64a617`, after independently verifying M11r merged  
**Scope:** new GitHub-only, **opt-in** synthetic fixture helper; no production/QML/host modifications, local execution, migration or activation.

## IMPLEMENTATION

M11q and M11r expose four separate synthetic native fault injection points, with M11r's single-fixture read-only journal inspector. M11s reduces repetitive fixture preparation while preserving the key safety requirement: **one fresh, private journal per fault**.

`tests/tasks/fixtures/TaskNativeFaultMatrixM11s.py` provides two manual subcommands:

- `prepare --private-parent ...`: only when *explicitly invoked*, creates a fresh random `m11s-native-*` folder under an already existing 0700, current-user-owned parent, with exactly four new private subdirectories. It calls the **existing** `TaskJsonGateSeedM11m.py` once per case. It prints the four absolute **synthetic** file paths needed for QML's input field. It never overwrites an old run, reads user's task data, bootstraps a host journal, launches Quickshell, or cleans any folder.
- `inspect --suite-dir ... [--after-existing]`: opens each of those four v2 journals through the **existing** `TaskNativeFaultInspectorM11r.py` in read-only mode, then returns one path-redacted JSON summary. `NOT_RUN` is never counted as acceptance. `PASS` means the corresponding *file/journal snapshot* matches its expected synthetic fault, **not** that the QML callback happened. The `nativeCallbacksObservedByThisTool` and `productionWriterAuthorized` fields are always `false`.

The four case labels are `AFTER_RESERVE`, `AFTER_SAVED`, `AFTER_READBACK`, and `AFTER_SETTLEMENT`. Their expected durable source/histories remain exactly M11r's existing contract.

No changes to `shell.qml`, production `ApolloHubTodoStore.qml`, M11m QML or test host, and no previously created M11n fixture.

## HOW TO USE

**This describes a future operator-approved, local disposable test. Nothing has been run on the operator's Fedora desktop by M11s.** Use a *separate clone* of the merged GitHub source; do not reset or pull into the operator's modified `~/.config/quickshell`.

Once at that separate clone and after explicitly creating a new private empty parent yourself (0700), run:

```sh
python3 -B -I tests/tasks/fixtures/TaskNativeFaultMatrixM11s.py \
  prepare --private-parent "/ABSOLUTE/PRIVATE/EMPTY_PARENT"
```

The tool prints a fresh `suite` path and four absolute synthetic paths. **Keep that output private**. For each case, launch only the standalone QML test harness (`qs -p /ABSOLUTE/CLONE/TaskJsonGateHarnessM11m.qml`), enter the case's matching printed test file, click **NEW TEST**, cycle **ARM FAULT** until it displays the intended case, then click **INCREMENT** **once**. Stop/exit the standalone test only, not the production Quickshell shell. Do not use any actual task file or rebootstrap an already interrupted journal. Repeat in the *next fresh case folder*, preserving the original journal.

After exiting all four test-host processes, **inspect the four journals without modifying them**:

```sh
python3 -B -I tests/tasks/fixtures/TaskNativeFaultMatrixM11s.py \
  inspect --suite-dir "/ABSOLUTE/NEW/m11s-native-xxxxxxxx"
```

To check restart fencing, separately attach `EXISTING` to each previously interrupted synthetic fixture in a new standalone harness process. Each case must display `RECOVERY_REVIEW` and refuse further stage admission. Stop the fresh harness after each, then run:

```sh
python3 -B -I tests/tasks/fixtures/TaskNativeFaultMatrixM11s.py \
  inspect --suite-dir "/ABSOLUTE/NEW/m11s-native-xxxxxxxx" \
  --after-existing
```

The aggregate JSON output is safe to share without the preparation paths, although the visible QML event summary is still necessary to support any native callback acceptance. `complete:true` means **all four file/journal patterns matched**. It never sets the `nativeCallbacksObservedByThisTool` field true or asserts end-to-end native safety. Preserve a local copy of the QML on-screen event tags and error/status for each case; do not upload private paths or actual task files.

If any result is `FAIL`, `REFUSED`, or `NOT_RUN`, stop that case. No automatic retry, repair, force, backup overwrite, cleanup or rearm is provided.

## VERIFY

`tests/tasks/test_task_native_fault_matrix_m11s.py` exercises:

1. One-time private synthetic seed for four separate v3 JSON copies, with 0600 files and 0700 folders.
2. Preparation never makes a case look passed or creates a host journal.
3. Temporary simulated reserve/save/settle for each case and the four expected M11r read-only journal states, including fresh-owner `RECOVERY_REVIEW` after reopening.
4. Altered source/counter failure, unsafe path/refusal, stdout privacy and a CLI summary containing no private paths.
5. Preservation of source bytes across read-only aggregated inspections, including the independent initial backup.

GitHub CI also runs M11r session transport, M11q pure callback guard, M11p durable journal/SIGKILL, M11o JS/Python policy parity and M11d single-writer inventory. This does **not** execute the Quickshell native buttons or physical power-loss events.

## WATCH OUT FOR

- The preparer makes fresh disposable files **only if the operator explicitly executes it**. No local filesystem mutations or processes have occurred as a result of this GitHub PR.
- Each case needs separate actual QML events; a synthetic Python-mocked journal pass cannot be marked native-accepted.
- M11r session tokens correlate one host process but cannot prove executable identity. QML FileView callbacks carry no durable stage metadata, so late callbacks and host impersonation remain production-acceptance risks.
- The underlying SQLite journal is test-only admission history; not a production task SQLite writer.
- Do not `pkill -x quickshell`, modify the live task JSON, pull/reset the dirty local worktree, delete old private test folders, or assume a green CI grants authorization to deploy.
- No operator native test evidence has been uploaded, and no local machine operation is authorized by this milestone.

## CHECKLIST

- [x] M11r reached GitHub main and code blobs verified
- [x] Source-only batch preparation reusing existing M11m one-time seeder
- [x] Four-case read-only summary reusing M11r inspector without changing durable authority
- [x] Privacy, new-folder safety, reject/NOT_RUN and fresh-owner tests
- [ ] GitHub CI on M11s draft head verified
- [ ] Actual four native QML fault runs, distinct private directories, and pre/post restart journal inspections
- [ ] Independent native callback provenance and production host trust-chain review
- [ ] Separate production host/writer integration authorization and rollback/activation acceptance

## NEXT

After code review, native fault observations can use this opt-in test suite without four rounds of handwritten fixture setup. The next decision is **whether native error handling and durable restart fencing are acceptable**, not whether SQLite or guarded TASKS should be activated.

## DECISIONS

M11s is a review-only GitHub change. `guardedWriterEnabled: false` stays in place, the original JSON FileView remains the sole live writer, and there is no operator-local mutation, production activation, data migration, rollback or live Hospital registration. Merge requires the operator's separate approval.
