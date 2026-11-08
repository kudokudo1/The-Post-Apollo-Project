# CPU++ // organization Social link modifiers and saved account-name associations v0

> **STATE:** GitHub review branch, code and CI; not merged, installed or operator accepted.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
> **SOURCE:** Operator approved the NEXT task following merged #1490: bring Social Relationship Modifiers and account-name associations into CPU++ while keeping local links separate from authenticated provider connections.

## IMPLEMENTATION

The fixed 1000×834 CPU++ chassis remains unchanged: left 390px overview, middle 260px filters and saved record selection, right existing Social editors. Under middle **ORGS / BRANCHES**, add **LINK MODIFIERS** alongside EDIT ORGS and BRANCH LOCATIONS. This is a real filter, wired to the CPU++ task allowlist, not a static placeholder.

Under that task, the right detail bay mounts exactly one `IdentityCenterLocalRelationshipModifiers` instance with `useSharedContext:true`, receives the same selected organization ID as other Social editors, and uses the original singleton references:

- `SocialOrganizationDirectoryStore` and `SocialLocalOrganizationStructureStore` for company, branch and unit names;
- `SocialLocalUnitLocationLinksStore`, `SocialLocalBranchLocationLinksStore`, `SocialLocalFunctionalReportingStore` for local LOCATED AT / REPORTS TO;
- `SocialOrganizationLinksStore` for local organization/branch → Social ID and optional account-label relationships;
- `SocialIdentityStore.snapshot` for saved local Social ID labels and `SocialAccountDetailsStore` for their saved per-service account names.

The original Social modifier form chooses an organization, existing branch or functional unit, then permitted LOCATED AT, REPORTS TO or SOCIAL LABEL modifier, then a target. SOCIAL LABEL supports the existing local ID alone or a saved account nickname. The form's existing `applyModifier()`, `alreadyLinked()`, `wouldCycle()`, `unlink()` and two-click **CONFIRM UNLINK** remain unchanged. On section, task or selected company changes, CPU++ clears any armed removal confirmation. Original Social settings keep using the original form with no new writer.

A previously existing duplicate `directoryStore:` line inside CPU++'s `IdentityCenterLocalArchiveTray` property bindings is removed. The tray now has exactly one directoryStore assignment, avoiding a potential QML parse failure and preserving the original seven-store guarded archive/delete behavior.

## HOW TO USE (after approved merge and deployment)

CPU++ → ID MANAGEMENT → middle **ORGS / BRANCHES → LINK MODIFIERS** → select local organization in the middle list. In the right editor select source (company/branch/unit), modifier and target, optionally choose a saved service and account nickname, then choose **APPLY MODIFIER**. A saved link can be removed with the existing **UNLINK MODIFIER → CONFIRM UNLINK** control. Creating a new company, branch, unit or account nickname remains in its existing editor. A saved account name is a label, not proof of an external login.

## VERIFY

`tests/cpuplus/test_cpuplus_social_link_modifiers.py` guards filter placement in the middle bay, actual right-editor instantiation, original singleton injection, QML archive property syntax, edit-state validation, selection reset, unchanged chassis and absence of privilege/credential operations.

The CPU++ workflow also reruns `tests/messaging/test_identity_center_inline_modifiers_v1.py`, `test_social_org_links_v1.py`, `test_social_account_details.py` and existing location/reporting/ID control tests. Those test synthetic local data and source semantics. They do not establish real Wayland rendering or provider login.

## WATCH OUT FOR

No real provider OAuth, universal Connect All, credential storage, real person identity, server-authorized company switch, legal company ownership or role assignment. Local `identity-N` labels and service account nicknames do not grant external access. The existing Identity Center host read-only verified context remains a separate security boundary. No new QML login buttons or local machine changes.

## CHECKLIST

- [x] Verify #1490 merged, Syntagma/Hospital protocols, main and open ownership
- [x] Add real middle-bay LINK MODIFIERS filter for existing Social relationship form
- [x] Bind selected local company, identities snapshot and saved account-name store
- [x] Preserve original Social writer and two-click UNLINK
- [x] Reset destructive confirmation when changing editor context
- [x] Repair duplicate QML directoryStore property in existing archive tray
- [x] Add CI source and original Social backend tests
- [ ] Exact-head CI green
- [ ] Operator review, merge and runtime appearance acceptance

## NEXT

**Add a dedicated CPU++ Connected Accounts management section with real connection status and provider action contracts**. Reuse the existing `CpuPlusSettingsConnectionsOverviewPane`, `CpuPlusSettingsConnectionsListPane`, `CpuPlusSettingsConnectionsDetailsPane`, and broker; identify supported provider OAuth handshakes and safe sign-in/reconnect/disconnect operations behind host and permission checks. Keep CONNECT ALL as a provider-by-provider consent queue, not a shortcut around a provider's authentication. This is an implementation milestone, not a request to repeat tests.

## DECISIONS

No duplicate Social stores, new window, chassis change, role/permission writers, automatic external login, local desktop mutation, PR merge or production activation. Operator is final authority.

**Hospital-compatible external checkpoint:** PATIENT The-Post-Apollo-Project; ROOM/ASSIGNMENT bounded CPU++ local Social modifier integration (not verified live registered); WORKER OPEN AI // CHATGPT; STAFF ROLE unassigned; PERMISSIONS GitHub review PR only. Recovery: this document, `widgets/cpuplus/CpuPlusLocalManagementNav.qml`, `widgets/cpuplus/CpuPlusLocalManagementPane.qml`, `widgets/CpuPlusW.qml`, `tests/cpuplus/test_cpuplus_social_link_modifiers.py`. Recheck main and owners before further modifications.
