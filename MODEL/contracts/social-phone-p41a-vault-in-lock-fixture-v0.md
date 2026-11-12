# Social PHONE // P41a synthetic final check inside P35 write lock

**Patient:** `kudokudo1/The-Post-Apollo-Project`. **Staff:** external Hospital-compatible ordinary DOC, PHONE-owned security seam. **Live Room / Assignment / Session:** unverified. **Checkpoint:** merged P40R PR #1930; dependency issue #1885 remains OPEN.

## IMPLEMENTATION
P35 encrypted `commit` already serializes cooperative ciphertext writers using a per-vault `flock`, verifies revision and atomically replaces the file. P36's synthetic host observer formerly checked permissions immediately **before calling** `commit`, leaving an additional interval before the actual locked publish.

P41a introduces optional `pre_publish_check`, invoked **after revision comparison and while holding P35's existing write lock, immediately before `_publish`**. Non-callable, nonliteral-True and throwing callbacks refuse without writing a new sealed file or exposing exception text. P35's existing callers remain source-compatible; the hook is optional and is not a new production authentication requirement. The P36 fixture now passes its fresh observed Personal/owner/session/selected-row and synthetic gesture comparison into this seam.

This is an ordering/critical-section **synthetic fixture**. Arbitrary Python callbacks are forgeable by a same-UID process; P35's file lock only coordinates cooperating writers, not C5 consent or kernel device state. A valid callback can be revoked immediately after it returns; a production host still needs an independent non-forgeable authorization lease whose lifetime spans publish and commit acknowledgment. These changes are not a consent or key-release grant.

No production QML, D-Bus, CLI, iPhone, BlueFerry IPC, on-host keyring, generic Favorites++, Notes, C3e/C4b/C5, message, or call implementation is changed.

## HOW TO USE
There is no additional PHONE button. Real FAVORITE and NOTES remain disabled. The new code runs only in synthetic regression tests until independently authenticated producer interfaces are available.

## VERIFY
- P41a checks that the callback executes inside P35's real OS `flock` and only literal `True` allows publication.
- Adversarial tests revoke synthetic human consent after P36's earlier checks, **once P35 has acquired its write lock**, verifying no ciphertext replace and no sensitive error leak.
- Stale revision callbacks must not run, and failed callbacks leave existing ciphertext unchanged.
- Dedicated disposable GitHub CI also runs P35, P36, and P40R regressions with isolated synthetic data.
- Exact PR-head GitHub CI and native Fedora behavior remain separate evidence gates.

## WATCH OUT FOR
P41a is not a trusted host. Do not promote a test callback, passed CI, file lock, signed fixture, or unlocked Secret Service collection into production authority. The real transaction must integrate independently enrolled C3e/C4b/Identity installed-process evidence, C3e one-use challenge consumption, C5 authentic human approval, a host-owned non-forgeable lease and protected PHONE key custody. Crash/rollback safety remains a distinct source of truth; P40R read-only observations are not durable commit receipts.

## CHECKLIST
- [x] Recover merged P40R and independently re-check issue #1885.
- [x] Add in-lock optional synthetic prepublication recheck.
- [x] Reuse P36 fixture's explicit current authorization, owner, session and selection checks.
- [x] Add fail-closed adversarial tests and dedicated CI workflow.
- [ ] Verify exact PR-head tests and operator review before any merge.
- [ ] Receive real independently verified C3e/C4b/Identity/C5 producer interfaces and key lifecycle.
- [ ] Design host-owned non-forgeable atomic authorization/commit lease and receipt ledger.
- [ ] Native Fedora installed-host verification with separate explicit local approval.
- [ ] Operator final acceptance of real favorites and notes.

## NEXT
Use issue #1885 to obtain exact authentic upstream signed receipt bytes, independently enrolled trust roots, session and one-use consent evidence. Then build the PHONE-side production verifier and protected save service under explicit scope authorization, with final check spanning a real host-owned lease. Keep P40 locked UI and all other systems untouched until then.

## DECISIONS
No production write authority, new key handling, live machine change, merge or deployment. P35 `commit` remains backwards compatible for existing tests, but no standalone P35 call becomes a secure public interface.
