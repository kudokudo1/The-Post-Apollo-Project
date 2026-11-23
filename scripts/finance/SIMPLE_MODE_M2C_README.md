# FinanceW Simple M2c // View-only Move Money preview in Budget

## IMPLEMENTATION

**Scope: GUI integration only.** FinanceW now shows **MOVE MONEY // PREVIEW**
under **+ ADD MONEY** in the **SIMPLE** experience of
**Finance → Budget → Budget**. The button opens the existing
`FinanceEnvelopeMovePreviewPane.qml` from M2a within the **existing**
budget scroll area, with the same authenticated
`financeBudget.snapshot` object as the other budget controls.

- The form selects source and destination expense envelopes, takes a
  positive dollar amount, and displays both available balances before
  and after the proposed move. The amount and available funds are
  calculated from the M2a pure policy.
- The form does **not** save, confirm, request, execute or emit any write.
  **HIDE MOVE MONEY PREVIEW** / **CANCEL** closes it.
- The launcher appears only in SIMPLE. It refuses opening when the
  Finance Budget page is not ready, while other money editors or
  pending/uncertain operations are active, or when fewer than two
  envelopes are available in the authenticated snapshot.
- While the preview is open, the Simple/Advanced selector is blocked
  until the preview is closed. The Add Money button and header refresh
  are disabled to avoid competing panels.
- Closing FinanceW, changing main mode, changing Budget submode,
  selecting another Budget tab, or refreshing/changing source/month
  clears the preview. Any input change clears the calculated result.
- `sourceReady` now also checks a valid sourceKey/month and finite
  bounded integer-cent TO BUDGET amount, matching the source-only
  M2a policy. Invalid snapshots do not open the editor.
- The footer explicitly says
  **PREVIEW ONLY // NO CHANGES SAVED // WRITER NOT CONNECTED**.

## HOW TO USE (after merging and reloading FinanceW)

1. Open **Finance → Budget → Budget → SIMPLE**.
2. Click **MOVE MONEY // PREVIEW** beneath **ADD MONEY**.
3. Select two different envelopes using the **FROM** and **TO** cycling
   buttons, type a positive amount, and choose **PREVIEW MOVE**.
4. Inspect source and destination before/after available balances,
   plus unchanged unassigned money.
5. Click **CANCEL** or **HIDE MOVE MONEY PREVIEW** to close.

This is **budget allocation planning only**, never a bank transfer.
No real budget mutation occurs from these controls.

## VERIFY

- `tests/finance/test_finance_simple_m2c_view_contracts.py` checks
  that FinanceW mounts the view once under Add Money, shares the same
  source, refuses conflicting modes/editors, invalidates on navigation,
  and contains **no M2b CLI bridge, permit or save action**.
- Updated M2a and M2b contracts remain strict about source validation
  and inactive write authority, while accounting for the now-mounted
  view-only QML.
- The existing FinanceW contracts workflow runs the new test and the
  updated M2a/M2b authority checks.
- The existing Budget Qt geometry workflow loads the **actual** QML
  preview with fictional source data, including invalid keys, months,
  lost source, refresh invalidation, source insufficiency and an
  overspent destination. This does not prove native Silverblue visuals.

## WATCH OUT FOR

**M2b is already merged at source level but must stay HARD OFF.**
It uses two non-atomic Actual API assignments and currently awaits
an **independent Nurse 2 security/recovery review**. M2c does NOT
mount its service, provision any `envelope-moves-enabled` permit,
alter writer journals or credentials, or authorize actual allocations.

**Operator's earlier visual PASS was for M1's Simple/Advanced selector,
not the newly mounted Move Money pane.** M2c needs its own desktop
visual acceptance once the operator merges the PR.

## NEXT / DECISIONS

Leave M2c in DRAFT pending shared FinanceW root integration review,
exact-head CI and operator merge approval. After M2c visual acceptance
and independent M2b security approval, a separate M2d review may
consider a protected, explicitly gated Save/Confirm bridge. Do not
treat preview success as financial-write acceptance, and do not
simulate envelope movement by calling the single-category writer twice.

The scope is the existing Budget root, read-only preview pane,
associated tests and workflows, and this README. No user host or
actual financial records were touched.
