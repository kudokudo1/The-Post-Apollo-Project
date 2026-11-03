# Social / Local Branch to Structure-Location Associations v1

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible; no verified live Room, Assignment or Staff Role.  
**CONTEXT:** Operator confirmed merged function-to-location editor works in running Quickshell. Three-organization portfolio and original local managers accepted.  
**STATE:** Repository implementation for review; no merge or local deployment.

## IMPLEMENTATION

Inside Social → USER → SETTINGS → ORGANIZATIONS, add **BRANCH LINKS // LOCATIONS** below the Structure and function/location editors. An operator chooses one existing active local organization, one active branch **from that organization**, and one active Structure location **in that same organization**, then presses **+ LINK BRANCH TO LOCATION**. Branches may reference multiple locations, and locations may serve multiple branches. **SHOW ALL LINKS** exposes saved associations, including archived/missing references. **UNLINK BRANCH LOCATION → CONFIRM UNLINK** removes an association only.

Branches and Structure locations remain independent records. A branch can represent an operating branch, program, or organizational label. A Structure location is a geographic label, not verified real estate or a physical address. There is no automatic migration, merge, deletion, rename, mapping by name, or implied hierarchy.

The separate private XDG JSON store **local-branch-location-links-v1.json** contains only stable IDs: id, orgId, branchId, locationId, plus revision and nextId. No company names, addresses, employees, roles, credentials, provider identifiers, real ownership records or grants are copied. SocialLocalBranchLocationLinks.py validates an active parent organization, an active branch under that parent, and an active Structure location under the **same parent**. The five existing directory/portfolio/structure/function-location/Social-link stores remain strictly read-only inputs.

Storage uses owner-only 0700 data directory and 0600 file, a fixed read/update CLI with JSON stdin, strict schema and bounded input, optimistic revision checking with lock, atomic replacement/fsync, and fail-closed corrupt/newer/unsafe file checks. The QML singleton owns the process bridge. Archived or missing references remain displayable as **STALE OR UNAVAILABLE** and removable, not treated as verified access. The Identity Center switcher remains disabled.

## HOW TO USE

After review/merge and separately approved local source sync: **USER → SETTINGS → ORGANIZATIONS**. Create a branch in MY ORGANIZATIONS and a location in MY STRUCTURE. Under BRANCH LINKS select organization → branch → location → **+ LINK BRANCH TO LOCATION**. To remove a link, SHOW ALL LINKS then UNLINK BRANCH LOCATION → CONFIRM UNLINK.

## VERIFY

Synthetic tests cover three fictional organizations, branches, Structure locations, many-to-many sharing, cross-company refusal, wrong-kind rejection, archived data, stale unlink, exact revision conflicts, corrupt/symlink/unsafe file refusal, private modes, fixed CLI and **byte-for-byte preservation of all five original stores**. The new CI workflow reruns original organization, portfolio, structure, function-location, Social-link and Settings tests plus actual Qt6 offscreen QML loading. Native Quickshell and live mouse-click verification are separate.

## WATCH OUT FOR

Manual planning pointers are not legal ownership, real addresses, employee memberships, tenant scopes or permission grants. Multi-file reference validation can race with archiving, so these local records must never authorize an operation. Owner-only storage is not encryption or same-UID adversary isolation. Existing branch records are never silently transformed into locations.

## CHECKLIST

- [x] Inspect current main, Syntagma rules, source and PR collisions
- [x] Private local branch-location link storage and QML singleton
- [x] Existing Settings screen editor and two-click unlink
- [x] Synthetic tests, regression tests and Qt6 workflow
- [ ] Exact-head CI green
- [ ] Genuine native Quickshell persistence verified
- [ ] Operator review, merge and live acceptance

## NEXT

Run CI and repair bounded failures. Add a separate disposable genuine Quickshell save/restart test. Operator controls merge and local installation. Reporting-line hierarchy and verified enterprise workforce permissions are different assignments.

## DECISIONS

Only explicit branch ↔ location links inside one local organization. No live desktop writes, Quickshell reload, company switching, cross-company association or permission expansion.
