# 🏥💜 TASKS M12h // Stage-to-Source Receipt in an Isolated SQLite Fixture

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M12h byte-exact stage-to-source test receipt and recovery contract  
**DOCTOR //** External Hospital-compatible ChatGPT, no verified live Hospital registration  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED BASE //** GitHub `main` at `ab4fca2bcbe87cb3e3b816e63b2d92277655b052` on October 31, 2026; recheck for each future change  
**CLASSIFICATION //** **EXPERIMENTAL SYNTHETIC SQLITE EVIDENCE ONLY**, no production task writer integration.

## IMPLEMENTATION

### Starting evidence

M12g was tested by the operator on a disposable M11e fixture, with two observed native save chains, exact source counter 2, freeze and post-restart `RECOVERY_REVIEW`, followed by matching read-only SQLite inspection. A later screenshot showed unchanged counter 2 after attempting the recovery refusal test. This evidence is **operator-observed native + disposable journal**, not a trusted signature or an independently authenticated callback-to-stage receipt. The operator's brief `ok` was treated as authorization to **continue repository-only M12h work**, not as a production-release decision.

M11g's existing test host already independently reads exact fixture JSON before `settle_stage(saved=True)`, but the M10p SQLite `authority` table loses the stage identity when it clears `pending_stage`. That makes historical stage-to-bytes verification unavailable after an unacknowledged settlement or owner crash. M12h introduces a **stage-specific receipt** in the SAME existing disposable `handoff-test.db`, not a new task-data store.

### Mechanism and scope

The new `tests/tasks/fixtures/TaskStageSourceReceiptM12h.py` is an import-only test module with no executable launcher, QML mounting, GUI controls, installation logic or actual TASKS data access. It reuses:

- **M11g** `stable_file()` and `encode_next()` to inspect the exact private `m11e-fileview-test/fixture-only.json` source and derive expected next bytes, without trusting callback-provided content.
- **M10p** `Authority` to establish the existing private ownership lock and durable SQLite `authority` epoch/phase. Only on explicit **fresh test bootstrap** it creates a test-only `stage_receipts_m12h` table in that same journal; original M10p schema `user_version=1` and production modules remain unchanged.
- **M10p's private `_transition()`** solely within this disposable test fixture to make M10p's `pending_stage` reservation and the receipt metadata insert **one SQLite transaction**. This private API reuse is **NOT** a proposed production API; a real host needs separately reviewed public ownership methods.

Each receipt records `stage_id`, `owner_id`, epoch, **baseline SHA-256**, **expected SHA-256**, **actual readback SHA-256** and status `RESERVED`, `SETTLED_UNACKNOWLEDGED` or `REVIEW_REQUIRED`.

**State sequence:**

1. Read the exact synthetic source twice; require it matches the last confirmed bytes held in memory.
2. Atomically persist pending stage and `RESERVED` receipt before handing expected next bytes to a **separate disposable test writer**. The M12h module **never writes source JSON**.
3. A native `FILE_SAVED` or `FILE_READBACK_OK` tag is only an untrusted notification. It does not settle or publish anything.
4. A separate host-side call rereads actual private file bytes **independently**, checks exact expected bytes and source baseline, and repeats that read inside its SQLite transaction.
5. On a match, atomically update the receipt to `SETTLED_UNACKNOWLEDGED` with actual digest **and** clear the M10p pending stage. This means the test ledger cannot have an acknowledged cleared stage without its matching settled receipt. **It does not acknowledge the UI or activate writes.**
6. On mismatch, invalid source or missing file, atomically persist `REVIEW_REQUIRED`, advance the journal epoch and retain the pending stage. No blank-source reconstruction or automatic replay.
7. A new authority process always enters `RECOVERY_REVIEW` and preserves either the reserved receipt or a `SETTLED_UNACKNOWLEDGED` receipt, depending on the crash boundary.

### What it verifies

