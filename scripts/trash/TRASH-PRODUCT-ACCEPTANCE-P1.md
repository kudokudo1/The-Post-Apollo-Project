# 🏥💜 Trash++ // P1 Consolidated Product Acceptance · Disposable Lifecycle Battery

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ · Universal Resource Lifecycle
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration unverified
ASSIGNMENT // Product finishing package 1: prove already-implemented GIO Burn, managed-copy lifecycle and V2 Archive isolation end-to-end, before native acceptance
BASE // main 63884328e4e192ac05d80c8992247579fedeffd1
AUTHORITY // GitHub CI fixture and source-only tests. No actual user Trash, source-owned writes, key authority, local changes, branch merge or production activation.

## IMPLEMENTATION

The existing **U9–U10c GIO Restore assignment remains closed and accepted**. Its real disposable restore runner explicitly refuses to test Burn. The existing GIO Burn and Burn All commands, managed-copy Burn and V2 Archive snapshot pilot had synthetic tests, but no single cross-backend real-GIO product acceptance receipt.

This package adds only one coordinated validation fixture and its guard tests to the existing Trash workflow:

- `scripts/trash/trash_product_acceptance_p1.py`: **GitHub Actions only**. Before writing, it validates GitHub-runner ownership and uses a newly created private `RUNNER_TEMP/trashpp-product-p1-*` child. Launches a separate `dbus-run-session` whose HOME, XDG storage/cache/config/runtime and GVfs are under this disposable child. The source script checks this private child and the exact initially empty GIO Trash. No actual workstation file can be named as an input.
- Actual `gio trash` of one generated file followed by CLI Burn confirmation refusal, confirmed `gio remove trash:///` Burn and exact single-item receipt/inventory verification. **This intentionally and irreversibly deletes only a random disposable GitHub runner file**.
- Actual `gio trash` of two newly generated files followed by explicit Burn All confirmation and stale inventory refusal; real `gio trash --empty` execution scoped to the **new isolated HOME/DBus/GVfs**; verifies two exact candidate names, two receipts and empty private inventory. No user file or foreign Trash is present.
- In the same disposable HOME, create two tiny fabricated quotes.toscrape.com demo source pages (no outbound web request). Run the **actual CLI** managed-copy Archive→Trash→Restore→Trash→Burn and independently Burn All only the two generated trashed copies. Require verified receipts; no owner source mutation.
- In the same disposable dataDir, run the real V2 `preview`, stale confirmation refusal, confirmed snapshot capture and read-only index before and after managed Burn All. This verifies the retained V2 copy is unaffected by ordinary managed-copy Burn and original demo JSON remains checksum-identical.
- `tests/trash/test_product_acceptance_p1.py`: offline CI guard checks; confirms non-CI invocation refuses before any source, GIO or filesystem modifications, disallows redirected fixture roots and refuses wrong receipts.
- Extends the **existing** `.github/workflows/trash-bottom-left-launcher.yml` to execute after U9 installs GVfs/dbus in the disposable GitHub runner. It does **not** add a recurring separate workflow or edit production QML/Python backends.

## HOW TO USE

No new end-user controls. For development verification, inspect the existing `Trash Bottom-Left Launcher Contracts` workflow on the draft PR and require a PASS receipt with:

```
gioSingleBurnVerified=true
gioBurnAllVerified=true
gioUnconfirmedAndStaleDenied=true
managedRestoreVerified=true
managedSingleAndBulkBurnVerified=true
archiveV2ReadOnlyPreserved=true
originalSourceUnmodified=true
hospitalAuthorityUsed=false
protectedArchiveAuthorityUsed=false
hostAcceptance=false
```

**Never run the real fixture on Fedora or outside GitHub Actions.** The entry gate is defense against accidental misuse, not a cryptographic guard if an attacker forges CI environment variables. Do not copy the command into an operator-host terminal.

## VERIFY

**Requirements before Nurse 2 handoff:**
1. Exact PR-head existing Trash Python/Node suite, U9 Restore real-GIO fixture and the new P1 real-GIO Burn/managed/V2 battery all pass. Grammar passes.
2. Inspect raw CI logs, not only a green checkbox. Ensure new receipt explicitly says `hostAcceptance=false` and both unrelated protected authority paths were excluded.
3. Confirm changed-file list has only this script, offline test, CI workflow and runbook. No Camera, Media, source Archive writers, Hospital, Connections or QML production edits.
4. Continue to treat native Burn, Camera Cleanup/Desktop and V2 UI acceptance as **operator-required**, not something fixture CI can self-approve.

## WATCH OUT FOR

- Actual GIO Burn and Burn All are permanent removals. The new fixture creates a new private empty Trash namespace, does not accept user paths/URIs, and uses randomly generated disposable test files. It deliberately does not exercise production or a real machine.
- This is an **acceptance test**, not a new Burn permission model. All existing Burn All multi-mount semantics and GIO provider limitations remain unchanged.
- V2 Archive pilot snapshots are read-only independent copies; this fixture never asks V2 to Restore, Trash or Burn. Protected Archive V3 signer/cutover work is separately owned and remains deny-only.
- Hospital Room and original-record owners remain protected/fail-closed; Media's MPD queue cannot become a file delete.
- If GitHub CI proves a failure, repair only the demonstrated issue in one coherent follow-up on the same PR; no speculative security work. If CI passes, report repository acceptance readiness and use *one* native acceptance sheet for supported features, subject to explicit workstation approval.

## CHECKLIST

- [x] Inspect Syntagma rules, current main, ownership and open PRs
- [x] Preserve closed U9–U10c GIO Restore assignment
- [x] One private actual-GIO Burn and Burn All acceptance fixture
- [x] Same-fixture managed-copy recoverability/Burn and V2 read-only isolation
- [x] Add non-CI invocation safety tests and existing Trash workflow step
- [ ] Exact-head GitHub checks and raw receipts verified
- [ ] Independent Nurse 2 fixture scope/security review
- [ ] Operator authorizes any merge, native installation or workstation acceptance
- [ ] Native supported feature acceptance and demonstrated fixes only

## NEXT

Run the existing GitHub checks on one draft PR, investigate any failing receipt, then hand off for independent Nurse 2 review. The separate Protected Archive / Hospital Room owners should continue their assigned authority work without overlap.

## DECISIONS

A single bounded Package 1 test and acceptance handoff, not an open-ended deletion redesign. No source-owned data mutation, live Fedora files, privilege elevation on user host, protected signer, source-owner transfer, GIO Restore re-opening, production activation or merge in this task.
