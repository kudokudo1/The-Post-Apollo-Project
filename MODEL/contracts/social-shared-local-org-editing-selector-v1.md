# Social Organizations / Shared Local Editing Selector v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT; external Hospital-compatible, no verified live Room or Staff Role
ASSIGNMENT: First usability control from the accepted single-page Organization Manager checklist.
STATE: Draft repository change; no local deployment, merge, or operator UI acceptance.

## IMPLEMENTATION

Add one LOCAL ORGANIZATION TO EDIT selector at the top of the existing Social → USER → SETTINGS → ORGANIZATIONS page. Choices are active organizations from the accepted local Directory store plus ALL / NO SELECTION. No company is preselected for writing; the operator explicitly selects it. An archived/missing ID resolves to no active editing target.

The selector controls the existing MY ORGANIZATIONS editor (focus one row, or show all), MY STRUCTURE (reuse its shared-context mode and hide redundant company buttons), and ORGANIZATION LINKS // APPLY MODIFIER (hide the repeated company buttons and bind its selection to the same context). Changing company clears pending archive/unlink confirmation and modifier source/target/account fields.

MY PORTFOLIOS retains its full cross-organization view because its purpose is to manage several organizations in one group. There are no new tabs, workspaces, nested menus, private store changes, migrations, or additional authorized operations.

The local editing focus is independent from the permanently disabled trusted SWITCH ORGANIZATION // UNAVAILABLE action. An identity-N or org-N local identifier never establishes authenticated membership or rights.

## HOW TO USE

After operator-controlled merge and separately authorized local source update: Social → USER → SETTINGS → ORGANIZATIONS. Choose one active company under LOCAL ORGANIZATION TO EDIT, then edit that company's Directory row, Structure, and modifiers on the same page. Select ALL / NO SELECTION to browse every Directory record; structure and modifier saves require a chosen active company. Portfolios remain cross-company.

## VERIFY

New source contracts confirm one selector, the original inline page, shared selection passing into both scoped editors, archived/unknown ID refusal, and no privileged switching. CI reruns current organization, portfolio, structure, modifier and Social regression tests. A new real Qt offscreen test injects three fictional company records and checks that Structure and Modifiers follow the same selected company and reject archived/unknown IDs. No live system is accessed.

## WATCH OUT FOR

Archived companies cannot be selected for new writes. Use ALL, then original Directory SHOW ARCHIVED / RESTORE to restore an archived organization. Cross-organization portfolio lists are intentionally not filtered. Local editing focus is not persistent and not a server identity context. Live Wayland mouse acceptance remains pending.

## CHECKLIST

- [x] Inspect current main, Syntagma authority, exact QML and open PRs
- [x] Bind Structure and Modifier editors to one top local selector
- [x] Preserve all Directory and Portfolio operations and private storage
- [x] Add source and real Qt tests
- [ ] Exact-head CI passes
- [ ] Operator reviews and merges
- [ ] Live UI acceptance

## NEXT

Check exact-head CI and repair bounded QML/test issues. The next separate control after acceptance is unified search/filter. No workstation change, self-merge or permission expansion.

## DECISIONS

Default to no selected company rather than first company to avoid editing the wrong LLC/nonprofit. Keep existing single page and private service boundaries. The local selector never switches authenticated tenant access.
