# 🏥💜 TASKS // M14b Standalone Native Post-Crash Source Review Bridge

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS Source Integrity / Encrypted Draft Recovery  
**STAFF ROLE //** DOC, external Hospital-compatible, provider OPEN AI // CHATGPT; not verified registered in live Hospital  
**ASSIGNMENT //** Join M13y real disposable SQLite/source inspector to the strict M13z review projection in a standalone Quickshell panel  
**CHECKPOINT //** M14a PR #1394 merged at `dfc60bba61f0bfae66ebb34f05fddad7a4704e11`; all 57 pull-request workflows passed at its reviewed head. Main was `e3595b0035bb3d89aa87c6ba2bd1aac04a975181` at M14b branch creation (November 6, 2026).  
**SCOPE / PERMISSIONS //** Isolated fixture-only GitHub QML/test/CI/documentation. No actual task-data reads, local Fedora work, production writer changes, UI service activation, keyring/Connections mutation or automatic PR merge.

## IMPLEMENTATION

M14a now reports real `FileView.onSaved`/failure signals in **TASKS → SYNC → RECOVERY**, but the source bytes and callback origin are **not authenticated**. M13y separately inspects real *synthetic* JSON and SQLite journal bytes in a disposable `m11e-fileview-test` directory; M13z projects a strict redacted fixture result into safe labels and keeps the unsaved draft. Until now these two pieces were tested independently, and the actual M13z production screen correctly left source inspection marked **NOT CONNECTED**.

M14b makes a **standalone, manually started native lab**, not a new production provider:

- `TaskPostCrashReviewHarnessM14b.qml` is a root Quickshell configuration never imported by `shell.qml`.
- `tests/tasks/fixtures/TaskPostCrashReviewLabM14b.qml` offers an explicit **INSPECT TEST** button. It accepts only an absolute `/.../m11e-fileview-test/handoff-test.db` input. Only after a click does one short-lived Quickshell `Process` invoke the existing Python read-only M13y inspector with `python3 -I -B` and that fixture path. Neither this QML nor the root config uses `FileView`, `setText`, task JSON writer access, a new daemon, keyring or a network client.
- Output is a single bounded redacted M13y JSON report. The QML `acceptFrame()` rejects extra/large/malformed lines. It passes the report only to the already-existing `TaskRecoveryReviewPolicyM13z.syntheticResult()` exact-schema projection, which refuses unexpected fields, authenticated-source claims, grants, or deletion flags.
- A successful classified fixture is **SYNTHETIC SOURCE OBSERVATION // REVIEW ONLY**, showing one of M13z's unchanged/expected-unsettled/settled-unacknowledged labels. Missing/unsafe/unclear sources remain **REFUSED // SOURCE EVIDENCE UNVERIFIED**. All states retain the draft and deny replay, restore, source writes and deletion.
- `tests/tasks/test_task_postcrash_native_review_bridge_m14b.cjs` constructs actual owner-private synthetic JSON/SQLite journal fixtures, reserves/settles stages using the existing M12h disposable owner, launches M13y's Python inspector as a separate process, and runs its real output through the M13z UI policy in Node. It checks three normal crash-stage states, unsafe link, foreign journal, forged approvals, data minimization, and the standalone QML non-mount/non-write boundaries.

**This test is an independent process/filesystem-to-presentation contract.** It neither launches Quickshell on CI nor proves a genuine native callback can be attributed to an independently trusted source owner. It does not bind M14a's live callback to a specific M12h synthetic stage. All real saved task work remains under the sole existing `ApolloHubTodoStore.qml` FileView.

## HOW TO USE

### GitHub CI

The new workflow runs the end-to-end **disposable** SQLite/source → Python inspector → M13z projection tests, M13y/M13z/M14a/M11d/M12r/C2a security regressions, and Qt `qmlformat` syntax of the standalone config.

### Future isolated native acceptance, only with separate operator approval

