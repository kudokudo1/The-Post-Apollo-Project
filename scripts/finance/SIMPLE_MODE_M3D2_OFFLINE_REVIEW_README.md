# FinanceW Simple/Budget M3d2 // Dormant offline categorized-save contract

**Owner:** FinanceW Simple/Budget successor DOC, Hospital-compatible (live registration unverified)
**Patient:** The-Post-Apollo-Project
**Status:** Draft staged review, no production operation
**Financial writes:** HARD HOLD

## IMPLEMENTATION

This isolated step prepares the eventual M3c-to-M3b handoff without connecting either GUI or writer. A pure data function `prepareOfflineCategorizedReview` calls the merged M3d0 inspector, checks that the selected picker category matches the proposed category, and extracts 11 preview-only fields that match the financial parts of M3b's strict command. It **deliberately omits the executable action and 32-character one-use requestId**. M3b's strict command validator therefore refuses this output as `unexpected-fields`. There is no process, IPC, permission, journal, budget mutation, or native host action.

`recheckOfflineCategorizedReview` recomputes the preview against caller-supplied current source, month, category, account, amount and payee. It refuses edited inputs or altered review fields. **Both functions return `canSave:false` even when they succeed.** This is a consistency check, not a signed authorization, protected runtime observation, or permission check.

No existing source files were changed. The root, transaction editor, category preview pane, live financial writers and read-only service remain exactly as on main.

## VERIFY

The new Node tests use fictional Actual-shaped snapshots through the **real** merged `normalizeSnapshot` and M3d0 inspector, then validate schema compatibility using M3b's existing pure command validator with a **fictional test-only requestId**. They test category switch, source/month and draft edits, stale balances, hidden/unknown/income categories, duplicates, malformed dates, oversized expense previews, and review tampering. A Python source contract ensures no UI import or writer bridge and that the old Save remains blocked when the category plan is active.

The dedicated CI is synthetic, not a real Actual 26.10.0 server test. No runner is authorized to use the user's credentials, accounts, personal financial records, or desktop.

## WATCH OUT FOR

- **M3b writer #2356 has no recorded independent security review.** The real categorized CLI has not been tested against a disposable Actual 26.10.0 server with fresh category readback and failure recovery.
- The merged M3d1 visibility fields may be `null` when Actual omits them. Unknown is not approval.
- The read-only selector defaults to loopback port 5007; writer policy is hard-pinned to 5006. Do not silently weaken source binding.
- Rechecking a snapshot is not freshness proof from the Actual server. A future authorized bridge must execute the existing M3b writer preflight under the global lock after independent review.
- M2b Move Money keeps its separate production HOLD.
- Research, Categories, Banking and other worker-owned files are untouched.

## NEXT

Obtain independent Nurse 2 security review of M3b's actual write/locking/journal boundary and a **dedicated disposable real Actual 26.10.0** categorized-write rehearsal. Reconcile the shared read-only source schema and endpoint config with the Budget source owner. Only after those reviews and explicit operator authorization should anyone separately propose wiring a live categorized Save UI. The only rollback for this source-only PR is a revert; no money or host state changed.

## DECISIONS

No automatic retry, no financial permit creation, no production activation, no merge without operator acceptance. Preserve the existing category-preview Save block.
