# 🏥💜 TASKS M12f // Native Acceptance Preparation and Disposable Journal Evidence

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** TASKS JSON writer continuity  
**ASSIGNMENT:** M12f prepare an independently inspectable native-test source/journal evidence workflow, still isolated from production  
**WORKER:** External Hospital-compatible ChatGPT doctor; not registered in live Hospital  
**PROVIDER:** OPEN AI // CHATGPT  
**INSPECTED BASE:** GitHub `main` `2f89ac320f1ab911fc15986c668297ff6c3b2ef9` on October 31, 2026. Recheck branch and ownership before any later work.  
**CLASSIFICATION:** **GITHUB-ONLY TEST AND MANUAL NATIVE ACCEPTANCE PREPARATION; NATIVE ACCEPTANCE NOT EXECUTED.**

## IMPLEMENTATION

M12e introduced a pure test proving that native `FileView` callback tags do not have a uniquely authenticated stage identity, plus an unmounted observation window. M11g already provides a standalone `FileView`, a disposable Python host and a SQLite *authority* journal. M12f **reuses these** rather than creating another FileView or pretending a GitHub runner has observed a real Quickshell save callback.

### New implementation

- `TaskNativeCallbackHarnessM12f.qml` is a **root-level, unmounted wrapper** that instantiates existing `TaskNativeCallbackLabM12e.qml`. Locating the standalone config at the repository root preserves the existing M11g `Quickshell.shellPath("tests/tasks/fixtures/TaskFileViewOwnerHostM11g.py")` relative path. No additional QML FileView, Process, autorun, shell import, task writer, or on-login activation.
- `tests/tasks/fixtures/TaskNativeEvidenceInspectorM12f.py` is an importable and optional CLI post-run inspector. It accepts **only** an explicitly supplied absolute `m11e-fileview-test/fixture-only.json` under an owner-private directory. It checks private owner-only file metadata, refuses symlinks/hardlinks, rereads exact JSON bytes, and parses the original M11e v1 `fixture/revision/counter/marker` schema with duplicate-key refusal.
- The inspector also requires the existing `handoff-test.lock`, takes a **nonblocking exclusive advisory `flock`** to refuse if the cooperative M11g host is still running, and opens only the existing `handoff-test.db` with SQLite `mode=ro` plus `query_only=ON` to inspect the exact M10p v1 single-row `authority` schema. It never bootstraps a database or executes write SQL. SQLite itself may access sidecar WAL/SHM files during read; this is not an immutable offline-forensic imaging process.
- An optional operator-supplied list of **sanitized enum callback tags** may be evaluated for basic ordering. This is a *statement about observed tags*, not a trusted native trace, durable stage attribution, or OS-host attestation. The report contains counter, phase, epoch, pending boolean, simple expectation matches and provenance flags. It omits paths, task text, stage/owner IDs, hashes, environment data, source contents and secrets.
- Read-only source tests confirm root wrapper remains unmounted, production `guardedWriterEnabled: false`, one live FileView, nine existing TASKS mutations, no real task-path access, no native execution claimed. Disposable Python tests use the **original M10p `Authority`** for real synthetic SQLite state and verify active-owner lock refusal, source/journal mismatches, unsafe paths, malformed schemas, stale or out-of-order operator tags.

### Four evidence tiers

| Evidence tier | What it means | M12f status |
| --- | --- | --- |
| SOURCE | Code, QML imports, single-writer invariants reviewed on GitHub | Automated CI |
| SYNTHETIC OS | Disposable Python/SQLite fixture and lock inspected in Linux runner | Automated CI |
| NATIVE OBSERVED | Operator explicitly launched unmounted Quickshell M11g lab on private fixture and retained sanitized event observations | **NOT RUN / OPEN** |
| PRODUCTION ACCEPTED | Independently provisioned signed host, real-source permissions, stage-bound settlement, all nine M11t gates and separate operator activation approval | **NOT AUTHORIZED / OPEN** |

A completed callback chain does **not** by itself prove exact stage attribution. SQLite `authority` row in M11g contains a `pending_stage` and epoch, but a row alone has no signed receipt binding its stage to an independently authenticated native `FileView` event. M12f is an **acceptance preparation**, not closure of the `NATIVE_STAGE_ATTRIBUTION` production gate.

## HOW TO USE

**No desktop action required for this PR.** GitHub CI runs the inspector regression:

```sh
python3 tests/tasks/test_task_native_evidence_inspector_m12f.py
```

**Future manual native-test protocol, only after explicit operator approval for local test-file creation and starting the standalone Quickshell process:**

