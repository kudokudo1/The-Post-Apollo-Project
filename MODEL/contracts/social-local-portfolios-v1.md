# Social / Local Portfolio Organization Groups v1

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**SOURCE:** operator direction to group two LLCs, a nonprofit, future ventures and branches, with explicitly separate legal entity boundaries. Operator confirmed the accepted organization editor and Social label linking worked on the live desktop on 2026-11-02.  
**STATE:** Repository implementation for operator review. No verified Identity Center portfolio membership or auth changes.  
**HOSPITAL:** External Hospital-compatible ChatGPT (not connected or registered to a live Room, Assignment, Staff Role or Session).

## IMPLEMENTATION

Inside existing Social USER / SETTINGS / ORGANIZATIONS, insert **MY PORTFOLIOS // LOCAL GROUPS** between the accepted manual organization directory and the accepted Social label associations. An operator can create and rename local portfolios, add/remove existing active local organization IDs, archive/restore portfolios, show archived groups, and show archived/missing organization references until intentionally removed. Portfolios are many-to-many *personal management lenses*: an organization can appear in more than one local group, without changing its underlying local organization record or the links to Social account nicknames. A portfolio group is **not** a company merge, a verified tenant portfolio, a grant, or an access-control switcher.

A separate SocialLocalPortfolios.py helper persists local metadata to post-apollo/social/local-portfolios-v1.json in XDG data. The versioned schema stores only portfolio ID, display label, archive flag, and an ordered list of local organization IDs. It does not copy legal details, branch rosters, account nicknames, credentials, provider identities, membership grants or signed-in contexts. Existing organization, Social layout, and account nickname files remain unchanged by grouping. Archived or missing organization entries remain *displayable* as inactive rather than disappearing. Attaching requires a currently active existing local organization; removing a stale one remains allowed.

The helper uses the existing private Social data directory pattern: owner-only 0700 directory and 0600 file, exact schema/request validation, bounded names/records, locked optimistic revision check, atomic write with file and directory sync, fail-closed corrupt/newer/unsafe files, and explicit user actions only. The QML singleton invokes a fixed read/update helper via stdin and never passes sensitive data or arguments to external networks.

## HOW TO USE

Once merged and separately updated on the operator desktop, open USER → SETTINGS → ORGANIZATIONS and scroll to MY PORTFOLIOS. Enter a portfolio name, then + PORTFOLIO. Under that group, select + ORGANIZATION NAME from the offered existing organizations. Use SAVE to rename, REMOVE FROM GROUP then CONFIRM REMOVE to detach an organization, ARCHIVE then CONFIRM ARCHIVE to archive the group, and SHOW ARCHIVED / RESTORE to recover it. An organization can be attached to multiple portfolios. None of these steps authenticates a company or creates access grants.

## VERIFY

CI runs tests/messaging/test_social_local_portfolios_v1.py for private storage, grouping, multi-portfolio membership, stale/archived references, corrupt/unsafe file refusal, revision conflicts, fixed CLI, and no privilege fields. It also preserves existing organization directory, Social local link, and Identity Center Settings regressions, with a genuine offscreen Qt6 loader of the Organizations page. This does not constitute a live Sway mouse-interaction or desktop persistence test.

## WATCH OUT FOR

Owner-only local metadata is not encryption and does not stop malicious same-user applications. The local directory existence check during group assignment is not transactional with concurrent organization archiving, so missing/archived local references may exist and are displayed accordingly. A portfolio cannot serve as trusted membership, audited governance, delegated account authority, workforce permissions or sensitive account routing. Existing **verified** Identity Center portfolio display and disabled organization switcher stay unchanged. Full Identity Center portfolio integration belongs to a separately authorized backend-owned assignment.

## CHECKLIST

- [x] Reinspect AGENTS, Hospital authority, current Social source and open PR ownership
- [x] Separate private portfolio storage and local-only QML bridge
- [x] Existing Organizations screen portfolio management, multi-group membership, reversible archive
- [x] Synthetic tests, existing regressions and Qt offscreen workflow
- [ ] Exact-head CI verified
- [ ] Native genuine Quickshell or operator-run UI persistence acceptance
- [ ] Operator review, merge and live installation authorization

## NEXT

Review CI on this draft PR and correct bounded implementation failures without modifying the user's live workstation or permission boundaries. After operator-authorized merge and desktop sync, verify one fictional group holding a fictional LLC and nonprofit, detach and restore/archive, and persistence after reopening the Organizations panel.

## DECISIONS

This implements only **manual local organization grouping**, respecting the existing portfolio concept but not claiming verified Identity Center authorization or legal membership. No merge, local machine mutation, shell restart, real company data write or permission expansion was authorized by the user's continuation.
