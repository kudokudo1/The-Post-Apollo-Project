# 🏥💜 MACHINE // Fail-Closed Cross-Resource Recovery Classification

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
STAFF ROLE // Hospital-compatible external DOC (no verified live attachment)
ASSIGNMENT // Pure read-only recovery-state classification after synthetic ciphertext publication/journal disagreement
SCOPE // New classifier, adversarial unit tests, integration in existing eight-window CI crash matrix, CI workflows, documentation

## IMPLEMENTATION

After Nurse 2's independent [#1925 audit](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1925#issuecomment-6809033498), the repaired SQLite journal/cross-resource crash boundary has **technical test PASS on its exact corrected head**, and #1925 is merged. That pass is limited to synthetic root-only CI scenarios, not a live archive migration.

`MachineBraveCrossResourceRecoveryContract.py` is a **pure function contract**. It compares five independently supplied, already-read structures: the existing #1911 migration plan, before/after source and destination encrypted-record metadata inventories, the #1915 fixture journal's inspection response, and a synthetic count of staged files and observed link counts. It imports existing strict validators; it does **not** read from disk, open SQL, invoke the transfer fixture, talk to a browser or use credentials.

The classifier validates exact schemas and existing non-authorizing flags. Malformed/positively-authorizing inputs refuse; individually well-formed but mutually contradictory evidence produces `manual_reconciliation_required` with stable `hold_reasons`. It distinguishes:

- Source inventory drift, changed preexisting destination sentinel, unexpected target IDs, or changed published ciphertext metadata.
- A staged temporary file still present, or published file with unexpected hardlink count / missing link observation.
- Destination publication without a journal event, journal `published` or `observed` without a destination file, a `rolled_back` phase with the file still present, or incomplete/uncertain receipt phases.
- Journal's own pinned-head mismatch, even when the sampled destination looks complete.
- Fully matched fixture publication/observed phases, which return **`synthetic_consistent_but_untrusted`**, explicitly not an authorized transfer.

Every output, including synthetic consistency, preserves `automatic_retry_allowed=false`, `automatic_cleanup_allowed=false`, `delete_original_allowed=false`, `migration_authorized=false`, `restore_allowed=false`, `requires_independent_human_review=true`, and `safe_actions=[]`. Original archives are never touched. The classifier has no operation that can retry, overwrite, remove or move any file.

The original root-only eight-window test now calls this classifier on the **actual measured fixture** after each child process exit. It compares the new result to its pre-existing expected manual-hold/fixture-consistent status and reasserts all deny-only flags. A second independent test file supplies adversarial metadata input and tests all eight modeled crash states, conflicting metadata, forged positive trust and invalid shape/phase/head evidence.

## HOW TO USE

No desktop, TimeW UI or production CLI exists. GitHub CI runs:

```bash
python3 -B -I tests/timew/test_machine_cross_resource_recovery_contract.py
sudo -n python3 -B -I tests/timew/test_machine_cross_resource_crash_matrix.py
```

The first test is pure synthetic metadata. The second requires disposable root-only Linux CI with synthetic numeric UIDs; **never run the second command on a personal workstation**. No real Brave profiles, history, keys or archives are accessed.

## VERIFY

Exact-PR-head GitHub Actions are required before reporting a technical test PASS. The dedicated classifier workflow, the existing eight-window root fixture (with new classifier integration), the TimeW foundation contracts and Meta Apollo Grammar should all pass. Inspect raw logs, not just check labels. NRS-2 remains the independent review authority.

This only proves that the code **classifies supplied measurements**. It cannot authenticate the source of those measurements, prove independent backup custody, establish an externally protected recovery high-water mark, or sign a real host/process/seat witness.

## WATCH OUT FOR

- An inventory hash or HMAC created with the public fixture key does not prove protected signing authority; a malicious actor controlling all samples can present mutually consistent but false data.
- Real filesystem publication and SQLite COMMIT are separate durable operations. No power-loss/fsync fault injection, adversarial concurrent file replacement, SELinux/ACL or cryptographic storage custody guarantee is delivered here.
- A correctly formed `fixture_pinned_head_observed` is a synthetic statement from the fixture, not an authenticated external rollback floor.
- Validity of `synthetic_consistent_but_untrusted` **never** grants safe actions, even when all entries match.
- The protected metadata broker remains DENY-ONLY. C3e signed active host/process/seat evidence and C5 one-use human consent are separate unfulfilled gates. No automated archive migration, backup deletion or Brave session restore is enabled.
- No silent merge or production activation. Operator controls final acceptance.

## CHECKLIST

- [x] Reconcile current main, #1925 post-merge NRS-2 PASS, and MACHINE ownership
- [x] Add one pure classifier with strictly negative authorization
- [x] Exercise all eight crash states and independent source/target/ledger inconsistency conditions
- [x] Bind classifier to the existing root-only crash fixture's measured metadata
- [x] Add independent tests, CI triggers and protocol handoff
- [ ] Exact-head GitHub CI and independent Nurse 2 security review
- [ ] Operator merge/acceptance decision
- [ ] Future independent protected custody/witness, recoverable durable state, C3e/C5 and actual Brave restore

## NEXT / DECISIONS

Keep the PR **DRAFT and UNMERGED** until technical CI and independent review. If the classifier tests expose a new ambiguity, fix the bounded contract without expanding archive privileges. The subsequent milestone, once accepted, should address externally authenticated recovery witnesses and custody under a separate operator-reviewed assignment. This PR authorizes **no** action against an archive or installed desktop.
