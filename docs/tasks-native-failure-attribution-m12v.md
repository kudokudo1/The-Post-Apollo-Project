# 🏥💜 TASKS M12v // Native Self-Report Failure Attribution

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Diagnose the real M12u operator failure without changing the live writer  
**WORKER //** External Hospital-compatible doctor, OPEN AI // CHATGPT; no verified live registration  
**INSPECTED BASE //** GitHub `main` at `a272b3851ffcb06a73bcea716bc30506ec96ef67` on 2026-11-02  
**STATUS //** Source-only diagnostic repair. Actual native cause still unknown until re-run.

## IMPLEMENTATION

The operator executed the merged M12u runner on Fedora and reported:

```text
M12u // Starting a separate disposable Quickshell test
M12u // Live shell and live tasks are not targeted
M12u // FAIL // NATIVE_STAGE_SEQUENCE_MISSING
Native or disk evidence was incomplete; no success assumed
```

**Only this is proved:** the automatic runner did **not** receive a complete expected sequence. It does not establish that the live To-Do store failed, which native event did not occur, whether QML loaded, or whether synthetic disk data was created. Earlier M12s *did* yield a disposable v3 JSON file with one task after exit; that partial evidence remains valid, but it does not cover ticket refusal or a native reload callback.

The error reporting in M12u obscured the real failure: `evidence()` checked for missing stages *before* inspecting any `M12U_RESULT|FAIL|REASON` marker. Any native fail reported after a partial sequence therefore became the generic `NATIVE_STAGE_SEQUENCE_MISSING`.

M12v is a narrow diagnostic source patch:

- **Native terminal failure takes priority.** `evidence()` now first detects ambiguous duplicate terminal messages, then preserves the explicit native FAIL reason, then reports incomplete stage order. PASS remains contingent on all four stage markers, one successful native result, and independent test-file re-read. It never changes a FAIL to PASS.
- **Actionable summary instead of hiding logs.** On failure the Python runner prints the observed stage names/count, next expected stage, the native terminal status and a fixed-vocabulary Quickshell boot/load indicator. It never displays arbitrary log lines, private paths or task contents.
- **QML guard attribution.** The unmounted M12u root emits a boot marker and distinguishes three failure causes before writing: `FIXTURE_PATH_MISMATCH`, `DISPOSABLE_ENV_MISSING`, `PRODUCTION_GATES_UNSAFE`.
- **Stable marker parsing.** The runner requests Quickshell `--no-color`, sets `NO_COLOR=1` only in its test child, and removes any remaining ANSI color codes from stage/result lines.
- **Tests.** Extended the existing Python evaluator negative cases: explicit native failures with zero/partial stages, timing timeout, ANSI-wrapped markers, duplicate or wrong order, and unchanged production isolation.

No production `ApolloHubTodoStore.qml` edits; no other task caller, FileView, write path, native service or durable state introduced. The preexisting temporary fixture runner still creates one isolated data directory and terminates only the process it started.

## HOW TO USE

After operator review/merge and the user's **separately authorized local source update**, from the installed Quickshell checkout:

```bash
python3 tests/tasks/fixtures/TaskNativeSelfReportRunnerM12u.py
```

The command will run one disposable test and print a richer result, such as:

```text
M12u // FAIL // SAVE_CALLBACK_INVALID
Native stages: INITIAL_EMPTY, TICKET_DISABLED // 2/4
Expected next: NATIVE_SAVE
Native terminal: FAIL/SAVE_CALLBACK_INVALID
Quickshell: M12U_QML_OBJECT_STARTED
```

The example is **illustrative**, not an observed result. A PASS still requires all previous acceptance checks. Neither PR merge nor the diagnostic patch is native acceptance.

The user's local `main *5 ?4` prompt indicates existing modified/untracked work. **Do not issue git reset/clean/checkout or a blanket pull.** This remote PR does not modify the local worktree; only an operator-controlled update after checking conflicts should install it.

## VERIFY

- Observed operator report: `NATIVE_STAGE_SEQUENCE_MISSING`; root cause **NOT ESTABLISHED**.
- Source defect verified: native `RESULT|FAIL` can be swallowed by an earlier missing-stage test.
- Automated regression: native failure prioritized without sacrificing false-positive denial; stage counts and guard codes remain source-scoped. CI pending on final branch.
- Outstanding: native rerun, full root cause, Qt callback/commit identity, producer and user-data acceptance.

## WATCH OUT FOR

- A missing log marker might result from actual QML load failure, a failed guard, a missing Qt callback, an unexpected early exit, or log capture rather than file persistence. Do not infer a root cause from the generic previous output.
- The diagnostic enhancement does **not** fix an actual native FileView callback failure if one exists. It is built to identify that failure before editing production files.
- All test I/O stays in the disposable directory. No live tasks file is opened by the runner; no new native writer or backup system.
- The runner retains its 20-second QML deadline and 35-second outer collection cap. No auto-retry or restart of the live shell.

## CHECKLIST

- [x] Confirm current GitHub main, M12u source, protocol and no competing open TASKS PR
- [x] Preserve the user's literal failed-output evidence
- [x] Identify missing-stage-before-native-fail diagnostic precedence bug
- [x] Prioritize exact native failure and add guarded, redacted report summaries
- [x] Expand negative tests, preserve strict original production writer
- [ ] CI success and independent review
- [ ] Operator PR review/merge
- [ ] Operator-controlled source update without overwriting dirty local work
- [ ] Native rerun and actual failure attribution
- [ ] Final M12s/M12u acceptance and further ticket integration only after evidence

## NEXT

After green CI, review and merge M12v only if approved. Re-run the same disposable test and use its explicit native reason and step count to repair **the specific discovered issue**, if necessary. Keep ticket producer and the future UI cutover disabled; avoid adding speculative infrastructure.

## DECISIONS

**Implemented for review:** narrower diagnostics for an already-running test.  
**Not proven:** actual reason for the operator's failure or completion of M12s/M12u native acceptance.  
**Unchanged:** M12l one logical writer, M12t read-only source baseline and M10e reuse; no real task-data access, local machine writes, Quickshell restart, permanent process, merge or production ticket activation.
