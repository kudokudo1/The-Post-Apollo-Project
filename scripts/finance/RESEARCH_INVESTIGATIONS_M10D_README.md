# FinanceW Research M10d // Linux pinned-directory read-only proof

**PATIENT:** The-Post-Apollo-Project
**STAFF:** external Hospital-compatible FinanceW Research DOC
**SCOPE:** new isolated Linux read-only directory descriptor module and disposable tests
**PRODUCTION RESEARCH SAVE:** HARD HOLD
**OWNERSHIP:** Research only; no shared FinanceW.qml, Banking, Simple, Market or Connections changes

## IMPLEMENTATION

Research M10a (merged #2646) retained locks after interrupted writes. M10b (merged #2657, independently scoped reviewed) implemented read-only diagnosis. M10c (merged #2710, independently scoped reviewed) added a prior/proposed write-intent fingerprint in the lock. Those reviews deliberately did **not** accept the M2 store's pathname-based ancestor/path replacement race risk.

M10d is a separately reviewable **read-only** native Linux experiment, not a new activated storage writer.

The module scripts/finance/research_directory_anchor.mjs walks an absolute path from filesystem root one directory at a time using pinned Linux file descriptors and /proc/self/fd/<fd>/<child> paths with O_NOFOLLOW|O_DIRECTORY. It checks the final Research directory's owner and private permissions, then retains that pinned descriptor for bounded, O_NOFOLLOW reads of only investigations.json and investigations.lock. It requires a normal private single-link file. It refuses missing, unsafe or symlinked components and never falls back to following mutable full-path strings.

The read-only anchor exposes no write, rename, delete, lock clearance, permission grant, retry, subprocess or user-file-creation operation.

## WHY THIS MATTERS

A conventional lstat(fullPath) followed by open(fullPath) permits a malicious or concurrent actor to move/replace one of the parent directories between operations. The existing M2 writer still uses that pattern in several places. M10d tests holding the intended directory inode while an ancestor is renamed and replaced with a symlink, including a synthetic swap **during** descriptor traversal.

The pinned read continues observing the original directory rather than reading the decoy. This is **not a full write-path fix**. A directory descriptor can still point to a directory that was moved to an unexpected location, so any future writer integration needs protected path-continuity policy and tests. The /proc/self/fd strategy also depends on the host Linux procfs and needs independent deployment compatibility review. This is not a claim that kernel openat2 RESOLVE_BENEATH/NO_SYMLINKS has been implemented.

## HOW TO USE

No new operator steps. The live FinanceW Research interface is unchanged and the permanent Save writer is disconnected.

For developers, only in private disposable storage:
node tests/finance/test_research_m10d_directory_anchor.mjs

The test's cleanup deletes only its own randomized temporary directory. No user XDG data, Quickshell reload or live finance action occurs.

## VERIFY

- Tests pin a directory and read its private investigation file.
- Rename a trusted ancestor and substitute an attacker-controlled symlink; the held descriptor still reads the original file and fresh traversal refuses the symlink.
- Race ancestor substitution during the descriptor walk; the final file still comes from the originally opened parent inode, not the decoy.
- Refuse file symlinks, hardlinks, nonallowlisted names, size limit violations, missing directories, and reads after close.
- Require no privilege escalation, no package install on the user's machine.
- Standard Research contracts run the test and a Fedora 44 native workflow reruns M10b/M10c regressions.
- Verify exact-head CI and independent review before accepting M10d beyond the isolated prototype.

## WATCH OUT FOR

1. **Not yet connected to M2.** No claim that the running writer is protected against path swaps.
2. /proc/self/fd is Linux-specific and is not identical to a dedicated openat2 syscall. Verify procfs availability, container behavior and races before any protected writer use.
3. An inode can remain pinned after its directory is renamed. A future writer must decide whether relocated paths are permitted; never infer permission solely from inode stability.
4. Same-UID actors, real OS power loss, the stranded lock recovery procedure, plaintext Research file sensitivity, independent Nurse security review and the operator's final approval remain separate gates.
5. No new GUI Save action, no automatic retry and no lock-unlock functionality.

## CHECKLIST / NEXT / DECISIONS

- [x] Isolated read-only directory-descriptor proof added.
- [x] Deterministic synthetic ancestor swap and Linux native regression authored.
- [ ] Exact-head GitHub CI and independent scoped review.
- [ ] M10e proposed: adapt the **M2 read path only** to a verified descriptor-anchored primitive after review; preserve no-writes mode.
- [ ] Independently design and verify descriptor-based **write path** and stranded lock adjudication.
- [ ] Operator approval before any live Save activation.

**Decision:** keep this isolated prototype read-only. The goal is reliable persistent Research, but not at the price of silently weakening its storage boundary.
