# 🏥💜 TASKS M12i // Isolated Native FileView and M12h Stage Receipt Bridge

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M12i standalone Quickshell FileView → disposable M12h receipt integration  
**DOCTOR //** External Hospital-compatible ChatGPT worker; not registered in live Hospital  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED BASE //** GitHub `main` `7e05711581d9e19454de4631de194c1edc9c2cfb` (October 31, 2026). Recheck latest source before further work.  
**CLASSIFICATION //** **ISOLATED NATIVE-TEST IMPLEMENTATION, NOT NATIVE ACCEPTANCE OR PRODUCTION ACTIVATION.**

## IMPLEMENTATION

### Existing mechanism

M11g already has a real standalone `FileView` (with `atomicWrites: true`), an isolated Python process and deferred `Qt.callLater(... fixtureFile.reload())` after `onSaved`. Its host independently reads source before settling an M10p SQLite `pending_stage`, but historically did not persist each expected/actual source digest with a stage. M12h adds the durable `stage_receipts_m12h` table in a **new disposable** `m11e-fileview-test/handoff-test.db`, with a stage, epoch, baseline SHA-256, expected SHA-256, actual SHA-256 and `SETTLED_UNACKNOWLEDGED`.

M12i connects these mechanisms in **a new standalone test-only configuration** without editing M11g, M12h, M10p or the production singleton.

### New files

- `tests/tasks/fixtures/TaskNativeReceiptHostM12i.py`: a separate **test-only Python process** using the existing M12h `DisposableStageReceipt`. It accepts bounded newline-delimited JSON commands `status`, `reserve`, `verify` and `freeze`, with increasing request IDs and strict schemas. It opens only the exact M11e fixture and M10p journal. `reserve` atomically persists expected/baseline bytes and stage, returns the synthetic next-file payload; **the host does not write task JSON**. `verify` requests an independent exact file reread, then atomically records actual digest/receipt and clears pending in that same existing disposable journal. Wrong bytes or invalid/missing source enter `RECOVERY_REVIEW`; stale stage/epoch and unrecognized messages fail closed. A callback does not prove a stage.
- `tests/tasks/fixtures/TaskNativeReceiptLabM12i.qml`: an **isolated** one-FileView, one-Process Quickshell window, based on M11g's known `FileView` timing. It requires a human to enter `/…/m11e-fileview-test/fixture-only.json` and an approved synthetic writer ID and explicitly click `NEW TEST` or `EXISTING`. It writes only the private synthetic fixture after a durable host `reserve`, defers reload after `onSaved`, compares the local reread to the pending payload and asks the host for its own independent readback. It only increments its displayed counter on a matching `verify` receipt. A new process with existing journal enters `RECOVERY_REVIEW`. It does **not** auto-rearm, automatically start the process, read task storage or mount in `shell.qml`.
- `TaskNativeReceiptHarnessM12i.qml`: **root-level, unmounted** Quickshell config wrapper so `Quickshell.shellPath("tests/tasks/fixtures/TaskNativeReceiptHostM12i.py")` resolves relative to the repository.
- `tests/tasks/test_task_native_receipt_host_m12i.py`: process-level Python tests with disposable source/journal fixtures and a **simulated file replacement** to exercise the host's positive and negative cases. It also asserts QML source/guard invariants, but does **not** run QML.
- Scoped GitHub Actions and this Hospital continuity report.

### Real and simulated boundaries

1. **Genuine in CI:** Python child process, OS-private SQLite journal and cooperative `flock`, M12h stage reservation, actual source reread from the disposable test file, byte-exact SHA-256 matching, transactional settlement and review on restart.
2. **Simulated in CI:** Quickshell `FileView` write, using a test-only atomic file replacement. A green CI check cannot certify QML imports, actual `onSaved` order, rendering, or native event attribution.
3. **Manual native testing, not performed here:** Launch the standalone Quickshell configuration on an expressly approved disposable fixture. Only this step provides direct evidence of the real `FileView` save path.
4. **Not proved:** Independent signing authority and executable attestation, external writer fencing, source protection against all same-user adversaries, callback origin cryptography, real TASKS source permission, UI acknowledgment beyond the test window, power-loss durability or production activation. The M12h `SETTLED_UNACKNOWLEDGED` receipt is a synthetic OS-host observation and is **not automatically a user-visible committed task**.

### Failure behavior

- Native `onSaved` is only a hint; it never sends or creates a settlement on its own. The lab defers reload, then issues the stage+epoch `verify` command to an existing cooperating OS process; the host rereads the source **again**.
- Wrong source bytes return `READBACK_REVIEW_REQUIRED`; M12h's journal preserves the pending stage, records the readback and moves to `RECOVERY_REVIEW`.
- Stale process, stage, epoch or wrong protocol frame fails closed; no auto-retry, blank source promotion or repeated use of the same stage.
- An exiting host leaves QML read-only. Restarting the lab with `EXISTING` does not reacquire `JSON_ACTIVE`; the new SQLite owner enters `RECOVERY_REVIEW`.
- An actual application crash after host settlement but before UI publication leaves an explicitly unacknowledged durable receipt for later review.