1. Inspect local `git status`, `quickshell --version` and current process state; do not pull/restart/kill an existing Quickshell session as an implicit step. Confirm the correct M12f commit is available locally and the disposable test path has no existing task data.
2. Create a **new private disposable** directory named `m11e-fileview-test`, with no symlinks and `0700` permissions; seed a new `fixture-only.json` using existing `tests/tasks/fixtures/m11e_fileview_fixture.py`. Do not use `Quickshell.dataDir` or `apollo-hub-todo-v1.json`.
3. From the repository root, **explicitly** launch the standalone config using the same pattern as the known M11g harness, `qs -p /absolute/repo/TaskNativeCallbackHarnessM12f.qml`. This must be a separate, voluntary native test, not a `shell.qml` edit or restart of the live shell. The config's root location is important to script resolution. Quickshell CLI behavior and QML compilation **are not verified by M12f GitHub CI**.
4. Enter the private fixture path and a synthetic writer identifier (8–96 approved ASCII characters). Use **NEW TEST**, then **INCREMENT** twice, checking two sequential observed chains with `FILE_SAVED`, `FILE_READBACK_OK` and `HOST_SETTLED`. Use **FREEZE**, then **STOP**. Redact user paths/IDs when reporting; preserve only allowed event tags, test counter, phase and non-sensitive diagnostics.
5. Once the standalone host is stopped, run `TaskNativeEvidenceInspectorM12f.py --fixture-file /absolute/private/m11e-fileview-test/fixture-only.json --expected-counter 2 --expected-phase FREEZE_REQUESTED` using a separately approved local command. Optionally include `--operator-native-tags STAGE_REQUEST,HOST_ADMIT,FILE_SAVED,FILE_READBACK_OK,HOST_SETTLED`, which is **operator-provided evidence only**. An active cooperating host refuses the inspection.
6. **Fresh-process recovery test:** close the standalone test instance, start a **new** isolated test instance and use **EXISTING** for the same disposable fixture. The original M11g bridge does not rearm a stopped object inside one QML session; a fresh instance is required. Expect `RECOVERY_REVIEW` without automatic new write admission. After stopping this second instance, rerun the inspector with `--expected-counter 2 --expected-phase RECOVERY_REVIEW`. Do not infer production eligibility from the resulting synthetic state.
7. Compare sanitized observations, exact synthetic source counter, and the SQLite epoch/phase. Record **PASS**, **FAIL**, **REFUSED**, or **NOT_RUN** separately for every step; do not translate a source-check PASS into a native acceptance PASS.

This is a **protocol for a later explicitly approved local run**, not a request to carry it out now. If Quickshell compilation or script resolution fails, report the error and preserve the disposable files. No automatic deletion or reset is authorized. A faulty fixture must not be repaired by pointing the test at a live source.

## VERIFY

- M12e PR #933 was confirmed as an ancestor of `main`, with no open competing TASKS PR or M12f branch during preflight.
- Production `ApolloHubTodoStore.qml` still has one `FileView` and `guardedWriterEnabled: false`; its save callback still uses legacy early publication.
- M12f CI runs the new disposable inspector tests, original M11g source/process tests, M12e native ambiguity suite, M11q deferred-readback checks, M11t production gates and M11d single writer audit. A green run **does not certify native execution**.
- No actual operator native results were gathered during this GitHub-only milestone.

## WATCH OUT FOR

- The same-user filesystem owner could replace or mutate files outside the cooperative M10p flock protocol. A lock and consecutive reads do not prevent hostile external writes, so the inspector is not production proof.
- SQLite `mode=ro` and `query_only=ON` prevent direct write SQL, but the SQLite library may touch WAL/SHM sidecars while reading. For power-loss/forensic evidence use independently retained stable copies after host exit and a separate approved protocol.
- This audit reports the M11g **SQLite authority journal**, not the M11l production-shaped journal or task-data migration database. It does not verify a production release signer or authenticate QML callback stage identity.
- `TaskNativeCallbackLabM12e.qml` is the original unmounted M12e lab, not a guaranteed working native binary. QML compilation and actual callback timing still require a deliberate local run.
- No source paths, task content, private identifiers or raw process logs should enter the PR, generated report, CI output or chat. Use sanitized enum tags only.

## CHECKLIST

- [x] Confirm merged M12e and current repository/ownership baseline
- [x] Audit original M11g/M10p native host, lock and authority journal schema
- [x] Add root-level standalone wrapper for existing lab/host relative paths
- [x] Add strict private post-run source and SQLite readonly evidence inspector
- [x] Add synthetic OS-authority, lock contention, source/schema/path refusal cases
- [x] Add provenance-safe CLI report and manual native acceptance contract
- [ ] GitHub CI verification and independent review
- [ ] Operator review/merge
- [ ] Separately authorized actual native Quickshell run; record outcomes
- [ ] Production source/host/callback binding, UI completion and guarded activation gates

## NEXT

Review M12f PR and CI. The **next decision is whether to authorize an isolated local native test**, not to activate the guarded writer. If native evidence is obtained, use it to design independent stage-to-source readback receipts, and retain the distinction between native observation and actual durable stage provenance.

## DECISIONS

**Implemented:** Standalone root launcher and test-only post-run evidence inspector plus CI regressions.

**Evidence limit:** CI may verify source and synthetic OS journal; **native observation remains NOT RUN** and **stage attribution remains NOT PROVEN**.

**Not authorized:** Fedora local edits/test launches, Quickshell restart, real TASKS access, trusted signing-key deployment, task migration, auto-recovery, merge, production activation or live Hospital registration.
