# Social // Local organization-to-Social identity and account nickname links v1

**STATE:** Proposed repository implementation for review; no company verification, provider account authorization, merge, or local activation.

**PATIENT:** kudokudo1/The-Post-Apollo-Project. **CONNECTION:** External Hospital-compatible ChatGPT, with no verified live Room, Assignment, Staff Role or workstation attachment.

## IMPLEMENTATION

Within existing Social USER // SETTINGS → ORGANIZATIONS, add **SOCIAL LINKS // LOCAL LABEL ASSOCIATIONS** below the accepted organization/branch directory. Select an existing active organization, optionally a branch, then an existing Social layout identity and **+ LINK IDENTITY LABEL**. Optionally select a service and nickname already stored in SocialAccountDetailsStore to create an **account nickname association**. Browse the current target or SHOW ALL LINKS, and use UNLINK LABEL then CONFIRM UNLINK for removal.

The new SocialOrganizationLinks.py and SocialOrganizationLinksStore.qml form an independent local metadata store: XDG data / post-apollo / social / local-social-associations-v1.json. The versioned document stores only stable local orgId, optional branchId, Social identityId, and optional serviceId/accountId. No names, emails, phones, tokens, passwords, provider subjects, roles, scope grants, or legal ownership records are copied. Display names are resolved from the original stores. Missing, archived and unavailable references are shown as stale/unavailable, never verified.

Python follows the established owner-only SocialAccountDetails hardening pattern: private 0700 directory/0600 file, bounded schema, exact operations with JSON stdin, locked revision-checked writes, atomic replace and fsync, duplicate rejection, file-mode and symlink refusal, and no replacement of corrupt/future-version documents. New links require an existing nonarchived local organization/branch; a branch must actually belong to its parent organization. Unlink remains possible after archiving. Original identity layout, account nickname, and organization directory files remain unchanged by this feature.

The local link is **not an Account Broker connection, a legal owner declaration, an authorization grant, or a verified Identity Center membership**. It never selects a company or switches the Social provider session.

## HOW TO USE

After review and separately approved local sync, visit USER → SETTINGS → ORGANIZATIONS. Under SOCIAL LINKS select organization, choose ORGANIZATION LEVEL or a branch, select a Social identity, and choose + LINK IDENTITY LABEL. To associate an existing nickname, select its service and nickname then + LINK ACCOUNT NICKNAME. To create nicknames first, use SOCIAL LAYOUT → ACCOUNT NAMES. SHOW ALL LINKS includes archived or missing references so they can be unlinked with confirmation.

## VERIFY

CI runs test_social_org_links_v1.py and prior organization/Identity Center Settings regression suites. PySide6 offscreen instantiates the real Organizations QML. Synthetic tests exercise organization/branch ID scoping, account-nickname references, private durable file writing, conflict detection, missing/archived targets, stale-link removal, CLI stdin and non-credential boundaries. Offscreen Qt is **not** a real running Sway desktop or a mouse interaction test.

## WATCH OUT FOR

Owner-only storage is not encryption or strong same-UID adversary isolation. The check of local organization state and the link write are not a single cross-file transaction, so races with archiving are possible; these manual links must never be used as permissions. Social identities are layout handles, and account nicknames can be stale/renamed/removed. No permission enforcement or provider login is implemented. Do not mutate any original Social store as a side effect of linking.

## CHECKLIST

- [x] Reinspect existing contracts and current PR ownership
- [x] Local-only association schema and guarded writer
- [x] Same-screen UI with identity and saved nickname choices
- [x] Source, storage and offscreen Qt CI tests
- [ ] Exact-head CI verification
- [ ] Genuine Quickshell test of association interactions
- [ ] Independent operator review/acceptance
- [ ] Separately approved local deployment and live UI check

## NEXT

Repair any exact-head CI failures within this bounded local-association work, then review the draft PR. Future privileged organization membership, account delegation, provider connection and permissions belong to separately authorized Identity Center/Account Broker implementation.

## DECISIONS

Operator directed the next phase after accepting local Organization Manager v1. This slice is deliberately **manual label associations only**, and preserves identity/provider authorization boundaries. No PR merge, local workstation mutation, new window, live Quickshell restart or credential changes are authorized.
