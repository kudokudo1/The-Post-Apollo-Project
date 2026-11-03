# Social Organizations / Inline Record Actions & Archived Visibility v1

PATIENT // kudokudo1/The-Post-Apollo-Project
CONNECTION // External Hospital-compatible doctor, live Hospital Room/Role/Assignment unverified
SCOPE // Control 3 of approved single-page Organization Manager usability checklist
STATE // Draft repository change; not merged, deployed, or operator accepted

## IMPLEMENTATION

Preserve the existing Social → USER → SETTINGS → ORGANIZATIONS inline UI with one local editing organization and unified search. The underlying add/rename/save/archive/restore actions ALREADY exist for organizations, branches, portfolios, and Structure units; keep their original validated store methods and two-click CONFIRM ARCHIVE actions, avoiding duplicate new edit forms and screens.

Remove visual repetition by making the search/header component's SHOW ARCHIVED RECORDS / HIDE ARCHIVED RECORDS button work even when the search query is empty. One QML boolean in the existing local Search component now controls the archived visibility of Directory (organizations + branches), Portfolios, Structure units, and archived search-result labels. The three editors hide their standalone duplicate archived toggles only while embedded in this shared page, retaining those controls if used separately elsewhere. When archived visibility changes, pending archive confirmation is cleared in all three editors.

A short in-place RECORD ACTIONS line explains the existing workflow: add new record above, edit name and SAVE, ARCHIVE then CONFIRM ARCHIVE, or RESTORE a visible archived record. To restore an archived organization while focused on an active organization, select ALL / NO SELECTION in the existing local editing selector. No full-page navigation changes, no new edit surfaces, no private store edits.

## HOW TO USE

After operator-authorized merge and separate local source update: open Social → USER → SETTINGS → ORGANIZATIONS. Use the single SHOW ARCHIVED RECORDS button by Search, even with an empty search field, to reveal archived companies, branches, portfolios and units throughout the page. Use each row's existing SAVE / ARCHIVE → CONFIRM ARCHIVE / RESTORE controls. Select ALL / NO SELECTION to restore an archived company. HIDE ARCHIVED RECORDS restores default display.

## VERIFY

Static contract checks existing Add/Rename/Archive/Restore functions for all four record types and confirms shared toggle vs standalone compatibility. Real Qt6 offscreen test with disposable JS local store snapshots verifies archive visibility propagates to three independent editors, list selection of archived units, and clears pending archive confirmation. Existing directory, portfolio, structure, search, selector and relationship tests rerun; original backend files and store schemas are unchanged.

## WATCH OUT FOR

Archive/restore is not deletion, real tenant switching, a permission grant, or server audit. Archived references in saved relationship links remain separate stale-link management. Changing visibility does not modify any local data; archiving or restoring still invokes existing validated service methods. Existing source editor show-archived controls are hidden only under shared parent ownership, not removed.

## CHECKLIST

- [x] Verify #1137 merged, current GitHub main, Syntagma and no overlapping Social PR
- [x] Reuse CRUD; one page-wide archived visibility, no duplicate new buttons
- [x] Preserve standalone editor controls and original backend methods
- [x] Add static and genuine Qt6 verification
- [ ] Exact-head CI green
- [ ] Operator review/merge
- [ ] Live UI acceptance

## NEXT

Repair bounded CI issues; operator handles final merge and separately approved live Quickshell update. After operator acceptance, Control 4 is explicit Save/Conflict/Error feedback without new menus.

## DECISIONS

Unify presentation and confirmation-reset behavior only. No new persistence format, ownership inference, staff roles, account delegation, or local machine changes.
