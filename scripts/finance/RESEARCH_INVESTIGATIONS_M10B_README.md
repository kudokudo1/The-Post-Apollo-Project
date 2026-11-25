# FinanceW Research M10b // Read-only interrupted-save recovery inventory

**PATIENT:** The-Post-Apollo-Project  
**ROLE:** Research DOC implementer · external Hospital-compatible, no live registration claimed  
**SCOPE:** Research-owned inspection tool and tests only; M2 write store unchanged  
**PRODUCTION WRITES / LIVE FINANCEW SAVE:** HOLD

## IMPLEMENTATION

M10a hardened the store's exclusive lock against a crash or a directory fsync failure after a JSON file replacement. Such a lock *intentionally* prevents subsequent writes because the previous outcome may not be known. M10b adds the **non-mutating diagnostic half of recovery** without automatically deleting locks or retrying writes.

\`scripts/finance/research_investigation_recovery_probe.mjs\`:

- Calls the existing protected **read-only** M2 \`list\` operation, including its private path and file-integrity checks.
- Returns the observed schema revision, count of investigations and evidence entries, and a SHA-256 fingerprint of the returned JSON document, **not the notebook's content or URLs**.
- Observes whether the lock is absent, present and owner-private, or unsafe/unavailable. A present lock is always \`REVIEW_REQUIRED\`. A hash of the lock's device/inode/metadata supports comparison on separate inspections but never proves a lock is stale.
- Counts up to 128 directory entries and separately counts orphan M2 temporary filenames and unexpected files without opening or deleting them.
- Returns \`UNAVAILABLE\` on a refused/corrupted/unsafe snapshot, lock or path, rather than guessing that nothing was saved. It never follows a rejected ancestor to enumerate files.
- Exposes \`canUnlock:false\`, \`canRetry:false\`, \`changesMade:false\` in every report, including when no lock is observed.
- Is a read-only executable with zero command parameters and no writer operations. Its JSON result is a bounded, single-line \`FINANCE_RESEARCH_RECOVERY_RESULT ...\` frame.

**This tool is for a future protected recovery interface or independent reviewer. It is not a new operator-facing button.**

## HOW TO USE

No operator action required and no desktop test. The UI still has its writer disabled.

A future approved recovery interface could read the report and show:

- \`NO_STORE\`: local Research directory does not currently exist;
- \`NO_RECOVERY_LOCK\`: no lock or unexpected files were observed at that instant, **not** permission to write;
- \`REVIEW_REQUIRED\`: lock or orphan/temp evidence exists, and recovery needs human adjudication;
- \`UNAVAILABLE\`: storage/lock/directory is unreadable, unsafe, invalid or too large.

Never instruct a user to delete \`investigations.lock\`, overwrite a corrupt file, or repeat an uncertain save merely because a probe returned a revision. There is **no release/delete/repair capability** in M10b.

## VERIFY

- \`tests/finance/test_research_m10b_recovery_probe.mjs\` creates only private disposable stores. It checks absent and intact stores, stable fingerprints, lock-preserving review, corruption refusal, abandoned temp/foreign-file preservation, malicious lock symlink rejection, untrusted path refusal and a bounded directory inventory.
- It runs the CLI in a private XDG path, verifies zero note contents/path leaks and explicitly rejects an \`--unlock\` argument.
- \`.github/workflows/finance-research-recovery-m10b.yml\` runs on Fedora 44; also reruns M10a fault-injection and SIGKILL tests.
- Standard Research contracts run M10b in the existing Node test matrix.
- Review exact-head workflow results and raw native logs before treating any test claim as verified.

## WATCH OUT FOR

**Read-only inventory does not resolve an uncertain write.** A revision and fingerprint prove only what was observed during one read, not that a previous operation was committed or that no writer is alive. The M2 lock currently contains no authenticated operation identity, caller nonce, prior expected revision or durable attempt receipt. A safe unlock/acknowledgement protocol must be designed and independently reviewed, not inferred from this report.

Remaining security gates:

1. Native Linux same-UID ancestor/directory replacement races between path-based operations; the reader's static checks are not an \`openat2\` / directory-FD guarantee.
2. Independently reviewed persisted write-intent/receipt and lock recovery (or a specified manual-only recovery process) before granting write activation.
3. Real power-loss durability and hostile filesystem conditions beyond SIGKILL tests.
4. Confirm that local unencrypted JSON is limited to nonconfidential, public-market research notes. No credentials, banking details, tax records, or confidential family financial documents.
5. Independent security acceptance and explicit operator authorization for both code merge and any production UI writer installation.

## CHECKLIST / NEXT / DECISIONS

- [x] Provide safe read-only evidence of revisions, lock state and abandoned-file count.
- [x] Keep notes/URLs off stdout and keep all recovery actions disabled.
- [x] Add local disposable regressions and Fedora-native workflow.
- [ ] Exact-head test verification and independent security review.
- [ ] M10c protected recovery/operation identity design and race hardening.
- [ ] Separate authorization before FinanceW Save is ever enabled.

This is the Research owner's bounded source contribution. Independent Nurse 2 remains the security acceptance authority; the operator remains the final approval authority. No live host write is authorized or performed.
