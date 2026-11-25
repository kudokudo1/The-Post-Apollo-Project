# FinanceW Research M10a // Protected local-store unknown-outcome boundary

**ROLE:** Research DOC · external Hospital-compatible · non-independent implementer  
**PATIENT:** The-Post-Apollo-Project  
**SCOPE:** Research-owned M2 store and disposable regression only  
**PRODUCTION RESEARCH WRITES:** HOLD · **LIVE FINANCEW SAVE:** DISCONNECTED  
**STATUS:** Candidate hardening requiring independent Nurse 2 security review and operator approval

## IMPLEMENTATION

The previously merged M2 store used an exclusive lock and atomic JSON replacement. A safety defect remained: after \`renameSync\` succeeded, the final directory \`fsyncSync\` could fail, yet the unconditional \`finally\` block deleted the lock. The next write was permitted even though the earlier save's outcome could not be acknowledged. The same problem existed for a rename whose outcome was unknown.

M10a makes the writer **fail closed across the commit boundary**:

- Fsync the exclusive lock and containing private directory *before* attempting the save.
- Enter an explicit \`uncertainCommit\` state **before** calling \`renameSync\`.
- When the rename or subsequent directory fsync cannot be confirmed, refuse with \`COMMIT_OUTCOME_UNKNOWN\` and **retain the already-created private writer lock**. Later writes fail with \`WRITE_BUSY\` until external recovery/review.
- When a write fails *before* the rename attempt, clean up the temporary file and release the lock.
- After a confirmed durable commit, release only the lock inode actually created by this process, rejecting a changed/replaced lock with \`UNSAFE_LOCK\`.
- Synchronize the directory after lock release as well. Uncertain lock-release results remain errors, not successful acknowledgements.
- Refuse pre-existing symlinked ancestor components before creating any Research directory; create missing components one-by-one rather than recursive mkdir (which followed unchecked parents). A deliberately symlinked custom XDG data path will now fail closed.
- Refuse hardlinked Research files and refuse a file whose inode changes between the lstat preflight and O_NOFOLLOW open. Cap read allocation to 500001 bytes even if the file grows after fstat.
- Replace the CLI's unbounded \`readFileSync(0)\` with a maximum-8KiB, single-newline frame reader which can finish when stdin remains open (Quickshell's typical behavior).
- Keep existing encrypted-storage and protected-writer boundaries unchanged. No new QML writer hooks, no automatic retry/recovery, no financial account access or source-data logging.

## HOW TO USE

No new operator action or desktop test. Research remains read-only + ephemeral scratch. **Do not manually delete a stranded lock** merely to make Save work.

A later authorized recovery process must first compare the durable revision and contents against the attempted operation, retain evidence of the ambiguous outcome and authorize any lock release. Reissue of the original write is never automatic.

## VERIFY

- Existing M2 read/write tests and M1 model test, unchanged.
- New \`tests/finance/test_research_m10a_store_commit_uncertainty.mjs\` creates only isolated disposable temp stores and fault-injects failures before rename, during rename, after rename on directory fsync and during lock inode replacement.
- Tests assert an ambiguous save preserves the exclusive lock and blocks further writes, while read-only access remains possible for recovery; precommit failure cleans up safely; replaced lock isn't deleted. Extra disposable tests reject ancestor symlink creation, hardlinks, swapped read inodes and a file growing after fstat.
- Subprocess tests require a writer that finishes from a single frame without stdin EOF and refuses oversized/multi-frame input.
- Real Linux child-process `SIGKILL` immediately before and immediately after rename verifies retained locks and blocked subsequent writes across process death. This is not a power-failure durability certificate.
- Exact-head GitHub CI and Fedora 44 Linux test are required before describing this revision as validated. An independent reviewer must inspect the source, race behavior and tests.

## WATCH OUT FOR / UNSOLVED SECURITY ITEMS

This change deliberately **does not certify or activate** M2. Additional independent work is required:

1. Static ancestor symlink checks now fail closed, but same-UID adversarial path replacement **between** filename operations remains a residual race; inspect whether directory-fd-anchored operations or stronger OS-native primitives are necessary before protected activation.
2. Verify lock creation and release behavior under real SIGKILL and power-loss/uncertain-rename crash matrices, with retained recovery pointers.
3. Define explicit operator-controlled recovery procedure and any durable acknowledgement/attempt ledger; a stranded lock is *safety* but not a pleasant product workflow.
4. Confirm that unencrypted JSON storage is acceptable **only** for nonconfidential public-market Research notes. The user expects reliable persistence, but this storage is not a banking vault.
5. Independent Nurse 2 review, operator approval, UI write adapter, and desktop end-to-end save/reload/restart are all separate gates. No prior Research PR has an independently submitted GitHub PR review recorded for this storage lane.

## CHECKLIST / DECISIONS

- [x] Reconstruct M2 code and existing read-only/temporary integration.
- [x] Identify unknown-outcome lock cleanup bug.
- [x] Add explicit conservative commit-boundary semantics.
- [x] Add reproducible disposable safety regression and Fedora native workflow.
- [x] Add static ancestor-symlink/hardlink safeguards, inode identity check and bounded store reads.
- [ ] Exact-head workflow verification and independent security review.
- [ ] Independent assessment of remaining path-swap races, SIGKILL/OS crash recovery and protocol review.
- [ ] Express operator approval before live writer or host modification.

The decision to keep M2 disconnected and fail closed is conservative and preserves the existing HOLD, not a decision to permanently deny the product Save capability.
