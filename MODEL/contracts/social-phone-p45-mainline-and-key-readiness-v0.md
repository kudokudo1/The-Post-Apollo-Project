# PHONE P45 // Mainline P44 reconciliation + protected read-only key seam + honest save result

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Role:** external Hospital-compatible DOC, PHONE assignment; live Room/Assignment/Session unverified  
**Recovery root:** current `main` immediately before P45; P43 PR #1947 and stacked P44 PR #1956 were BOTH marked merged by GitHub. P44's eight changed files did **not** arrive on `main`, because its PR targeted P43's side branch.

## IMPLEMENTATION
1. **Repair actual mainline:** Reconstruct every changed file from original exact-head P44 commit `af14fda86ce3b9ff61f2c1801ce8f989da5d52ae` onto a new branch based on current `main`, including the Favorite/Note two-action JS plan, real AES-GCM synthetic transaction coordinator, workflow, tests, contract and integrated Quickshell edit-review text. Do not alter C3e/C4b/C5 or unrelated widgets.
2. **Protected key read path:** `PhonePersonalProtectedKeyP45.py` introduces a distinct, dormant PHONE-owned **read-only** Secret Service lookup mechanism. It uses a 128-bit opaque externally enrolled selector under a separate protected namespace, a fixed absolute `/usr/bin/secret-tool` path, a bounded empty-stdin lookup and strict canonical 32-byte URL-safe-base64 decoding. No key, note, profile or provider error is included in public exceptions. It cannot create, unlock, rotate, delete or back up key material. A future independently verified installed host must control who calls it, own the selector, pin executable provenance and enforce locked-state denial before any keyring call; a same-UID script can forge its arguments and Secret Service may prompt. This module is **not** authentication or a production key release grant.
3. **Honest UI result:** `PhonePersonalSaveFeedbackP45.js` maps exact non-authorizing statuses (HOST_UNAVAILABLE, KEY_LOCKED, CONSENT_REVOKED, CONTACT_STALE, PARTIAL_UNCONFIRMED, COMMIT_UNCERTAIN, INVALID_EDIT) into content-free messages with `saved:false`, `retryAuthorized:false`, `productionEnabled:false`. It intentionally cannot convert any caller-supplied `SAVED` flag into a success. P42/P44 editor shows HOST UNAVAILABLE until a genuine trusted native channel exists, without displaying note text or unlocking SAVE.
4. **Regression:** Dedicated GitHub workflow and source tests require P44's exact files and editor import to physically exist in the PR tree, plus P44 encrypted matrix, P43/P42 editor, P35/P36/P40R, key retrieval and UI result tests. This guards against repeating a side-branch 'merged but absent on main' mistake.

## HOW TO USE
No operator-facing save yet. After a separate reviewed merge/deployment, P44's native review explains one vs two approvals. The protected-key source is **not connected to QML, any real service, or a production keyring**. It is a library mechanism for the future installed PHONE host to review. Do not provision or store real keys by manually running commands or inventing a selector.

## VERIFY
Test canonical Secret Service lookup arguments, no PATH shadow, no secret in subprocess argv/environment or returned error, refusal of missing/locked/tampered key data, and no provisioning. Check all fail/revoke/partial/uncertain UI statuses remain not saved and non-retryable; fake saved status refuses. Rerun full P44/P35/P36/P40R/P43/P42 regressions. Native Fedora/installed Secret Service behavior and real human C5 consent remain unverified.

## WATCH OUT FOR
A 128-bit selector is **not a capability**. A read-only local Secret Service lookup does not authenticate an installed RPM, Linux process, seat or C5 human. A fake UI status never authorizes SAVE. P35's optional callback and P36 fixtures are not non-forgeable. The missing independent C3e/C4b/Identity signatures, external one-use challenge/rollback ledger, genuine C5 phone action and hardened PHONE key creation/unlock/backup/rotation/erase + lease remain governed by issue #1885. Do not claim the P45 adapter is a completed lifecycle. Quickshell SAVE and real Favorite/Notes storage stay disabled.

## CHECKLIST
- [x] Recheck merged P43 and P44 and verify P44 missing from current main.
- [x] Reconcile eight exact P44 source/test/CI/UI files onto fresh main-based branch.
- [x] Add dormant, read-only protected Secret Service key-lookup library and adversarial tests.
- [x] Add honest deny/partial/uncertain UI feedback model and tests.
- [x] Add mainline completeness regression.
- [ ] Exact-head GitHub CI, operator review and merge.
- [ ] Genuine independent installed C4b/Identity host signer and C3e issuance/consume/revoke authority.
- [ ] Genuine C5 PHONE-specific one-use explicit SAVE consent.
- [ ] Protected PHONE provisioning/unlock/rotation/backup/erase, host-owned immutable lease through P35 ciphertext CAS and acknowledgment, trusted readback, native Fedora verification.

## NEXT
Do **not** stack merge into an already merged feature branch. Review this PR targeting `main`, ensure all P44 files really exist after its eventual merge, then complete real installed protected PHONE service with verified independent C3e/Identity/C5 receipts and protected key lifecycle. Only then connect UI SAVE and show authenticated saved/readback states.

## DECISIONS
GitHub source-only with explicit independent PR; no local machine mutation, service install, real keyring access, notes, iPhone write, external-owner modification, merge or production activation. Operator remains final authority.
