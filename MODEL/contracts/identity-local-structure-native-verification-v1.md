# Identity Center / Organization Structure v1 genuine Quickshell persistence verification

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**CONNECTION:** External Hospital-compatible ChatGPT worker, not technically attached to a live Hospital Room, Assignment or Staff Role.  
**DEPENDENCY:** PR #1075 merged into main as a04d46c with 23/23 exact-head workflows passed.  
**CHANGE:** Tests and this verification note only; no production QML or service changes.

## IMPLEMENTATION

Add a separately gated, unmounted CI-only ShellRoot, LocalOrganizationStructureNativeSmokeV1.qml, and a Python native runner. It launches genuine pinned Quickshell 0.3.2 in Qt offscreen mode with a new private temporary HOME and XDG runtime/data/config/cache/state directory. No live Sway/Wayland socket, production user database, identity host, or authorized company membership is required.

Python seeds **three fictional organizations** (two LLCs and a nonprofit) and a synthetic local portfolio spanning all three, plus a fictional Social label link. It records the exact existing organization/portfolio/link file bytes. A first Quickshell process exercises the production SocialLocalOrganizationStructureStore QML singleton through eight saved operations: create division and department under the first company, location under the second, team under the third, rename division, archive/restore department, add another location under the first. Each step waits for a successful saved revision. A second **fresh Quickshell process** reloads the same structure data and verifies exact saved records. Python asserts 0700 directory and 0600 structure file, correct JSON schema/revision, no privileged fields, unchanged structure bytes across second-process read, and original organization/portfolio/Social-link bytes unchanged in *both* processes.

The test instantiates IdentityCenterSettingsSections and injects both the original local directory singleton and the new structure singleton. It proves genuine QS loading of the new settings editor, **not visual human interaction**.

## HOW TO USE

Review the draft PR CI. The test can be run only in an explicitly approved **disposable environment** with real qs:

    python3 tests/identity/native_local_organization_structure_smoke_v1.py

No desktop source sync, restart, system package installation, user files, or real organization labels are necessary for PR review.

## VERIFY

Expected markers: ORG_STRUCTURE_NATIVE_PASS_CREATE and ORG_STRUCTURE_NATIVE_PASS_RELOAD, strict private file modes, immutable original fixture data, and the same unit records after the second process. CI also re-runs existing structure/directory/portfolio tests and isolation guards. A green result is evidence of native Quickshell/Python persistence, but not of live compositor rendering or actual mouse clicks.

## WATCH OUT FOR

All input names are synthetic and all data is disposable. The local structures remain labels rather than verified tenant scopes, employee membership, geographic registration, legal ownership or permission grants. Local owner-only storage is not encryption. This test must never be mounted from shell.qml or run against the operator's HOME, Wayland session or production organization data.

## CHECKLIST

- [x] Confirm merged #1075 and 23/23 exact-head workflows
- [x] Inspect original organization/portfolio and native smoke test patterns
- [x] Add genuine native synthetic 3-organization structure save/restart smoke
- [x] Check source isolation, no live mount, private state and existing regressions
- [ ] Exact-head GitHub CI green
- [ ] Operator review and PR merge authorization
- [ ] Live Structure v1 click/save/reopen verification

## NEXT

Review CI and repair test harness issues if any. After an approved merge and local code update, verify a fictional unit in each real UI organization and persistence after reopening, without disrupting the user's live Quickshell.

## DECISIONS

A verification-only follow-up to Structure v1, not an authorization to add reporting-line graphs, employee permissions, hierarchical location trees or cross-organization sharing. No production source changes, local computer changes or PR merge performed by this worker.
