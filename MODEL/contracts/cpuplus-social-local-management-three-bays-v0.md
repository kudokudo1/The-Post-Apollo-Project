# CPU++ // real Social local company, branch, unit and portfolio management in three bays v0

> **STATUS:** GitHub review branch, operator acceptance and Qt/Wayland appearance verification pending. Real local edit actions only; NOT verified employer membership, OAuth connections, global sign-in or company permissions.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator accepted the earlier CPU++ local-ID / organization-association flows and requested the rest of Social management and PostWallet connections inside a fast interface. Logind security PR #1474 was confirmed merged and all eight checks passed before this work. The currently accepted CPU++ 1000×834 chassis and its three bays must remain unchanged.
>
> **OWNERS:** Existing Social stores own all local writes. Existing CPU++ owns layout and selection. Trusted Identity Center host and provider Connections broker independently own real authenticated persons, memberships, sessions and provider authorizations.

## Implemented interface

```text
CPU++ MAIN RAIL (unchanged)           ID MANAGEMENT
┌───────────────────┬───────────────────┬────────────────────┐
│ LEFT // OVERVIEW  │ MIDDLE // FILTERS │ RIGHT // DETAILS   │
│ 390 px            │ 260 px            │ remaining width    │
│                   │                   │                    │
│ Saved ID count    │ [IDS] [ORGS]      │ Rename ID          │
│ Active layout     │ [UNITS] [PORTFOLIO]│ Contact/accounts   │
│ Company count     │ ------------------│ Org/branch editor  │
│ Linked IDs        │ Select local ID / │ Structure editor   │
│ Host context      │ org / portfolio   │ Portfolio editor   │
│ status (read-only)│ Search and records│ Save/Add/Red X     │
│                   │                   │ Archive / Restore  │
└───────────────────┴───────────────────┴────────────────────┘
```

The main mode remains `ID MANAGEMENT` to preserve existing operator workflow and tests. `CpuPlusLocalManagementNav.qml` adds a compact four-tab local task selector **at the top of the existing middle selector bay**; tab IDs are `IDS`, `ORGANIZATIONS`, `STRUCTURE`, `PORTFOLIOS`. No new window, chassis rescaling or sibling rail slot.

`CpuPlusLocalManagementPane.qml` has one instance per existing `overview/selector/details` bay. The left shows active counts and a plain local-only warning; the middle filters actual saved company or portfolio records and controls **editing focus**, not provider or tenant switching. The right instantiates the original Social edit components from `widgets/messanger` with the **original Social singleton stores** and guarded `IdentityCenterLocalArchiveTray` dependency-aware red deletion.

For `IDS`, the original `CpuPlusIdManagementPane` and `CpuPlusIdDetailsEditor` are unchanged: local ID create/remove, rename/contact, saved account names, local association editor and host-context viewer stay in their original bays. The middle selector list starts below the category filters; the left overview returns to full height. The accepted color grammar and existing keyboard/text focus guards remain.

For `PORTFOLIOS`, the original Social `IdentityCenterLocalPortfolioEditor` gained an optional `focusedPortfolioId: ""` property. **Default empty** preserves the existing Social all-portfolios editor exactly. CPU++ sets the selected record ID so the right bay shows only one portfolio and keeps the form digestible. Local organization and structure editors already supported equivalent selected record focus, so they needed no new writer logic.

## Security and data ownership

- Local `SocialOrganizationDirectoryStore` owns company/nonprofit names and branches. `SocialLocalOrganizationStructureStore` owns units; `SocialLocalPortfoliosStore` owns portfolios. `SocialOrganizationLinksStore` remains the owner for local saved Social-ID associations. No clone files, provider credentials or new LocalStorage.
- Full guarded deletion of local organization/branch/portfolio/unit records reuses the seven-store `IdentityCenterLocalArchiveTray.requestRemove` and backend revision/dependency checks. Red X requires current revision and confirmation; deletion does NOT require backup or archive first. Archive/restore remains available.
- Selecting a local organization only selects a QML editor record. It does not set the verified Identity Center tenant, change provider accounts, log in, grant roles or activate an organization permission. Text labels explicitly state this.
- Existing separate Identity Center host status/connection review is unchanged. Real `CONNECT ACCOUNT`, `CONNECT ALL`, verified `SWITCH ORGANIZATION`, permission writes, device/passkey/MFA and PostWallet profile-source ingestion require their own security/owner contract.
- Source inspection during the previous milestone did not locate a separate PostWallet repository. This milestone does not claim to have imported unseen PostWallet code. The roadmap `social-postwallet-management-connectivity-roadmap-v0.md` tracks that dependency.

