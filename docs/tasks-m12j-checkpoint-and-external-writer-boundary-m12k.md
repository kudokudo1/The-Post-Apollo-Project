# 🏥💜 TASKS M12k // Native Receipt Checkpoint and Uncooperative Writer Boundary

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Preserve M12j native evidence and test same-user noncooperating source writes  
**DOCTOR //** External Hospital-compatible ChatGPT worker, not live Hospital registered  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED MAIN //** `8ec95a9ffeec8a57c6018e36d43d4ff5f958b152` (2026-11-02); recheck before later implementation  
**CLASSIFICATION //** SOURCE AND DISPOSABLE LINUX EXPERIMENT; **PRODUCTION PROTECTION NOT IMPLEMENTED**.

## IMPLEMENTATION

### M12j observed native checkpoint, preserved with provenance

The operator explicitly ran the standalone M12i Quickshell `FileView` receipt lab and supplied screenshots plus read-only terminal inspector results in the previous conversation. The evidence is **operator-observed** and remains separate from GitHub CI.

| Operator-observed boundary | Reported result |
| --- | --- |
| Standalone M12i lab attached | `JSON_ACTIVE`; counter initially 0 |
| First native save | UI counter 1, settled receipts 1 |
| Second native save | UI counter 2, settled receipts 2 |
| Freeze | `FREEZE_REQUESTED`, `TEST_FROZEN`, counter 2 |
| Read-only SQLite receipt inspection after stop | Eight checks passed: counter 2, frozen journal, no pending stage, exactly two settled-unacknowledged receipts, matching expected and actual digests, matching stage chain, final digest equal to source |
| First recovery attempt | Invalid wildcard fixture path was entered literally; inspector refused or phase mismatched; **not counted as native success** |
| Corrected fresh instance | Native UI displayed recovery review; corrected read-only inspector returned `SYNTHETIC_JOURNAL_MATCH` with expected `RECOVERY_REVIEW` and counter 2 |
| Native callback origin and production authority | **NOT PROVEN**, inspector deliberately reported `independentNativeAcceptance:false`; live guarded TASKS writer remains disabled |

Machine-readable redacted record: `tests/tasks/fixtures/task_native_receipt_external_writer_m12k.json`. It excludes the user's exact machine path, screen captures, actor IDs, private keys and raw file hashes. This record is historical evidence from the operator's chat, **not a direct GitHub attachment to the original Linux machine**. Final operator acceptance of production operation was not given.

### What M12k tests

The M10p ownership `flock` is advisory. A process with the *same effective Linux user identity* may replace the owner-writable disposable JSON file while the SQLite authority lock remains held. The M12h receipt scheme compares exact bytes but does not authenticate which process wrote them, nor can it atomically commit an SQLite row and a separate filesystem JSON pathname against a hostile concurrent writer.

`tests/tasks/test_task_uncooperative_writer_m12k.py` starts a **real second Python process**, unrelated to the cooperative owner, that ignores the lock and may replace only a temporary `/tmp/m12k-*/m11e-fileview-test/fixture-only.json`. The child enforces the exact synthetic filename, private directory owner/modes, private regular existing source file and fixture schema. The original M12h fixture, M10p, M11g, Quickshell UI and production writer are **unchanged**.

The regression matrix separates **detection**, **unproven provenance**, and **race exposure**:

| Experiment | Result we expect to observe | Security interpretation |
| --- | --- | --- |
| A separate same-UID process replaces the file while M10p flock held | Replacement succeeds | Advisory lock does **not** fence noncooperating writer |
| External revision change before reservation | M12h `EXTERNAL_SOURCE_BEFORE_RESERVE` | Ordinary changed-source detection works |
| Wrong revision after reserve, before readback | Durable `REVIEW_REQUIRED`, epoch bump, pending retained | Wrong bytes fail closed |
| Outsider writes the **exact expected bytes**, with **no FileView write** | M12h settles and hashes match | Exact bytes do **not** authenticate writer/callback origin |
| Outsider changes source after settlement | Next reservation detects drift | Detection is periodic, **not continuous fencing** |
| Outsider races after second host readback, before SQLite settlement commit | Receipt may settle while actual file has different bytes | TOCTOU vulnerability; separate JSON and SQLite are not atomically fenced |

The race test uses deterministic injection at the specific second stable readback boundary, rather than gambling on scheduler timing. It confirms **an existing limitation**, not that an attacker has been prevented.

### Trust/ownership choices awaiting operator authorization