| Boundary | Test evidence |
| --- | --- |
| Reservation atomicity | Pending M10p stage and baseline/expected receipt persist in one SQLite commit |
| Native event only | Callback tag does not change receipt or assert stage identity |
| Readback settlement | Independently reread exact fixture bytes match recorded expected SHA-256 |
| Receipt settlement atomicity | `SETTLED_UNACKNOWLEDGED` and clearing M10p pending stage occur together |
| Byte mismatch | Valid wrong revision or semantically identical JSON with changed whitespace is rejected |
| Bad/missing source | Persists review state, does not claim success |
| Wrong stage/epoch | Refused without attributing to current stage |
| Duplicate/replayed stage | Rejected; prior receipt not overwritten |
| Process death after reservation | Fresh owner enters recovery, pending and reserved receipt survive |
| Death after settlement but before UI acknowledgment | Fresh owner enters recovery; settled receipt retained; no auto-rearm |
| Concurrent M10p owners | Cooperating second owner denied via existing `flock` |
| Production boundaries | One existing TASKS `FileView`, nine mutations, guarded writer remains off |

### Trust limitations

- **NOT** actual independent native callback attribution: only source bytes and stage provenance **within the same cooperative synthetic host/journal** are correlated. The test's expected payload and SQLite host authority are generated within one user-owned process; signatures, root-controlled launch, hostile-writer fencing, and trusted actor identity remain unavailable.
- `flock` is advisory; an unrelated same-user process can ignore it and replace a file **after** readback/settlement. Back-to-back reads and SQLite transactions cannot atomically lock a separate JSON file. A production design must handle this explicitly.
- The experiments simulate FileView writes in tests with owner-only atomic replacement. **No native Quickshell run of M12h is included**. The prior M12g native run remains separate evidence.
- Actual source bytes are not recorded in journal, only SHA-256 and status. No claim of hardware fsync-order verification, power-loss durability, privileged process attestation, or rollback-resistant anti-replay across arbitrary disk restoration.
- There is deliberately no UI acknowledgment API. `SETTLED_UNACKNOWLEDGED` persists even if a callback/response is lost; later recovery must remain read-only, not silently replay or assume a UI accepted the stage.

## HOW TO USE

No operator-local steps, no Quickshell restart or task data migration. GitHub Actions runs:

```sh
python3 tests/tasks/test_task_stage_source_receipt_m12h.py
```

It allocates temporary private `m11e-fileview-test` fixtures in the CI runner. Test-only source replacement is performed **by the unit test**, not by a second host or a production writer. The old M12g disposable fixture on Fedora is left untouched.

## VERIFY

- Inspected current Syntagma AGENTS and Hospital protocols, latest GitHub `main`, M11g `stable_file`, M10p owner/journal, and current TASKS single-writer guard; no open competing TASKS PR or M12h branch on entry.
- New M12h source/test/doc/CI files only. Do not change original M11g, M10p, QML, `shell.qml`, M11l/M11m path restrictions or existing TASKS data.
- CI will run the M12h byte-exact, crash/replay and mismatch matrix plus M12f/M12e/M11g/M11t/M11d regressions.
- **All nine production M11t gates and ten M12b evidence topics remain OPEN.**

## WATCH OUT FOR

A successful test receipt is **only a consistent synthetic ledger record**, not an externally authenticated completion certificate. The new stage table is not a production SQLite TASKS schema, and the source remains the only task-data file. Reusing a private M10p method in a test fixture must not be mistaken for an approved public host interface.

No automatic conversion from test success to operator acceptance is permitted.

## CHECKLIST

- [x] Reconstruct M12g native checkpoint and current GitHub source
- [x] Check concurrent TASKS ownership before starting
- [x] Add strict disposable stage-to-source receipt and single-journal atomic transitions
- [x] Add wrong-byte, stale-owner, missing-source, replay, lock and restart tests
- [x] Preserve production singleton and all guarded activation gates
- [ ] Verify GitHub CI and independent review
- [ ] Operator review/merge
- [ ] Separately design a real authenticated host handoff and hostile-writer fencing
- [ ] Native callback receipt acceptance and production activation remain separately scoped

## NEXT

Review this PR. A future bounded milestone could use a **separate disposable native experiment** to test these SQLite receipt states under a real Quickshell callback sequence, without trusting the callback itself or connecting to the production source. Do not install new trust credentials or enable guarded mode on the basis of this receipt test.

## DECISIONS

**Implemented:** Isolated test-only stage, source-byte, owner-epoch and SQLite settlement evidence.

**Pending:** Real independent signer/host authority; source permission, last-confirmed UI acknowledgment semantics, native stage callback attribution, noncooperating-writer behavior, power-loss and rollback strategy.

**Not authorized:** Actual TASKS file reads/writes, Fedora edits, Quickshell restart, production QML changes, live Hospital registration, SQLite task-data migration, PR merge or guarded writer activation.
