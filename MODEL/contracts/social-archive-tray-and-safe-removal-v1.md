# Social Organizations / Archive Tray & Safe Archived Removal v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT, external Hospital-compatible, no registered Room/Staff Role/Assignment verified.
SCOPE: Operator-requested correction after 2026-11-04 live screenshots. Preserve one-page Social Organizations layout.
STATE: Draft source change; exact-head CI and operator live acceptance must be reported separately.

## IMPLEMENTATION

The existing SHOW ARCHIVED RECORDS button is embedded in Search and merely reveals archived items interleaved with active rows, making them difficult to find. Introduce one conspicuous **ARCHIVE TRAY // N ARCHIVED RECORDS** summary **above Search** on Social → USER → SETTINGS → ORGANIZATIONS. Its VIEW ARCHIVES // N control expands an **inline archived-only list** of companies, branches, portfolios and structure units with clear type and name. Existing Show Archived Records, archive, restore and editing context remain intact in their original forms. No additional window or workspace.

Each archived row offers a green RESTORE control using the original store's existing validated writer, and a distinct **red REMOVE PERMANENTLY / CONFIRM REMOVE** control using the original button width/height conventions. Removal always requires **two separate clicks on the exact same archived record**, and a completed backend response before the UI reports removed. Toggling the tray clears pending confirmation.

New \`services/social/SocialLocalOrgArchivedRemoval.py\` CLI is a tightly limited one-record deletion path. It acquires **all seven original writer locks non-blockingly**, reloads their validated private JSON records, checks exact record ID, name, owning organization, archived flag and expected source revision, requires an already **validated private backup snapshot that contains the exact archived record**, and refuses deletion while there are any dependent child branches, structure units, portfolio memberships, location/reporting links or Social identity labels. A portfolio must have zero members before permanent removal. No automatic cascade, no deleting active records, no ID reuse and no arbitrary file path or system account access. On success **only the owning existing JSON document** is atomically rewritten through the existing secure \`save()\` method with its revision advanced; the UI refreshes the affected store.

Backend refusal includes precise codes and UI guidance like REMOVE_BRANCHES_FIRST, UNLINK_REPORTING_FIRST, DETACH_PORTFOLIOS_FIRST, REVISION_CONFLICT or BACKUP_REQUIRED. There is no failure path that silently deletes related records. This is a **local record removal**, not removal of a verified legal entity, its signed-in company account or network data.

## HOW TO USE

After operator-authorized merge and separately approved local source update: Social → USER → SETTINGS → ORGANIZATIONS. Near the top, ARCHIVE TRAY shows how many archived local records exist, even without a search query. Click VIEW ARCHIVES to inspect them. Use green RESTORE to reactivate. For actual removal, first ensure a recent BACK UP NOW snapshot was made *after archiving* the exact record, unlink/delete its dependent local records, then click the red REMOVE PERMANENTLY and the subsequent red CONFIRM REMOVE. Only then does the backend independently check backup, revision and references and, if safe, remove the one record.

## VERIFY

Python tests run exclusively under a disposable XDG_DATA_HOME and verify: archive-required, exact-snapshot-required, revision conflict and changed-record refusal, unit/branch/portfolio/company removal, parent/child/link refusal, writer-lock contention, no unreviewed cascade and nextId monotonicity. Source tests verify Archive Tray is above Search, the red confirmation path is separate from Restore, no new menus and existing original editors are preserved. Real Qt6 offscreen Settings test uses fictional stores and a stubbed Process to verify visible count/list, two-click red confirmation, unchanged stored records on backend refusal, and read-only refresh after synthetic backend success. No actual user data or live Wayland process is touched.

## WATCH OUT FOR

Permanent removal is an actual destructive operation and cannot be undone with the Restore button. Backup restore remains separately **locked**; a private backup preserves bytes but its automated multi-file recovery flow has not been enabled. Do not remove important business data without a validated recovery plan. The backend only removes records of the four supported local kinds; no broader tenant deletion or account offboarding. There is no global search or audit permission change.

## CHECKLIST

- [x] Inspect current Syntagma/Hospital authority and repository, user screenshots, existing Search/Archive interfaces and seven data schemas
- [x] One visible archive-only destination on the same page, near the top
- [x] Red two-click Remove Permanently and green Restore for archived entries
- [x] Backend refuses missing backup, active/linked/child records or stale revisions
- [x] Preserve exact original actions, current color language and unlocked Restore boundary
- [x] Add isolated backend, static UI and real Qt test coverage
- [ ] Exact-head CI green
- [ ] Operator-controlled PR review and merge
- [ ] Live visual acceptance, with destructive test **only on disposable records**

## NEXT

Correct any bounded CI failure, then hand off. Keep exact shades, global geometry, authenticated organization access and full backup Restore in their own scope.

## DECISIONS

No auto-cascade, no auto-purge on Archive, no unconfirmed destructive click, no local workstation modification, self-merge, production restart or new permission grant.