1. Confirm a disposable `m11e-fileview-test` fixture exists from the **existing M12i test harness**, with `0700` owner-private parent, `0600` JSON and an initialized M12h `handoff-test.db`. This may be created only within an explicitly authorized private test location, never from the live TASKS source. Let the M12i host exit so its cooperative exclusive lock is released.
2. From a reviewed repository checkout, explicitly run the standalone config (do not restart live `shell.qml`): `qs -p /absolute/repository/TaskPostCrashReviewHarnessM14b.qml`.
3. Enter the **absolute synthetic** `.../m11e-fileview-test/handoff-test.db` path and click **INSPECT TEST** once. Confirm the panel states `SYNTHETIC FIXTURE ONLY // NOT LIVE` and the correct source/journal review class, without showing source bytes, stage IDs, task titles or secrets.
4. Test missing or unsafe fixtures and a live M12i owner (should refuse rather than claim a reliable snapshot). Close only the standalone M14b test panel. Preserve any failed synthetic fixture for diagnosis.
5. Record native launch status, read-only report, absence of source changes and native visual acceptance separately from CI.

**Do not perform the above on the user's Fedora desktop without current explicit permission.** The normal TASKS recovery UI remains operational, and its real source status remains **NOT CONNECTED**. Nothing here is an instruction to reset the user’s files or stop the running desktop.

## VERIFY

- Real Linux/Python M12h source-stage/journal fixtures are independently inspected in a separate child process. The strict M13z projection handles all three known M13y classes with the same review-only semantics.
- M13y refuses missing, unsafe and symlinked JSON; M13z rejects forged grants, unexpected source fields and client-injected identity.
- The QML panel starts the test-only inspector only in response to a user click, never on QML mount or timer. It restricts the entered fixture location, but relies on M13y for actual private-directory/symlink validation.
- Production remains one `FileView`, one `todoFile.setText()`; M14a live hints and M13z example UI continue, without a new consumer or real task-file access.
- No true approval, source-owner authentication, native callback attribution, saved-task ACK, recovery, key release, source write or draft clearing is added.
- CI `qmlformat` syntax does not certify native Quickshell runtime or actual display layout.

## WATCH OUT FOR

The standalone QML process has the **same filesystem UID as its parent**. Neither `SO_PEERCRED`, a test-only Python process, byte comparison nor an advisory `flock` certifies provenance against a malicious same-UID writer. The M13y inspector is not a production cryptographic trust root, and it may cause SQLite to manage transient WAL `-shm` metadata even when application SQL is read-only. The source and journal are distinct resources and not atomically committed together.

Only synthetic JSON inside the constrained fixture path is ever allowed. A correctly formatted result can still be forged by a malicious same-UID principal, so M14b's presentation never acknowledges a durable user save. No actual encrypted draft data is captured, previewed, deleted or restored. If native Quickshell `Process` behavior differs from CI's static expectations, preserve results and require a separate fix.

## CHECKLIST

- [x] Verify M14a merge and final 57/57 CI; inspect current Syntagma protocol, main and active TASKS ownership
- [x] Reuse M13y post-crash read-only inspector and M13z exact-schema projection
- [x] Add manual-only standalone Quickshell test panel and root config
- [x] Add real process-backed synthetic fixture-to-UI projection tests
- [x] Add scoped CI and security boundaries without altering production TASKS
- [ ] Final PR-head CI and independent security review
- [ ] Operator PR merge decision and local native acceptance
- [ ] Authenticated real-source readback and callback/source binding
- [ ] Real opt-in encrypted draft lifecycle and protected Connections authorization

## NEXT // M14c

After successful CI and independent review, run an **operator-authorized, isolated native Quickshell test** with synthetic M12i saved-source history and a fresh process, confirming the standalone review panel displays the correct classification. The next production-shaped change must choose and document a realistic local source-owner model and safe conflict behavior before connecting a live source to the real TASKS screen. Do not enable recovery or auto-clear drafts based on M14b synthetic evidence.

## DECISIONS

Preserve the accepted M12l local-first single logical TASKS writer and the explicit same-UID hostile-writer limitation. No additional production source reader, writer, Service, filesystem scan, network, credential action, local Fedora change, automatic restore, PR merge, or live Hospital registration. Native acceptance and the operator's final approval are separate from green CI.
