# 🏥💜 TASKS // M13u Journal-Backed Source Revision Evidence

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS opt-in encrypted recovery / source revision  
**WORKER //** OPEN AI // CHATGPT, Hospital-compatible external development; not live Hospital-registered  
**BASE //** main `6f886331d4b2747759beffb36dadf9ac33d54539`, November 6, 2026  
**PERMISSIONS //** Bounded GitHub-only disposable test fixture, workflow and handoff. No real TASKS/Quickshell/OS keyring writes, shared Connections owner edits, activation, merge or local deployment.

## IMPLEMENTATION

**Reconciliation:** TASKS M13t #1304, Connections C2r handoff #1343 and Connections C2s #1345 are merged. A November 6 handoff on #1304 assigns the durable saved-source revision to the TASKS owner and operator/caller authentication to the Connections owner. Connections has a tested confined *read-only fake service*, not an approval/key-release service. This task does not edit shared Connections files.

**Reuse, not a duplicate writer:** The existing M12h `TaskStageSourceReceiptM12h.py` already has real disposable SQLite stage rows, exact source readback and settled/unacknowledged receipts under the M10p lifetime owner lock. M13u adds a **read-only inspector** `TaskSourceRevisionEvidenceM13u.py`. It never creates another source writer, SQLite table, service, keyring client or permanent store. It works only with an already-held `DisposableStageReceipt` and its strictly fixture-only `m11e-fileview-test/fixture-only.json`.

The inspector requires a nonempty chain of durable `SETTLED_UNACKNOWLEDGED` stage rows, byte-exact source readback through M11g's existing guarded file descriptor routine, a linked baseline→actual SHA-256 receipt chain and agreement with the M11g synthetic JSON revision counter. It derives a **monotonic local revision number** from the persisted count of sequential settled stages. A synthetic compare-and-check pin contains `revision`, `stageId`, `sourceSha256` and `ownerEpoch`, which must all match when re-inspected. Any missing source, malformed/rewound bytes, interrupted stage, divergent chain or stale epoch fails closed.

A *new OS process* may read historical settled stages, but M10p deliberately transitions it into `RECOVERY_REVIEW`. M13u displays only the last observed revision in that state, **never** a current consent/commit receipt. This avoids pretending that a saved-file callback or a fresh process inherits write authority.

The new Python suite uses actual `sqlite3`, filesystem readback, fsync and an independent subprocess in disposable temp directories. It also injects source rollback, journal corruption and unsafe symlink paths. The original production `ApolloHubTodoStore.qml` remains unchanged, with one FileView and one `todoFile.setText()`.

## HOW TO USE

No live desktop action required. GitHub CI runs:

```bash
python3 -B -m unittest discover -s tests/tasks -p 'test_task_source_revision_evidence_m13u.py' -v
```

The accepted visible routes remain TASKS → SYNC → RECOVERY and CPU++ → SETTINGS → CONNECTIONS → TASKS; both remain status-only for recovery. The new inspector is never imported into QML.

## VERIFY

- No settled stage cannot manufacture a baseline/version-zero trusted receipt.
- Two legitimate sequential disposable settlements produce distinct journal-derived revisions.
- A previous revision or changed owner epoch cannot satisfy a current compare-and-check.
- Reverting a saved JSON file to valid but outdated bytes is refused against the more recent journal.
- A pending stage, missing file, symlink or tampered receipt chain fails closed.
- A fresh independent interpreter reads persisted history but enters REVIEW_REQUIRED and cannot claim current settlement.
- The new inspector never writes JSON or SQLite, starts a process, reads the user's actual TASKS JSON, looks up a secret or grants permission.
- CI repeats M12h, M12k, M13t, M11d and C2a regressions.

**Evidence boundary:** This is a **real durable local fixture experiment**, not a production-trusted source revision. A test-controlled journal count is not independently authenticated against an attacker who can rewrite the SQLite journal. The SHA-256 pin is observed at a particular instant; changes between check and actual protected operation remain possible. The existing `flock` is cooperative and does not fence an uncooperative same-UID process, and Linux fsync in CI does not prove actual Fedora power-cut durability. There is no safe production first-create provenance, real FileView stage attribution or trusted source/host isolation yet.

## WATCH OUT FOR

The eventual production protected host must bind a revision to a trusted source owner, not a QML self-reported `revision` property. It must re-verify **under a fenced commit or capture transaction**, not trust an earlier observation. The single TASKS writer must not be silently replaced, and an unsupported/absent/corrupt source must never become an empty authorized state.

Nothing in M13u authorizes actual draft capture, preview, deletion or restore. M13t's consent simulator, the C2s confined read-only service and this journal fixture remain separately nonauthorizing.

## CHECKLIST

- [x] Recheck Syntagma protocols, PR #1304 coordination, current main, C2s and active ownership
- [x] Reuse existing M12h/M11g/M10p durable fixture and single-writer architecture
- [x] Add read-only monotonic settled-receipt/source match inspector
- [x] Cover stale, rollback, process restart, unfinished, corruption and unsafe path cases
- [x] Add targeted CI and production gate checks
- [ ] Green final-head CI and independent review
- [ ] Operator merge / acceptance
- [ ] Actual source owner revision issuance, true first-create provenance and transactional fence
- [ ] Trusted Connections operator/caller consent and distinct capture/preview/clear grants
- [ ] Encrypted real-draft persistence with restart/reboot native acceptance

## NEXT

**M13v proposal:** Design a real TASKS coordinator-facing, fail-closed source receipt adapter that preserves the single FileView writer and only publishes a last-confirmed revision after independent durable evidence. This requires native Quickshell callback/transaction testing, first-create provenance, rollback/ABA treatment and a handoff API for the later independently authenticated Connections host. Keep real approval and activation closed.

## DECISIONS

No shared Connections, Social, Hospital or Fedora local mutations; no second task writer; no automatic source repair/replay; no real credentials/draft storage; no PR auto-merge. User retains final acceptance.