## How to use after operator-authorized merge and desktop deployment

Open **CPU++ → ID MANAGEMENT**. In the **middle bay's filter strip** select **ORGS / BRANCHES**, **STRUCTURE / UNITS**, **PORTFOLIOS** or **IDS / PROFILES**. For organizations/structure/portfolios, choose the local record in the middle or create one in right, then use the existing right-bay Save/Add/Archive/X buttons. The **Archive Tray** is at the end of the right editor and restores previously archived records. Red X is permanent and requires confirmation and intact dependency preconditions.

No provider login or real organization-switch button is implied. If a store shows Loading/Error, edits stay unavailable until refreshed and validated.

## Verification

Source contract tests `tests/cpuplus/test_cpuplus_social_local_management_bays.py` assert exact 1000×834 chassis, left 390/middle 260, unchanged ID controls, four working navigation tabs **only in the middle bay** above both middle record selectors, full-height left overview, real store bindings, right original Social editor reuse, archive delete controller and identity-host separation. The CPU++ CI workflow also reruns the current canonical Social organization, structure, portfolio, seven-store archive/remove suites. This is static code and backend verification; it does **not** prove native Qt runtime appearance or any live identity/provider session.

## Hospital checkpoint

### IMPLEMENTATION
Compact four-section ID Management filter strip in the middle bay, searchable record selector directly below, full-height left overview, contextual existing Social editors in right bay, shared original archive/delete controller, optional portfolio focus, new tests and CI. Existing ID functions and host read-only panel preserved.

### HOW TO USE
CPU++ → ID MANAGEMENT → middle category filter → middle saved record → right existing Save/Add/Archive/Delete. No tenant or account switching is performed.

### VERIFY
Require exact GitHub PR-head checks and native desktop rendering/data persistence test before operator acceptance. Confirm selecting one organization does not change the active Social ID or the verified Identity Center organization, and that red permanent deletion refuses records with dependencies.

### WATCH OUT FOR
This deliberately completes **local** organization editing in CPU++ before production login. The full Social section includes other specialties (location links, reporting, modifiers) not yet ported to this compact view; no invented authority, PostWallet profile import or Connect All feature is claimed.

### CHECKLIST
- [x] Inspect main, Hospital protocols and existing Social owners
- [x] Preserve CPU++ chassis, main rail, existing ID behavior
- [x] Add working local navigation and three-bay selection/editor focus
- [x] Reuse original organization/structure/portfolio editors and seven-store destructive guard
- [x] Add backward-compatible portfolio focus
- [x] Add regression tests/CI
- [ ] Exact GitHub workflow green
- [ ] Operator desktop acceptance
- [ ] Subsequent local specialty management and verified provider/tenant controls

### NEXT
After operator accepts this local-management UI, extend compact contextual tabs for branch/geographic links, reporting relationships and account-profile records using existing Social owners. In the separate security stream, verify Sway lock source, protected host supervision, real IdP credentials and server-validated org switch. Connect All must orchestrate independent provider-specific consent, not quietly reuse a master password.

### DECISIONS
No new top-level app window, no duplicate Social state, no local machine writes, no production login, no implicit tenant switching, no new role grant authority and no merge without operator approval. Same accepted magenta add/input, orange cursor and red destructive buttons remain.

**HOSPITAL:** External ChatGPT worker; no live Room/Assignment/Staff Role/Session lease is verified. Source of truth is current GitHub PR and this contract. Final acceptance belongs to operator.


## Operator layout correction // November 8, 2026

The operator reviewed the running CPU++ menu and requested that the four section filters move from the left **overview** bay to the middle **target/selector** bay, because the filters determine which records the middle bay shows. The corrected layout keeps the left overview independent and full height. The same selected section drives the middle list and right editor. This is a placement fix only: no Social writers, credential authorization, account switch behavior, CPU++ chassis geometry, or accepted ID CRUD logic changes. Confirm placement on a real Quickshell desktop after review; static tests do not prove rendering.
