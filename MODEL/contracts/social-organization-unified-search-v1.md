# Social / Unified Local Organization Search v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT; external Hospital-compatible; live Room/Role unverified
ASSIGNMENT: Control 2 of 7 from accepted inline Organizations usability checklist.
STATE: Draft, not yet merged, locally deployed, or operator accepted.

## IMPLEMENTATION

Keep the single-page Organizations view established by #1125 and the shared local organization editing selector from #1133. Add SEARCH LOCAL ORGANIZATION RECORDS near the top with results for local organizations, branches, portfolios, divisions/departments/teams/locations and saved link labels. No separate menus or workspaces.

Search is case-insensitive, max 80 characters. Show the complete match count and at most 60 visible rows. Inline category filters (ALL, ORGS/BRANCHES, PORTFOLIOS, STRUCTURE, LINKS), INCLUDE ARCHIVED, and CLEAR SEARCH affect presentation only. Search reads the original existing in-memory saved snapshots, not private files directly or a remote database. Portfolio results match names of attached companies. Link results match named source, target and relationship, including available Social labels.

Search also filters existing inline records: company and branch rows, portfolio rows, structure units (across unit types while searching), and saved link rows. The original Add/Edit/Archive/Restore and modifier input forms retain their existing validated operations. Source-unit filtering within the modifier form is independent and still available.

FOCUS COMPANY on an active result changes the local editing selection; for a structure unit it also selects that unit's category. Archived/stale results cannot be focused for a write. No verified organization switching or permissions result from filtering.

## HOW TO USE

After operator-authorized merge and separately approved local sync: Social → USER → SETTINGS → ORGANIZATIONS → SEARCH LOCAL ORGANIZATION RECORDS. Type an organization/branch/unit/location/portfolio/link term. Narrow results using inline category/status filters. FOCUS COMPANY to use existing editors lower on the same page; CLEAR SEARCH restores full record visibility.

## VERIFY

New static contracts cover one-page UI, categories, source-only reads and four editor filter paths. Qt6 offscreen tests use fictional local organizations, portfolios, units and associations and check category matching, archived matches, and shared edit context. Existing Organization Manager, Social link, source and native Quickshell regressions continue to run on the PR. No production data or local workstation accessed.

## WATCH OUT FOR

Search results are labels, not authenticated membership. Archived filters only affect search results; individual editors retain their own archive/restore controls. When a source store is unavailable, it contributes no results. Max 60 visible results prevents an enormous list, while the match count stays accurate.

## CHECKLIST

- [x] Verify #1133 merged, Git state and Syntagma governance
- [x] Search all supported local record types on same page
- [x] Wire four original editors to shared search text
- [x] Add contracts and Qt fixture
- [ ] Exact-head CI green
- [ ] Operator-controlled merge and desktop acceptance

## NEXT

Inspect CI and repair bounded bugs. Then hand off for review and live UI acceptance before Control 3 (record actions/archived display). Never self-merge, restart Quickshell, alter the local workstation, or add verified grants.

## DECISIONS

One page and original storage schemas, no new navigation layers or privileged action. Search is a read-only client presentation feature.
