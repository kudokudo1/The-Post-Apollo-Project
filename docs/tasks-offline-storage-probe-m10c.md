# TASKS // Proxy 1 M10c Disposable Atomic Storage Probe

**Status:** Isolated GitHub CI test design, not a storage engine deployed on
a desktop. **Dependency:** M10b draft PR #604 remains unmerged as of creation.
This M10c branch and PR are stacked on M10b. The M10c PR must not merge
before M10b is integrated and the branch is rebased/retargeted as appropriate.

## Goal

Test whether a single versioned task+intent envelope is easier to recover
from simulated interruptions than independently persisted model and queue
files. This experiment uses only Node's temporary directories **inside CI**.
It does not modify Quickshell storage paths or attempt any GitHub network calls.

## Files

- `tests/tasks/fixtures/atomic_envelope_fixture.cjs`: Node-only disposable
  writer using a same-directory candidate file. It writes, fsyncs the file,
  renames over the target, and fsyncs the parent directory.
- `tests/tasks/test_offline_atomic_storage_crash_windows.cjs`: tests
  injected exceptions around each stage with the pure M10b journal.
- `.github/workflows/tasks-offline-atomic-storage.yml`: CI test runner.

## Observed and expected fixture guarantees

| Injection point | Logical target observed after simulated process stop | Intent result |
|---|---|---|
| Before candidate creation | Previous complete envelope | Previous complete queue |
| After candidate write | Previous complete envelope; unused candidate may remain | Previous queue unchanged |
| After candidate file fsync | Previous complete envelope; unused candidate may remain | Previous queue unchanged |
| After rename, before directory fsync | New complete envelope **in the running process simulation** | New queue and task together |
| After directory fsync | New complete envelope in the running process simulation | New queue and task together |

These tests check **logical interruption boundaries** only. An injected
JavaScript exception is not an OS crash or power cut. In particular,
**after rename but before directory fsync, real power-loss durability is
not proven**; filesystem/kernel and hardware guarantees need separate work.
Directory fsync protects rename metadata to the extent supported by
the target filesystem. No guarantee of power-loss behavior is claimed here.

The tests further cover:
- stale in-process expected-revision rejection;
- reload of a committed SENDING operation as UNCERTAIN with no re-dispatch;
- a subsequent NORMAL edit without adding GitHub operations;
- malformed or unsupported committed documents refusing replacement;
- the counterexample: two separate JSON files with a crash between
  task and queue writes can disagree.

## Comparison: design options, NOT a final decision

| Strategy | Advantages | Remaining risks |
|---|---|---|
| One JSON envelope | Simple to inspect/back up; one task+intent commit unit; works with a single atomic file replacement | Full-document write amplification; queue growth; writer interleaving requires coordination; post-rename power-loss must be verified |
| Separate model + queue JSON files | Independent scaling and simpler file-level isolation | No cross-file atomicity by default; mismatch/crash recovery requires a transaction protocol |
| Transactional SQLite | Real transactions, indexes and larger queues; can atomically update model+queue within one DB | Requires a reviewed runtime binding/helper, deployment, DB integrity/checkpoint/backups, WAL and power-loss tests |

**M10c only exercises the first and second cases.** SQLite is not benchmarked,
installed, selected or activated here. Node temp fixture results cannot be
directly generalized to Quickshell's `FileView.atomicWrites` semantics.

## Production gates (still open)

1. Review existing Fedora/Quickshell filesystem and packaging compatibility
   without installing or modifying the user's machine.
2. Decide on one-transaction model/queue consistency mechanism, with
   platform-specific durability and locking guarantees.
3. Add a generation/CAS strategy that works across processes, not merely
   the fixture's optimistic revision check; enforce single-writer lifecycle
   or a real transaction lock.
4. Establish read-back and idempotency semantics. A journal receipt string is
   not GitHub confirmation; the Git-owned adapter must verify remote state.
5. Develop a **dry-run only** conversion from v3 task data, preserving
   timestamps, next-ID sequences, task/project relationships, descriptions,
   and all unsupported-version bytes. The M10b example envelope currently
   omits timestamps and is not acceptable as the final migration target.
6. Create backup/restoration verification, injected permission/disk-full
   failure tests, and restart recovery on isolated platform fixtures.
7. Preserve Apollo Hub, TODAY and Proxy 2 PLANNER projections before any
   schema migration or activation.
8. Require the operator to approve a live data migration separately.

## Proxy ownership

Proxy 1 owns pure storage/journal prototypes. Proxy 2 independently owns
PLANNER QML, its date policies, and tests (including PR #602). No changes
to the shared TASKS menu, GitW, live ApolloHubTodoStore/Policy, or desktop
are made in M10c.

## Acceptance

M10c can be accepted as an isolated **process-interruption experiment** if
CI passes and independent reviewers confirm that the tool's limitations are
clear. It is NOT completion of durable live storage, M10, or two-way sync.
