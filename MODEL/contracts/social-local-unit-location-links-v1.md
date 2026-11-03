# Social / Local Functional-Unit ↔ Location Links v1

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**PROVIDER:** OPEN AI // CHATGPT (external Hospital-compatible browser, no verified registered Room, Assignment or Staff Role)  
**CONTEXT:** Organization Structure v1 PR #1075 and the genuine Quickshell verification PR #1078 have both merged. Original exact-head workflow checks passed. Live operator click/save acceptance of Structure v1 remains unconfirmed.  
**STATE:** Bounded repository implementation for review. No tenant auth or desktop activation.

## IMPLEMENTATION

The existing **USER → SETTINGS → ORGANIZATIONS** screen gains **STRUCTURE LINKS // FUNCTIONS & LOCATIONS** immediately below MY STRUCTURE. Select one existing active local organization, one functional unit (division, department or team), and a location from that **same organization**, then **+ LINK TO LOCATION**. Multiple functional units may share a location; one functional unit may be linked to several locations. Saved links are presented with current names, and **SHOW ALL LINKS** reveals references across all organizations, including archived/missing records. **UNLINK LOCATION → CONFIRM UNLINK** removes one association, including stale links.

This is a deliberate **two-dimension relationship**, not a rigid parent tree. A company could have an Education division working in several places while another department is colocated at one of them. V1 does not decide that divisions always parent departments, that teams always parent locations, or that a worker's permissions follow these labels. Existing branches in the organization directory are still independent and are not silently migrated to locations.

A separate private, versioned **local-unit-location-links-v1.json** records only opaque IDs: id, orgId, functionId and locationId, plus revision and monotonic nextId. No labels, real address, coordinates, person, role, provider credentials or tenant status are copied. Backend **SocialLocalUnitLocationLinks.py** validates both referenced units and the active organization when creating a link: the function must be an active division/department/team; the location must be an active location in the *same* local organization. No cross-organization links. On archive or missing records, original links remain readable and removable but are marked stale/unavailable in the UI. Source documents for organizations, portfolios, structure and Social nickname associations are never mutated by linking.

Storage uses the existing Social private directory with 0700/0600 permissions, strict schema and request fields, size caps, stdin-only fixed commands, advisory file locking, optimistic revision checks, atomic replace and fsync, and fail-closed corrupt/newer/unsafe files. A QML singleton **SocialLocalUnitLocationLinksStore.qml** owns the process and exposes add/unlink. No new window, privileged Identity Center host calls, provider sign-in, grant enforcement or permission expansion.

## HOW TO USE

After code review/merge and separately authorized local source update:

1. Open USER → SETTINGS → ORGANIZATIONS → MY STRUCTURE. Create at least one division, department or team and one location in the **same** organization.
2. Scroll to STRUCTURE LINKS. Select the organization, functional unit, and location, then press **+ LINK TO LOCATION**.
3. Select another location to associate the same functional unit with multiple places, or another functional unit to reuse the location.
4. Use SHOW ALL LINKS to review, and UNLINK LOCATION → CONFIRM UNLINK to remove one manual association.

## VERIFY

Synthetic tests in tests/messaging/test_social_local_unit_locations_v1.py exercise three fictional organizations, all functional categories, many-to-many reuse, strict cross-company rejection, missing/archived target checks, stale-link removal, revision and duplicate rejection, private file modes, corrupt/newer/unsafe file refusal, fixed CLI and **byte-for-byte original store preservation**. New CI also runs existing organization, portfolio, structure, Social-link, settings and actual offscreen Qt parser/instantiation regressions. CI additionally runs a genuine pinned Quickshell 0.3.2 process twice against completely disposable XDG roots, creating and then reloading link records across three fictional organizations, while verifying byte-for-byte preservation of the source files and private modes. This is still not a live Sway desktop click test for the new editor.

## WATCH OUT FOR

These are **manual local planning links**, not tenant memberships, verified physical offices, employee assignments, enterprise hierarchy, or scopes usable by an authorization service. A parent organization or unit can be archived after local validation but before persistence because the source files are not one transaction. Consequently no operation may rely on this store for access control. The local file is owner-only, not encrypted. Existing real desktop user data must never be mutated by PR tests.

## CHECKLIST

- [x] Confirm Structure v1 and native persistence verification merged
- [x] Inspect Syntagma authority, active PR ownership and exact current Social source
- [x] Independent private local unit-location association model
- [x] Same-screen UI with many-to-many choices, stale status and confirmation unlink
- [x] Synthetic tests, original regressions and Qt offscreen workflow
- [ ] Exact-head Python, Qt and genuine native Quickshell CI green
- [ ] Independent review and operator merge
- [ ] Operator live UI acceptance

## NEXT

Check workflow results and fix bounded issues. A separate, approved milestone may add explicit functional reporting relationships, branch/location mapping or verified workforce scopes. None is inferred by these manual pointers.

## DECISIONS

Continue Organization Structure v1 with the **smallest useful relationship**: functional unit ↔ geographic location within a single organization. Avoid a forced enterprise org chart, cross-company link, credentials, role permission propagation or local workstation changes. Operator controls merge and final acceptance.
