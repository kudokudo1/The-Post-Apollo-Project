# CPU++ // local branch locations, unit locations and functional reporting v0

> **STATE:** Implemented on a GitHub review branch; automated verification and operator desktop acceptance are separate. Local Social relationship labels only, NOT employment verification, legal authority or company switching.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **CURRENT OWNER:** CPU++ manages presentation and focus; Social's original singleton stores own the data. The independent Identity Center and Connections broker own authenticated subjects, sessions, provider scopes and verified tenant permissions.
>
> **SOURCE:** The operator accepted the prior layout correction that puts filters in the middle CPU++ bay and requested its explicitly recorded NEXT: bring branch-location links, unit-location links, reporting relationships and structure management into the same practical three-bay UI. GitHub PR #1481 is merged; there is no overlapping open CPU++ owner PR at preflight.

## Implementation and physical effect

No new stores, Python write paths, password providers or floating windows are introduced. The existing CPU++ **1000×834** chassis remains: **390px left overview**, **260px middle filters/selector**, remainder right editor.

The middle-bay `CpuPlusLocalManagementNav.qml` retains its four primary category filters `IDS / PROFILES`, `ORGS / BRANCHES`, `STRUCTURE / UNITS`, `PORTFOLIOS`. Under **ORGS / BRANCHES**, a second compact row selects **EDIT ORGS** or **BRANCH LOCATIONS**. Under **STRUCTURE / UNITS**, it selects **EDIT UNITS**, **UNIT LOCATIONS**, or **REPORTING**. The middle-bay record list below continues selecting which local organization is in scope. These are *editor filters*, not company-session switches.

```text
CPU++ → ID MANAGEMENT
┌───────────────────┬─────────────────────┬─────────────────────────┐
│ LEFT // OVERVIEW  │ MIDDLE // FILTERS   │ RIGHT // SELECTED EDITOR│
│ existing counts   │ [IDS] [ORGS]        │                         │
│ local statuses    │ [UNITS] [PORTFOLIOS]│ ORGS + BRANCH LOCATIONS │
│ read-only host    │ ------------------- │   select branch/location│
│ preview           │ ORGS:               │   + LINK / CONFIRM UNLINK│
│                   │  [COMPANIES]        │                         │
│                   │  [BRANCH LOCATIONS] │ STRUCTURE + UNIT LOCATIONS
│                   │ STRUCTURE:          │   select unit/location  │
│                   │  [EDIT UNITS]       │   + LINK / CONFIRM UNLINK│
│                   │  [UNIT LOCATIONS]   │                         │
│                   │  [REPORTING]        │ STRUCTURE + REPORTING:  │
│                   │ ------------------- │   select parent/child   │
│                   │ SEARCH + SELECT ORG │   + LINK / CONFIRM UNLINK│
└───────────────────┴─────────────────────┴─────────────────────────┘
```

The right bay's `CpuPlusLocalManagementPane.qml` now instantiates, but does not rewrite:

- `IdentityCenterLocalBranchLocationsEditor.qml` with `SocialLocalBranchLocationLinksStore`. Branch-to-location add and two-click unlink.
- `IdentityCenterLocalUnitLocationsEditor.qml` with `SocialLocalUnitLocationLinksStore`. Division/department/team-to-location add and two-click unlink.
- `IdentityCenterLocalFunctionalReportingEditor.qml` with `SocialLocalFunctionalReportingStore`. Directed local reporting parent/child relationships and two-click unlink; the original editor blocks duplicate links and graph cycles.
- The existing `IdentityCenterLocalStructureEditor` remains available under **EDIT UNITS** to create missing divisions, departments, teams and `location` units; the Organization Editor under **COMPANIES / BRANCHES** creates branches. Existing archive/delete controller appears on primary record editors; relationship editors use their original guarded unlink actions.

All three relationship editors receive the **same selected local organization ID** from the middle bay and `useSharedContext:true`, so their source/target selections are scoped to that organization. Changing the section, secondary editor task or selected organization cancels pending unlink confirmations (including Archive Tray) to avoid carrying a destructive confirmation into a new context. Filters remain visually and technically in the **middle** bay.

## How to use after operator-authorized merge and deployment

