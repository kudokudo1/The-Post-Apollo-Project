# Social Organizations / Navigation v2 UI consolidation

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible, not verified registered in any live Room/Staff Role/Assignment.  
**SCOPE:** Existing Social USER → SETTINGS → ORGANIZATIONS UI-only, not a new backend or owner.  
**TRIGGER:** Operator requested combining nearly identical link panels shown in a live screenshot and accepted a four-workspace design.  
**STATE:** Isolated draft source PR for review and tests; not deployed to live Quickshell.

## IMPLEMENTATION

Replace the seven vertically stacked management panels with **one** \`IdentityCenterLocalOrganizationsWorkspace.qml\` presentation component:
- **OVERVIEW:** counts existing local organizations, portfolios, functional units, and link records; short direct navigation to other workspaces.
- **COMPANIES:** one of **ORGANIZATIONS & BRANCHES** or **PORTFOLIOS** at a time, reusing the accepted editors unchanged.
- **STRUCTURE:** one existing Structure editor (division/department/team/location CRUD).
- **RELATIONSHIPS:** one mode at a time among **REPORTING**, **FUNCTION / LOCATION**, **BRANCH / LOCATION**, and **SOCIAL ASSOCIATIONS**. All original add/remove/save/archive flows and stale-link handling are retained.

STRUCTURE and RELATIONSHIPS share a **single explicitly local organization editing context** and a lightweight organization-name filter. Each of the five scoped editors supports \`useSharedContext\`, which hides its original repeated organization selectors; selected child units/branches and pending unlink confirmations are cleared on context changes to avoid stale selections. Existing editor code executes the **same original commands and private data stores**. Companies/portfolios are still managed independently and no original records are rewritten or migrated by the navigation.

Only one workspace and one relationship mode are visible at a time. The read-only Identity Center snapshot and existing permanently disabled verified organization switch remain in Overview. The new context never authenticates, impersonates, changes a tenant, modifies login sessions or grants access.

The UI keeps original per-mode RELOAD/SAVE and error state where the existing stores own those operations. Consolidating backend stores or inventing cross-store global transactions is explicitly out of scope. This first iteration filters **organization names**; a full record-wide search/export/import or backup UI is a separate future milestone, not claimed here.

## HOW TO USE

After operator-approved merge and separately authorized local source update: Social → USER → SETTINGS → ORGANIZATIONS. Select OVERVIEW, COMPANIES, STRUCTURE or RELATIONSHIPS. For Structure or Relationships, choose the company from the shared LOCAL editing context; optionally filter company names. In RELATIONSHIPS choose the specific relationship type and use the original controls to add/remove records.

Rollback is repository-only: revert this navigation-only PR; the seven underlying private stores retain their original schemas and data.

## VERIFY

The new \`test_identity_center_local_navigation_v2.py\` contract checks that all seven original editors are reachable but only one workspace/mode is shown; five scoped editors use the shared local context, source is process/storage-free, verified switching remains disabled and the original service files are present. CI reruns seven existing local management/association regression suites and the Settings reader tests, then instantiates actual Settings QML in offscreen Qt6. Passing Qt loading does not prove native mouse interaction in the user's running Wayland/Quickshell session.

## WATCH OUT FOR

Existing social local identity IDs and organization IDs are unverified local labels; the shared organization context is a **UI data filter only** and no server-side rights flow from it. Records for archived organizations remain available in their original editors, but the shared active-organization selector does not choose archived companies for new links. Restoring an archived organization is performed from COMPANIES. Source-file changes are confined to UI composition and tests; no cross-repo or local workstation changes.

## CHECKLIST

- [x] Inspect current GitHub source, active PRs, Syntagma/Hospital authority and existing UI tests
- [x] UI-only grouped workspaces and one-relationship-mode navigation
- [x] Shared company filter for five original editors, no store mutation/migration
- [x] Existing test contracts adjusted to composite component; new nav contract and offscreen Qt workflow
- [ ] Exact-head GitHub CI green
- [ ] Genuine Quickshell manual UI verification and user acceptance
- [ ] Operator-authorized merge/desktop activation

## NEXT

Repair test or Qt loading issues only within approved UI scope. Review GitHub diff against current main and avoid concurrent shared-seam collisions. Operator controls merge and live testing; do not proceed into real Identity Center auth/roles, database migrations, unified backend refactoring or local Quickshell reload.

## DECISIONS

Reorganize presentation, not storage: retain original editors and backend guards, add local shared selection, do not add new functions/permissions. One screenshot-driven UI fix is the current bounded assignment. No production merge or local machine change authorized.
