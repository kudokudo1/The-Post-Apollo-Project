# 🏥💜 TASKS M11i // Native Quickshell Acceptance Visibility

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** TASKS storage recovery, Proxy successor continuation  
**Status:** Standalone QML acceptance instrumentation, no native execution yet  
**Authority:** Production `ApolloHubTodoStore.qml` remains the JSON FileView writer.

## IMPLEMENTATION

M11h PR #810 has merged. M11h proved the durable Python test-host crash
windows but did **not** run the actual Quickshell 0.2.1 runtime. The
next meaningful verification is native Process/FileView callback order
on the operator's own Quickshell/Sway environment, under a separately
approved disposable test. M11i **prepares** that acceptance without
requesting or making workstation changes.

- `TaskFileViewNativeEvidenceM11i.js` is an in-memory bounded
  (32 events) observer with an enum-only event vocabulary. It records
  event sequence and safe phase only. It NEVER records file paths,
  home directory, task content, fixture bytes, raw JSON, process stdout,
  host owner IDs or saved data.
- `TaskFileViewHostBridgeM11g.qml` remains unmounted and contains the
  same FileView and host process. It now records ATTACH, host HELLO,
  initial file LOAD, STAGE requested, host ADMIT, FileView SAVED,
  actual FileView READBACK_OK, host SETTLED, FREEZE and HOST FROZEN.
  Failure and host exit also enter the trace.
- `TaskFileViewHostHarnessM11g.qml` remains an **explicit standalone**
  configuration. Its panel now shows only recent event names,
  completed observed save chains, whether a freeze or recovery was
  observed, and the conspicuous label
  `OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED`.

These fields are runtime diagnostics, NOT durable evidence and NOT
production authority. The counter of completed callback chains counts
event order only, not proof of correct disk provenance. The host's
independent private-file readback and OS lock remain separate
acceptance conditions. The recorder cannot decide migration or
activate SQLite, and is not imported into TASKS, TODAY, PLANNER, Hub,
`shell.qml` or any active services.

## HOW TO USE

Repository-only CI, with no native Quickshell process:

```sh
node tests/tasks/test_task_fileview_native_evidence_m11i.cjs
python3 tests/tasks/test_task_fileview_native_evidence_m11i.py
python3 tests/tasks/test_task_fileview_crash_windows_m11h.py
```

### Proposed *later* native acceptance, requiring explicit local permission

**No commands below have been executed on the operator's PC.** This is
the record for a separately approved isolated desktop test, and its
steps are not permission to create local files.

1. Confirm installed Quickshell version and current repository HEAD;
   do not insert the harness into the production `shell.qml`.
2. After operator authorization only, create one new private test
   directory **outside** live QS data and instantiate the existing
   M11e synthetic fixture. The previous M11g instructions document
   the exact paths and commands.
3. Launch the M11g standalone harness in an **additional**, separately
   identifiable Quickshell process, leaving the normal instance alone.
4. Use the UI: enter the private fixture path; click **NEW TEST** only
   when no fixture authority DB exists. Confirm host JSON_ACTIVE,
   file READY, counter 0. Both initial FILE_INITIAL_LOAD and HOST_HELLO
   should appear; their order is not prescribed.
5. Click **INCREMENT**. Observe in the panel:
   `STAGE_REQUEST → HOST_ADMIT → FILE_SAVED → FILE_READBACK_OK →
   HOST_SETTLED`. The displayed confirmed synthetic counter advances
   only after HOST_SETTLED. Click again, and verify the same chronology
   with no extra or overlapping stage.
6. Click **FREEZE**. Check HOST_FROZEN with no pending stage and
   verify INCREMENT is refused. Press STOP and close only the
   standalone Quickshell instance.
7. Start another **separate** native harness on that old test authority
   using **EXISTING**. The fresh host must return RECOVERY_REVIEW,
   the test stage must remain unavailable and no source file should be
   silently reinitialized or deleted.
8. For native failure experiments, begin with a completely new
   *synthetic* disposable fixture each time; do not change the
   ownership or permissions of live TASKS/Quickshell files. Preserve
   test evidence until authorized cleanup.

Record only a compact report: Quickshell version, test repo SHA,
test sequence, phase, counter, chronological enum event names,
whether the window opened and closed normally, and sanitized
error codes. Never paste absolute private file paths, raw file
contents, host stderr, personal data or real task names. A future
worker can compare this record against the expected chronology.

## VERIFY

GitHub CI checks:

- Pure event ordering recognizes fully observed stage/reservation/
  save/readback/settlement chains, not skipped or scrambled callbacks.
- Host exits or failures during a chain prevent declaring that chain
  complete. Initial host/file load may be observed in either order.
- Event record is capped at 32 entries with dropped-event count,
  sequence monotonicity and strict vocabulary.
- Caller-supplied paths, private text and unrecognized states cannot
  enter evidence.
- Instrumentation is isolated to the unmounted M11g bridge and
  standalone window; production writer path and source remain intact.
- M11h/M11g and the M11d production writer inventory continue passing.

CI **does not** establish actual native Quickshell behavior because
the runner does not instantiate the operator's Quickshell/Wayland
environment. Its success means the instrumentation and earlier
subprocess tests pass, NOT native runtime acceptance.

## WATCH OUT FOR

The native trace can be incomplete if the 32-event ring fills;
`dropped` indicates that older events were lost. A callback event
in QML is not a cryptographically authenticated stage acknowledgment.
The isolated Python host is real but not a trusted production writer.

Do not confuse a valid synthetic callback chain with the
single-writer proof needed for production cutover. Symlink and
noncooperating-file-writer risks remain, as does the lack of
independently accepted native Quickshell runtime evidence. The
desktop test needs explicit operator authorization, and any live
writer integration or migration needs a separate approval.

## CHECKLIST

- [x] Inspect current GitHub state, M11h merge and M11g QML behavior
- [x] Confirm target Quickshell 0.2.1 Process/FileView API shape
- [x] Add bounded memory-only event chronology in isolated test bridge
- [x] Display traces and observed save chain counts in test panel
- [x] Add source-level privacy and callback-order regression tests
- [ ] Verify current GitHub workflow and independent review
- [ ] Operator-approved merge
- [ ] Explicitly approved native Quickshell acceptance
- [ ] Real FileView process/callback behavior verified on local desktop
- [ ] Separately reviewed and approved production writer integration
- [ ] Separately approved SQLite migration and rollback

## NEXT

Once merged, obtain operator permission and perform native standalone
Quickshell verification on the synthetic private fixture, then report
the actual event chronology and any process errors. Only those native
results can satisfy the outstanding runtime gate. Avoid adding more
mock milestones instead of collecting the real evidence.

## DECISIONS

M11i is an acceptance-visibility enhancement, **not** native acceptance
itself. JSON remains the only active TASKS writer. No live TASKS,
desktop process, local test file, service, SQLite production database
or GitHub Project has been changed.