In **CPU++ → ID MANAGEMENT**, select **ORGS / BRANCHES** in the middle filter bar, then **BRANCH LOCATIONS**. Pick a local company below the filters. The right bay lists its existing branches and location units; select each and choose **+ LINK BRANCH TO LOCATION**. Existing links have an **UNLINK** confirmation action. To add a branch, use **COMPANIES / BRANCHES**; to create a location, use **STRUCTURE / UNITS → EDIT UNITS** first.

For operating locations, use **STRUCTURE / UNITS → UNIT LOCATIONS**, select the same company and the functional unit/location, then **+ LINK TO LOCATION**. For reporting links, choose **STRUCTURE / UNITS → REPORTING**, select parent and child units, then **+ LINK FUNCTIONS**. Cycles, self-links, duplicate or cross-company relationships remain guarded by Social's original stores and policies.

Archive/restore and red permanent deletion of companies and units remain in the primary editors, not conflated with relationship unlink. There is no login prompt or provider credential field.

## Verification and boundaries

The CPU++ workflow runs the new source contract `tests/cpuplus/test_cpuplus_social_relationship_editors.py`, the existing three-bay contracts, and the canonical synthetic backend suites `test_social_local_branch_locations_v1.py`, `test_social_local_unit_locations_v1.py`, `test_social_local_functional_reporting_v1.py`. Those existing backend tests use synthetic LLC/nonprofit data and independently check writer guards and persistence. Static QML tests do **not** prove the running Quickshell renders or the operator's local records behave correctly; that requires desktop acceptance after separately authorized merge/deploy.

These relationships are **manual planning labels**, not verified addresses, employee management, real company membership, OAuth connections, backend permission grants, or Identity Center tenant switching. A Social layout ID and Account Center linked name remain distinct from signed principals and provider accounts.

## Hospital-compatible handoff

### IMPLEMENTATION
Working middle-bay contextual filters and actual original Social branch-location, unit-location and reporting relationship editors in the right bay. No modifications to privileged Identity Center, connections/authentication paths or Social writers.

### HOW TO USE
CPU++ → ID MANAGEMENT → middle ORGS or STRUCTURE → secondary location/reporting filter → middle select company → right link/unlink. Existing structure/company creation remains under EDIT UNITS / COMPANIES.

### VERIFY
Check all exact-HEAD CI runs, then visually validate the real CPU++ 260px selector and original link/unlink controls on an authorized desktop deployment. Keep test evidence under VERIFY, never NEXT.

### WATCH OUT FOR
No production tenant/session authority. Existing store guards are unchanged. Hidden editor state is reset on navigation; lack of one of the required source records disables adding links. Native Qt rendering not yet verified.

### CHECKLIST
- [x] Read main, Syntagma AGENTS / Hospital and source ownership
- [x] Keep primary categories and their secondary controls in middle bay
- [x] Reuse existing Social relationship editors, stores and unlink validation
- [x] Guard confirmation state on section/company changes
- [x] Preserve the fixed chassis and original ID editor
- [x] Add relationship-specific source and backend CI regressions
- [ ] Exact-head CI completion
- [ ] Operator native layout/action acceptance
- [ ] Remaining Social relation/modifier and account connection work

### NEXT
Implement the **Social Relationship Modifier** controls in CPU++'s right editor with middle-bay selection, including local Social ID / saved account-name linking to company or branch, while preserving the existing verified Identity Center context boundary. Reuse `IdentityCenterLocalRelationshipModifiers.qml` and `SocialOrganizationLinksStore`; do not invent real provider OAuth or grant authority. This is the next concrete development task, not a request to repeat tests.

### DECISIONS
No new top-level mode or window, no local desktop writes, no Social writer forks, no automatic switch/account login, and no PR merge or production activation without approval. The operator retains final acceptance authority.

**HOSPITAL:** External ChatGPT contributor; no verified live Room, Staff Role, Assignment or Session lease. Recovery pointer: this document, current GitHub PR head, and the three QML files `CpuPlusW.qml`, `CpuPlusLocalManagementNav.qml`, `CpuPlusLocalManagementPane.qml`. Recheck current ownership before continuation.
