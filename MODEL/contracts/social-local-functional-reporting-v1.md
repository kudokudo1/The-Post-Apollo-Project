# Social / Local Functional Reporting Relationships v1

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**PROVIDER:** OPEN AI // CHATGPT; external Hospital-compatible browser, no verified live Room, Staff Role, Session or Assignment.  
**CONTEXT:** Operator accepted local Organization Manager, three-organization portfolios, Structure v1 and function-to-location relationships. Branch-to-location PRs #1088 and #1090 are merged and CI-verified; live desktop acceptance of branch linking is still unconfirmed.  
**STATE:** Bounded GitHub implementation for operator review. No local machine changes, merge, permission implementation or production activation.

## IMPLEMENTATION

The existing Social **USER → SETTINGS → ORGANIZATIONS** screen gains **FUNCTIONAL REPORTING // LOCAL MAP** after BRANCH LINKS. This is an **explicit directed acyclic graph** of manually defined parent → child relationships between already-created local divisions, departments and teams belonging to the **same organization**. It allows multiple parents (coordination/reporting labels) without forcing a universal division → department → team sequence. Units may be of the same kind. A location is excluded because geographic planning is already a separate accepted dimension.

The UI selects an active local organization, active functional parent and active functional child, then **+ LINK FUNCTIONS**. Local UI checks self-links, duplicates and cycles; Python is the authority for all input validation. A saved link is shown with current names and **LOCAL REPORTING LABEL // NOT AN ACCESS GRANT**. Missing or archived company/unit references are still displayed as **STALE OR UNAVAILABLE** with SHOW ALL LINKS and a two-step **UNLINK FUNCTIONS → CONFIRM UNLINK**. Archiving an original unit or company never silently deletes a reporting link.

The independent XDG local store **local-functional-reporting-v1.json** holds **only** opaque IDs (link id, orgId, parentId, childId) and revision/nextId. No human roles, employee IDs, manager assignments, legal ownership, provider accounts, permission grants or credentials. Backend SocialLocalFunctionalReporting.py validates that both targets are active functional units in the selected active local organization and enforces **no cycle across all persisted edges, even those referencing archived units**, so restoration cannot reveal a cycle. It permits multiple parents, a deliberate non-fixed-hierarchy choice. Read-only lookups into accepted directory and Structure files prevent cross-organization links.

Private storage follows existing Social patterns: 0700 data dir and 0600 file, bounded exact schema and CLI stdin requests, locked optimistic revision writes, atomic replace and fsync, refusal of corrupt/unsafe/newer documents. SocialLocalFunctionalReportingStore.qml is its isolated fixed read/update bridge; no new top-level window or modification of existing organization/portfolio/structure/location/Social label stores.

## HOW TO USE

After operator-controlled PR merge and separately approved desktop update: open **Social → USER → SETTINGS → ORGANIZATIONS → FUNCTIONAL REPORTING**. Create at least two functional units in MY STRUCTURE for the same organization. Select the company → parent unit → child unit → **+ LINK FUNCTIONS**. Repeat with another parent if appropriate. The UI refuses loops and duplicate/self-links. **SHOW ALL LINKS** reveals archived/missing references; **UNLINK FUNCTIONS → CONFIRM UNLINK** removes one relationship.

## VERIFY

New tests/messaging/test_social_local_functional_reporting_v1.py covers three fictional organizations, directed links, multiple parents, cycles and reverse-edge refusal, source archiving, stale removal, wrong-kind/cross-company refusal, duplicate/self/unknown request fields, private modes, symlinks/corruption/future-schema refusal, stdin CLI/revision checks and **byte-for-byte preservation of the six accepted local source stores**. CI also runs all relevant previous Social tests and an offscreen Qt6 Settings loader. Native genuine Quickshell two-process persistence and live desktop check are separate verification boundaries unless added here.

## WATCH OUT FOR

This graph is **manual organization metadata**, not trusted workforce reporting authority, member permissions, corporate governance or delegated access. The operator decides any future interpretation of multiple parents. Source directory/structure records can be archived concurrently and are not atomically locked with this separate file; these labels must never be an authorization input. Owner-only local data is not encryption. No organization can reach another organization's function through a new link. No automatic mapping of branch/location relationships into reporting hierarchy.

## CHECKLIST

- [x] Inspect main, Syntagma AGENTS/Hospital authority, ownership and code
- [x] Separate graph store and isolated QML singleton
- [x] Existing Settings editor, active selection, stale cleanup
- [x] Synthetic tests and Qt offscreen workflow
- [ ] Exact-head CI green
- [ ] Genuine native Quickshell persistence
- [ ] Operator review/merge
- [ ] Live functional UI acceptance

## NEXT

Verify exact-head CI and correct any scoped problems, add genuine Quickshell restart smoke, then review draft PR. Real employee/permission/reporting authority is a different future Identity Center assignment.

## DECISIONS

Implement only explicit **same-organization functional-unit relationship labels**. No rigid mandatory hierarchy, implicit ownership, cross-company propagation, employee assignments, trusted role graph, company switching, source migrations, local workstation write or merge.
