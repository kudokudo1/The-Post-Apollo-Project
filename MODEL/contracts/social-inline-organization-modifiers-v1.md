# Social Organizations / Inline Modifier Editor v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT; external Hospital-compatible, no verified live Room or Assignment.
TRIGGER: Operator rejected Navigation v2 due to excessive menus and requested one inline editor with modifiers applicable to each level.
STATE: Scoped GitHub correction, pending exact-head CI, merge and live acceptance.

## IMPLEMENTATION

Correct the UX regression from PR #1121: remove four nested workspaces. Restore original direct MY ORGANIZATIONS → MY PORTFOLIOS → MY STRUCTURE editors in the one scrolling Organizations page. Replace the repeated link editors below them with one inline ORGANIZATION LINKS // APPLY MODIFIER form.

Choose local organization once. Choose source level (organization, branch, division, department, team); filter levels by name if needed. Choose an allowed modifier: LOCATED AT (branch/function → Structure location), REPORTS TO (function → parent function, acyclic), or SOCIAL LABEL (organization/branch → local Social identity, optionally an account nickname). Select target and press APPLY MODIFIER. One list shows all saved associations and supports SHOW ALL ORGS, stale reference indication, REFRESH LINKS and UNLINK MODIFIER → CONFIRM UNLINK.

The form dispatches to four accepted original writers without touching their schemas: local unit/location, branch/location, functional reporting and Social association stores. All existing Python backends remain authoritative for same-organization IDs, duplicate pairs, reporting cycles, and revision conflicts. The three modifiers cover four stores because LOCATED AT selects its existing writer based on whether the source is a branch or functional unit.

Unused Navigation v2 workspace, tests and workflow are deleted from active sources. Its historic contract is retained but marked superseded. No storage migration or record rewriting.

## HOW TO USE

After operator-approved merge and separately approved local sync: Social → USER → SETTINGS → ORGANIZATIONS. Edit company, portfolio and structure directly as before. At the bottom choose company → source → modifier → target → APPLY MODIFIER. For Social labels choose an identity or optionally an account nickname. Use SHOW ALL ORGS and confirmed unlink for cleanup. No nested workspace navigation.

## VERIFY

New inline modifier contract covers composition, support matrix, all four add and unlink handlers, duplicate/cycle guards, stale link cleanup and authorization boundaries. Existing organization, portfolio, structure, location, reporting, Social-link and Identity Center Settings test suites rerun. Qt6 offscreen QML test instantiates the real one-page form. Source and persistence backends are unchanged. Live Quickshell mouse acceptance remains operator-controlled.

## WATCH OUT FOR

All relationships remain manual local planning labels, never verified company access, employment hierarchy, permissions, legal ownership or provider sign-in. A source/modifier pairing the existing backend does not support stays disabled, rather than silently creating new relationship types. No live shell restart or workstation changes.

## CHECKLIST

- [x] Review latest main, shared ownership and current QML
- [x] Restore simple inline Organizations page
- [x] One modifier form for source levels and original private stores
- [x] Update source-level and offscreen Qt tests
- [ ] Exact-head CI green
- [ ] Operator PR merge and live UI acceptance

## NEXT

Fix bounded CI failures, compare PR against current main and hand off to operator. Real authorization and new organization semantics are separately scoped assignments.

## DECISIONS

Operator correction supersedes Navigation v2 menu splitting. No new menus, backend changes, permission activation, auto-migration, self-merge or desktop writes.
