# FinanceW Simple M3b // Nurse 2 security REVISE correction

**PATIENT:** The-Post-Apollo-Project
**ROOM:** FinanceW Simple/Budget
**STAFF:** Simple DOC · implementer (not independent Nurse 2)
**REVIEW INPUT:** https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2356#pullrequestreview-6047684744
**FINANCIAL WRITES:** HARD HOLD, no operator permit provisioned, no GUI Save bridge
**STATUS:** Corrective source PR for independent re-review, not security acceptance

## IMPLEMENTATION

This is a narrow response to the independent M3b **REVISE** review, keeping the source-only categorized expense writer dormant.

1. **Known visibility is mandatory.** Both the category and its expense group's hidden field must be explicitly the boolean false in the fresh Actual preflight. True, absent, null, strings, numbers and objects are refused before journal or Actual mutation. The post-sync budget read also refuses unknown visibility and preserves an uncertain outcome.
2. **Descriptor-anchored private files.** A Linux-only file-trust helper walks absolute paths from the filesystem root using O_DIRECTORY and O_NOFOLLOW opened parent handles. It verifies each directory's ownership and writable bits. Private files are opened with O_NOFOLLOW and O_NONBLOCK, then verified by fstat. Private config files must be regular, owned by the process UID, have only one hard link, and have no group/other permission bits. Root-owned sticky /tmp is permitted; untrusted writable or symlinked ancestors are not. The leaf config/financew and finance journal directories must be private.
3. **Journal-directory trust.** The writer creates missing components through trusted parent descriptors, then uses its verified open directory handle for every lock, prior journal, new journal and fsync. It keeps the original ATTEMPTED journal file handle through COMMITTED, avoiding a pathname reopen after Actual mutation.
4. **Local source binding.** The writer reads actual-server-url through the same private-file trust path rather than accepting a read-only module environment override. Allowed URL remains http://127.0.0.1:5006, and sourceKey still binds the private sync ID. No shared source reader or legacy writer is changed.
5. **Tests.** Policy tests cover missing/malformed visibility and post-sync loss. CLI tests cover symlinked permit/config/credentials/journal ancestors, hard-linked and world-readable journal entries, and descriptor stability after path swap. The pinned Actual 26.10.0 fictional fixture uses the real read-only budget and injects missing/malformed visibility to prove no attempt or add. Prior real roundtrip and SIGKILL checks rerun.

## HOW TO USE

No user-facing change. FinanceW category preview remains read-only. The categorized writer remains disconnected from Save. No new live permit, local file or transaction is created.

## VERIFY

Require successful exact-head targeted CI and raw logs. An **independent Nurse 2 RE-REVIEW** is needed to close the security gate; CI success is not a Nurse 2 PASS.

## WATCH OUT FOR

- Linux /proc/self/fd, O_NOFOLLOW and UID-based ownership validation are intentional. This writer is not declared portable.
- A real host with insufficiently private directories might now be denied. Any permission remediation must be separate and operator-authorized; this PR never silently chmods existing directories.
- Threat model: different-UID attackers and unsafe path substitutions. A compromised same-UID process is not contained by these controls.
- The older D9 transaction writer and all other FinanceW writer implementations are unchanged. They retain their separate security-review responsibilities, shared lock and journal semantics.
- No claim of power-loss safety, all crash windows, or independent security approval.
- No production Save or finance permit activation.

## CHECKLIST / NEXT

- [ ] Verify exact-head policy, CLI, real Actual and crash CI.
- [ ] Obtain Nurse 2 independent exact-head re-review.
- [ ] Address any further findings before planning a separate native Save bridge.
- [ ] Await operator authorization before any production activation or merge.

## DECISIONS / ROLLBACK

This correction stays inside the existing Simple/Budget assignment. Reverting the PR restores previous dormant M3b source and its tests. It does not clear any real finance journal or authorize production use.
