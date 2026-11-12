# Social PHONE // P44 full Favorite/Notes transaction rehearsal and exact one-action plan

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room:** Social PHONE scope, external Hospital-compatible DOC, live Room/Assignment/Session not verified  
**Branch:** stacked atop P43 draft #1947 because P43 ingress is not yet merged; P44 must not be merged ahead of its dependency  
**Mainline checkpoint:** P41b #1944 and P42 #1946 merged. Issue #1885 still open. C4b/Identity, C3e, C5 external real trust still pending.

## IMPLEMENTATION

One **integrated multi-action PHONE release slice** contains:

1. **Review/operation planner:** Pure `PhonePersonalSavePlanP44.js` turns P42's draft into 1 or 2 **distinct** P43 request messages, ordered FAVORITE then NOTE. An unset field is not a change, false is FAVORITE OFF, empty note is an explicit note clear. It rejects wrong selected contact, unexpected permission/nonce/revision fields, oversized/malformed notes and nothing-to-save. Generated plan is labeled `UNTRUSTED_REVIEW_ONLY`, has no IPC, storage, save or implicit consent.

2. **Encrypted transaction coordinator rehearsal:** `PhonePersonalSaveOrchestratorP44.py` accepts that strict plan, validates *all* actions before writing anything, then uses the existing P36 disposable one-action coordinator to perform each action independently. Each step receives a **fresh** distinct test nonce and expected revision. P36 repeats synthetic permission/selected-card checks before key access, after key access and **inside P35's lock** (P41a). The real P34 candidate-matching and P35 AES-GCM ciphertext/CAS are used in an isolated temp directory. LINK/UNLINK are separate explicit human workflows, never silently added to a Favorite or Note request. Results are content-free and always `productionEnabled=false`, `humanConsentVerified=false`, `durableCommitProven=false`, `retryAuthorized=false`.

3. **Native live review:** The existing P42 draft editor (mounted in P43) now imports the same P44 plan and labels a combined Favorite/Note edit as **2 SEPARATE HUMAN APPROVALS REQUIRED // NOT SAVED**. A one-field draft shows 1 required approval, invalid/no-op draft shows no valid change. Note contents never appear in status. All P42/P43 SAVE controls remain hard-false; this is a review display, not production transaction activation.

4. **Failure behavior:** If the first action succeeds and the second is denied, the first synthetic ciphertext update remains present, and the coordinator returns the number of acknowledged synthetic actions with an **unconfirmed** status. It does not silently roll back/auto-retry or claim the entire draft was saved. If directory fsync fails **after** P35's atomic rename, the result is still unconfirmed, not success. P40R may read current encrypted state but cannot issue a durable receipt.

5. **Comprehensive test matrix:** Node plan tests, native P42/P43 review presentation checks, Python full encrypted run, denied/revoked consent before next step, invalid whole-plan preflight, no key release for revoked action, duplicate nonce prevention, stale revision CAS, explicit Favorite OFF and Note clear, fsync-after-rename ambiguity, no personal content leaks, plus P35/P36/P40R/P43 regressions.

**Critical boundary:** P36 is a TEST FIXTURE with caller-supplied observations and synthetic human gesture. P44 demonstrates exact transaction ordering, encrypted data lifecycle and failure semantics but is not the trusted live installed host and is not wired to a QML SAVE button. No actual user notes or iPhone records are accessed, and no Secret Service/keyring is modified.

## HOW TO USE
There is no new live SAVE. The currently integrated draft editor already displays the number of required approvals, but SAVE is locked. After a future authorized host integration, the edit-review screen must perform the two discrete SAVE confirmation actions and, if the second fails, honestly display a partial/unconfirmed result. P43's live contact detail remains PREVIEW ONLY and `secureSaveAuthorized=false`.

## VERIFY
P44 workflow runs the Node planner and real synthetic AES-GCM P35/P36 encrypted transaction tests, then all relevant regression tests. GitHub CI is not an installed Fedora or independent C5 signature/replay test. Exact PR-head workflow run and operator acceptance must be checked.

## WATCH OUT FOR
- Do not transform a P44 plan into a production grant. It can be created by any untrusted UI.
- Do not serialize note values in logs, request status/error, a queue, debug repr or other public output.
- Protected host must hold an independently verified **per-action** C3e challenge/C5 consent lease through encrypted CAS/ack, with durable replay, release and rollback protections. A temporary P36 `_consumed` set is not sufficient.
- P35 success plus readback is not proof of independent durable commit acknowledgment.
- Protected Personal key namespace, provision/unlock/recovery/rotation/erase, signer enrollment, authentic process/seat and security boundary still need real owner-produced proof.
- Native Quickshell remains untouched. Do not merge stacked P44 ahead of P43 #1947.

## CHECKLIST
- [x] Verify P43 is a still-open draft; do not collide with its QML changes.
- [x] Build complete 1–2 action review planner and reject client-supplied auth fields.
- [x] Implement disposable encrypted transaction orchestration with one fresh nonce/revision per step.
- [x] Test true AES-GCM ciphertext, partial failure, revoke, stale CAS, fsync uncertainty and absence of notes in public result.
- [ ] Exact PR-head checks and independent reviewer acceptance.
- [ ] P43 merge before P44 merge.
- [ ] Genuine C4b/Identity installed source, C3e independent challenge and C5 one-use signed consent.
- [ ] PHONE protected key lifecycle and authenticated host-owned lease.
- [ ] Enable SAVE, secure reread and honest status, then native Fedora verification and operator final acceptance.

## NEXT
**Integrated production host work package**, not further isolated crypto-format PRs: consume actual C3e/Identity signed installed-host and C5 genuine human one-use receipts, enroll independent roots, use host-owned protected Personal keys, hold one-use lease through P35 CAS/commit+readback, tie P44 planned per-action revision to P41b `editHmac` and UI review/cancel. Do not confuse a green disposable transaction with a live service.

## DECISIONS
P44 is stacked GitHub source/tests only, under PHONE ownership. No local host mutation, external owner edits, PR merge, keyring installation, production credential release or active iPhone save. Operator remains final authority.