## HOW TO USE

**GitHub CI:** no Fedora changes, no local test execution.

```sh
python3 tests/tasks/test_task_native_receipt_host_m12i.py
```

**Future operator-approved isolated native test** (not performed as part of this PR):

1. Confirm local `git status`, matching M12i source, `qs` executable and existing Quickshell sessions. Never change, pull or restart the live shell merely to run this test.
2. Create a **new** owner-private `m11e-fileview-test` directory with `0700`, seed `fixture-only.json` with the existing M11e test seeder using `0600`, and verify that the directory has no existing SQLite journal. **Do not reuse the M12g historical journal**: M12i's `NEW TEST` creates an M12h receipt table and requires a clean journal.
3. Explicitly launch `qs -p /absolute/repository/TaskNativeReceiptHarnessM12i.qml`. This is a separate Quickshell config from the live `shell.qml`.
4. Enter the private fixture path and unique synthetic writer ID, click **NEW TEST**, then **INCREMENT** twice. Each stage must show a settled receipt and the fixture counter must advance only after host confirmation. The native UI will not claim cryptographic stage attribution.
5. Click **FREEZE**, confirm `FREEZE_REQUESTED`, then **STOP** and close only that standalone Quickshell instance.
6. Inspect the disposable SQLite journal and source **after closing the host**, recording stage receipt rows with **redacted** stage/owner identifiers and exact expected/actual digest equality, plus source counter=2 and phase. **Never publish private paths or task text.**
7. Launch a separate fresh lab and choose **EXISTING** with the same fixture but a new synthetic writer ID. It must enter `RECOVERY_REVIEW` and refuse a new INCREMENT. Preserve the journal and stop the standalone test.
8. Record a separate status for source tests, native launch, native completion, journal receipt equality, fresh-process refusal and operator acceptance. No production gate automatically closes.

Do not invoke this native procedure automatically from GitHub CI. Local writes, Quickshell launches and local Git synchronization require explicit approval and verification.

## VERIFY

- M12h PR #950 confirmed merged; no competing open TASKS PR or M12i branch at start.
- Live `ApolloHubTodoStore.qml` still owns one `FileView` and `guardedWriterEnabled: false`. No modification to the singleton, its nine mutation callers, `shell.qml`, M10p, M11g, M12h or existing native harnesses.
- M12i CI runs real process-protocol tests with disposable Python/SQLite sources, QML static structure audits and M12h/M12f/M12e/M11t/M11d regressions.
- CI passing remains **synthetic OS/process plus source-level QML verification**, not operator-observed native M12i acceptance.

## WATCH OUT FOR

- The M12i standalone test creates one **additional isolated FileView** only when its separate config is launched. It does not create a second production TASKS writer.
- QML's path regex is not a filesystem security boundary. The independent host uses the M11g private fixture validator and M10p owner permission checks; noncooperating external writers remain outside the cooperative lock.
- All host messages are **unauthenticated synthetic local process messages**. Even a matching stage/epoch and SQLite hash is not an independently trusted certificate; a malicious parent/host can forge messages or edit the private fixture.
- The test may produce `SETTLED_UNACKNOWLEDGED` without a later UI acknowledgment, so do not call it complete production storage merely because the local window counted two saves.
- A failed native run must preserve fixture and logs for diagnosis. Do not reset, delete, restore, or point the test to `apollo-hub-todo-v1.json`.

## CHECKLIST

- [x] Verify current GitHub main, Syntagma and Hospital source/assignment boundaries
- [x] Reuse M12h journal and strict M11g/M10p disposable fixtures
- [x] Create manual-only native FileView → host receipt bridge and root harness
- [x] Add process-level protocol tests for settlement, failure and restart refusal
- [x] Keep production single-writer guard and old test harnesses unchanged
- [ ] CI verified
- [ ] Operator review/merge
- [ ] Separate approved native Quickshell M12i runtime test
- [ ] Real trust-root, source authority, native callback provenance, UI API and activation acceptance

## NEXT

Review the draft PR/CI. Then separately authorize isolated Fedora native acceptance on a fresh disposable M11e fixture. Feed its native behavior and journal receipt evidence into the later production interface decision, without interpreting synthetic process success as real task-data protection.

## DECISIONS

**Implemented:** Isolated M12i Python host and manually launched Quickshell native receipt bridge, with no production wiring.

**Pending:** Native runtime observation and final operator acceptance, authenticated host identities, prevention of noncooperating writes, real source approval, durable UI acknowledgment and rollback.

**Not authorized:** Production TASKS file reads/writes, local machine edits, Quickshell restart, signing root installation, task data migration, PR merge, automatic restoration, or live Hospital registration.
