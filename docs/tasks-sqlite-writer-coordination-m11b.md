# 🏥💜 TASKS // M11b Disposable Writer Coordination & Restart Fence

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuation, operator-authorized Proxy 2 successor  
**Status:** Test-only coordinator using the existing M10p durable authority fixture  
**Live authority:** JSON `services/hub/ApolloHubTodoStore.qml`; no live change

## IMPLEMENTATION

M11a's pure JSON/SQLite snapshot comparison has merged. M10p already
provides an actual cross-process Linux `flock` on a disposable
`handoff-test.db`, durable epoch/phase records and strict restart
fencing. M10q connects this to an unmounted Quickshell rehearsal.

M11b reuses that authority rather than inventing a second lock. Its
`tests/tasks/fixtures/TaskWriterCoordinationM11b.py` exercises a more
concrete **simulated FileView save / JSON source drain**:

- A single coordinator lifetime owns M10p's private SQLite `handoff-test.db`
  and OS lock, using an explicitly private sibling `legacy-test.json`.
  The source must already exist, be owned by the current process user, be
  a regular non-symlink file with private permissions, and be bounded to
  at most 1 MiB. No real Quickshell task path can be supplied.
- `simulated_stage(token)` delegates to M10p's durable one-at-a-time
  stage admission. `freeze(epoch)` atomically shuts that simulated stage
  gate, while a previously admitted save token may remain outstanding.
  `simulated_callback(token, saved)` accepts only the matching callback.
- `review_source_drain()` refuses a pending save or a phase other than
  `FREEZE_REQUESTED`. It reads **real bytes** from the throwaway JSON file,
  using `O_NOFOLLOW`, inode/owner/mode/size checks, and a second read.
  A source change between reads blocks quiescence rather than pretending
  the source was stable.
- The underlying durable authority *again* verifies phase/pending-token
  state and records the resulting source SHA-256 in an SQLite transaction.
  Even then, the coordinator reports `legacyWriterEnforced:false`,
  `sqliteWriteAuthorized:false` and `liveChangePerformed:false`.
- On closing or crashing the owner, reopening the test authority
  persistently enters `RECOVERY_REVIEW`, even if an older checkpoint
  reported `JSON_ACTIVE` or `JSON_QUIESCED`. It never automatically
  rearms simulated JSON admission.

This extends M10p's evidence from caller-provided bytes to a **real
disposable file read** but deliberately does not claim control over
uncooperative external writers. Filesystem checks and advisory `flock`
cannot prove that the production JSON writer is frozen unless all
production stage paths actively obey the same gate.

The class has no CLI, default path, Quickshell imports, SQLite TASKS
mutation, Github transport, migration, activation, local desktop
registration or live JSON file access.

## HOW TO USE

CI only:

```sh
python3 tests/tasks/test_task_writer_coordination_m11b.py
```

Tests use `tempfile.TemporaryDirectory`, make strict private
`legacy-test.json` and `handoff-test.db` fixtures, start a genuinely
separate OS-process lock contender and release all resources afterward.
No operator workstation files or services are modified.

## VERIFY

The new suite checks:

- Real distinct process cannot acquire the test lock while the first
  coordinator owns it.
- Simulated one-in-flight save, freeze barrier, stale/mismatched callbacks,
  failed save and rejection of newly staged writes after freeze.
- Quiescence cannot be acknowledged until pending save has settled.
- Two consistent actual disk reads produce one persisted source SHA-256,
  with no write authorization.
- Changed JSON bytes between observations block source acceptance and
  leave the durable authority in `FREEZE_REQUESTED`.
- Reopening a clean, closed fixture fails closed in `RECOVERY_REVIEW`,
  preserving epoch fencing and denying any automatic rearm.
- Missing files, wrong names, symlinks, unsafe permissions and implicit
  creation are rejected.
- Original M10p/M10q/M10o tests and M11a/M10n regressions rerun.

## WATCH OUT FOR

**M11b does not enforce anything in the live Quickshell TASKS store.**
`ApolloHubTodoStore.stage()` still accepts the current JSON writer's
normal actions and has no connection to the test authority. No actual
`FileView.onSaved` callback is wired to this coordinator; stage tokens
are synthetic. Disk bytes are observed but not held immutable against
a noncooperating filesystem writer. CI proves a disposable process/lock
experiment, not real power-loss or two-writer production safety.

The ordinary Quickshell restart recovery/rearm policy also remains
undecided. M11b intentionally blocks rearm pending an independently
verified current-data/owner protocol. Simply reading old test hashes or
supplying self-reported booleans must never recover write authority.

M10z's isolated on-device native Quickshell runtime acceptance is
still pending explicit local approval. This is separate from a future
operator-approved migration and production activation.

## CHECKLIST

- [x] Confirm M11a merged and inspect existing M10p/M10q admission work
- [x] Reuse the existing durable OS lock and stage/freeze/callback contract
- [x] Read a real disposable legacy JSON file twice with safety checks
- [x] Test changing bytes, callbacks, process contention and restart fence
- [ ] CI completion and independent review
- [ ] Operator approval of experimental PR merge
- [ ] Explicitly approved on-device isolated QML runtime acceptance
- [ ] Design verified ordinary-restart rearm with no unintended lockout
- [ ] Implement an audited production stage gate inside the legacy singleton
- [ ] Verify full SQLite writer parity and the unified operation journal
- [ ] Separate approval for actual task migration, rollback and activation

## NEXT

M11c should design a **normal-restart recovery review** that distinguishes
a clean closed JSON writer from an ambiguous pending save, using actual
durable checkpoints, fresh source evidence and independent owner fencing.
It must remain an isolated fixture until native Quickshell acceptance
and an explicitly authorized production integration patch. The approved
production solution must preserve TASKS/TODAY/PLANNER behavior.

## DECISIONS

JSON remains the only live task writer. No local workstation modification,
actual SQLite TASKS database, real JSON data, GitHub Project, QML startup,
or live Hospital assignment was changed here.
