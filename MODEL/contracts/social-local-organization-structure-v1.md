# Social / Organization Structure v1: local organization units

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**CONNECTION:** External Hospital-compatible ChatGPT doctor, not verified as live Hospital registered.  
**SCOPE:** Existing Social / USER / SETTINGS / ORGANIZATIONS, local metadata only.  
**STATE:** Repository implementation, awaiting tests, review, merge and live operator acceptance.

## IMPLEMENTATION

Add **MY STRUCTURE // LOCAL ORGANIZATION UNITS** between the accepted local portfolios and Social account label associations. For each existing local organization, the operator selects one of four categories: **divisions, departments, locations, teams**. Each unit has a stable local ID, organization ID, category, user-supplied name and archived flag. The UI supports adding, renaming, two-step archival and restoration, browsing archived units and recognizing archived parent organizations.

**Purposeful v1 boundary:** The four category collections are flat *within each organization*. Divisions, departments and teams describe functional units, while locations describe geography. A division may later operate in multiple places; v1 does not force units into one rigid geographic hierarchy or invent parent/manager assignments. Existing branch/program records from the accepted organization directory stay independent. No migration, alias conversion, parent-child inference, employee assignment or link to a branch/location is performed automatically.

A separate private JSON file, XDG data / post-apollo / social / local-org-structure-v1.json, stores the new unit labels. Its versioned schema is post-apollo.social-local-org-structure.v1. The SocialLocalOrganizationStructure.py helper follows the existing owner-only private storage model: 0700 directory, 0600 file, capped exact schema, bounded input, fixed stdin requests, locked revision-checked updates, fsync and atomic replacement, fail-closed unsafe/corrupt/future-version files. New records, renames and restores require a current active local parent organization; archived organization entries still preserve existing unit names and IDs. Name uniqueness is scoped to organization plus category, not globally. Archiving retains historical names, and restore refuses duplicate active scoped names.

The SocialLocalOrganizationStructureStore.qml singleton is separate from organization/portfolio/account-label stores and does not modify them. The existing verified Identity Center display and disabled switcher are untouched. No passwords, provider tokens, employee lists, member IDs, roles, grants, real-world ownership, addresses, or company API operations enter this local structure store.

## HOW TO USE

After review and a separately authorized local source update: open **USER → SETTINGS → ORGANIZATIONS**, scroll to **MY STRUCTURE**. Pick a company, choose **DIVISIONS**, **DEPARTMENTS**, **LOCATIONS** or **TEAMS**, enter a name and press **+ ADD UNIT**. Use **SAVE** to rename, **ARCHIVE → CONFIRM ARCHIVE** to hide and **SHOW ARCHIVED UNITS → RESTORE** to recover. Organizations with archived status can be viewed via SHOW ARCHIVED ORGS; editing their units requires restoring the parent company first. All records remain local metadata.

## VERIFY

The new CI workflow runs test_social_local_org_structure_v1.py and the accepted organization directory, portfolio, Social account label link and Identity Center Settings regressions. Synthetic tests verify private durable storage, three organization scopes, all four categories, stable IDs, rename/archive/restore, duplicate scoped names, missing/archived parent rejection, stale reference retention, exact revision conflicts and malformed-file refusal. A real offscreen PySide6 Qt loader instantiates the Organizations screen. This does not demonstrate native Quickshell/Wayland interaction on the operator's workstation.

## WATCH OUT FOR

Functional units and locations can intersect but do **not** gain a location link or reporting-line relationship in v1. A team label is not an employee membership; a location is not a verified office address or a migration of an existing branch. An organization can be archived between the cross-file reference check and an update, so these local labels must **never** be used as trusted authorizations. Owner-only local metadata is not encrypted. The current authorized three-organization portfolio data stays in its original file, not rewritten by this slice.

## CHECKLIST

- [x] Inspect current Syntagma/Hospital authority and Post-Apollo source/PR ownership
- [x] Separate local structure schema and private writer
- [x] Same-screen UI with four category selectors and archive/restore
- [x] Synthetic tests and offscreen Qt CI workflow
- [ ] Exact-head GitHub checks green
- [ ] Independent review and operator acceptance
- [ ] Separately authorized live desktop verification after merge

## NEXT

Repair exact-head CI failures within this bounded scope. Review the draft pull request, then have the operator control merging and local source updates. A future separately approved task may link functional units to locations and branches, and a trusted Identity Center backend must own real staff membership, roles, permissions and scope graphs.

## DECISIONS

Operator approved continuing Organization Structure v1 following functional acceptance of local portfolios. This PR limits implementation to independently categorized local units per organization, preserving current portfolios, Social labels, existing branches and disabled verified organization switching. No local workstation writes, Quickshell restart, provider account actions, production Identity Center changes or PR merge authorized.