No new production host, privileged helper, authorization key or writer is selected by M12k.

- **Provisional option A:** Acknowledge same-UID noncooperating writers as out of the threat model; use readback checks and manual recovery for ordinary accidental edits only. This explicitly does **not** meet an adversarial same-user requirement.
- **Provisional option B:** Establish an independently trusted owner/broker and OS-enforced isolation that prevents untrusted same-UID processes from modifying the source. This likely changes the current Quickshell `FileView` direct-write ownership and requires separate architectural and operator approval, including source permissions, authenticated launcher, rollback and UI callbacks.
- **Provisional option C:** Scope a separate immutable/generation-verified source protocol with an authenticated intermediary, a carefully defined filesystem threat model and read-only client, again requiring explicit redesign and native acceptance.

The critical distinction: a root/admin-controlled verification key **alone** authenticates code release provenance, but cannot stop a different same-UID writer from modifying a file still writable by all programs with that user's filesystem authority. OS ownership design must be selected before claiming hostile-writer protection. No option becomes canonical simply by merging this evidence PR.

## HOW TO USE

There is no new Post-Apollo UI, local Fedora test, live host or activation. GitHub Actions runs only disposable fixtures:

```sh
python3 tests/tasks/test_task_uncooperative_writer_m12k.py
```

A passing test is a **demonstrated threat and expected fail-closed regression**, not proof of full protection. The old M12j on-machine fixture remains untouched and should be preserved until an explicit operator decision.

## VERIFY

- Inspected latest GitHub main and Syntagma / Hospital work permissions; no open competing TASKS PR or M12k branch before implementation.
- Expected diff: exactly this report, a sanitized JSON checkpoint, one isolated Python test and a scoped CI workflow. No production source/QML code changed.
- M12k CI exercises the actual OS child and synthetic M12h SQLite receipt plus older M12h/M12i/M11t/M11d regression suites. No Quickshell native process launches in CI.
- M11t's original nine production gates and M12b's ten evidence topics remain **OPEN** even if tests pass.

## WATCH OUT FOR

- **Do not declare `NATIVE_STAGE_ATTRIBUTION` or `OS_HOST_OWNER` complete.** Native callbacks are correlation hints; the same-user external writer can forge byte-consistent receipts.
- The test is deliberately in an independent disposable directory, **not** the historical M12j folder. No real TASKS source is read.
- Same-user writes, root compromise, power-loss ordering and rollback-resistant persistence are distinct threats. M12k demonstrates only one family of risks and does not solve them.
- A successful SQLite transaction covers the SQLite receipt and pending row; it cannot atomically cover an independently mutable JSON source path without additional coordination or a different storage architecture.
- The M12j result is an operator-provided checkpoint with read-only journal checks, not a cryptographically signed provenance artifact.
- Host authentication, single-writer preservation, asynchronous UI semantics, real-file access, key custody and native acceptance need fresh, scoped decisions before any deployment.

## CHECKLIST

- [x] Reconstruct M12j observed checkpoint and receipt verification from the current conversation
- [x] Read latest GitHub source, ownership and Syntagma protocols
- [x] Record redacted evidence without task content or user paths
- [x] Add actual same-UID noncooperating subprocess test restricted to disposable fixture
- [x] Expose wrong-byte refusal, exact-byte origin confusion and TOCTOU window
- [x] Keep live TASKS writer hard-disabled and existing M12h/M12i unchanged
- [ ] CI and independent PR review
- [ ] Operator review and merge
- [ ] Decide hostile-writer threat model / trusted writer architecture
- [ ] Separate approval for production implementation, local changes or activation

## NEXT

Review M12k and its CI. If the operator wants protection against malicious same-UID writes, the next milestone must be **an independently approved source ownership architecture**, not merely a stronger test assertion. Otherwise continue fail-closed detection and last-confirmed UI integration under an explicitly narrower threat model. Preserving one live TASKS source owner remains an invariant.

## DECISIONS

**Implemented:** Redacted M12j native checkpoint plus isolated Linux subprocess tests that demonstrate both existing detection and known noncooperating-writer gaps.

**Still OPEN:** Real signer/root custody, OS-isolated host, source permission, authenticated stage attribution, full native acceptance, asynchronous UI contract, rollback and explicit final activation.

**Not authorized:** Production TASKS access, a new live JSON writer, real signing-key creation, local Fedora edits, Quickshell restart, real-data migration, data restore, PR merge, staff reassignment or live Hospital registration.
