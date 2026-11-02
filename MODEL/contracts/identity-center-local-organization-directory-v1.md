# Identity Center // Manual local organization directory v1

**PATIENT:** kudokudo1/The-Post-Apollo-Project
**CONNECTION:** External Hospital-compatible browser worker; no verified live Room, Staff Role or Session.
**STATE:** Repository implementation for operator review, not live activation.

## IMPLEMENTATION

The existing Social USER // SETTINGS → ORGANIZATIONS panel adds a manual
directory for LLC, nonprofit and other organization names, plus branches and
programs. Users can add, rename, archive and restore both organization and branch
records. Archive requires a second click. There is no permanent deletion action.

A separate SocialOrganizationDirectoryStore.qml singleton calls fixed Python
read/update operations with JSON on stdin. SocialOrganizationDirectory.py stores
only local names, kinds and reversible archive flags in the XDG data directory
post-apollo/social/local-organizations-v1.json (private directory 0700, file
0600, atomic replace/fsync, locked writes and revision conflicts). Missing files
read as empty until an explicit edit. Corrupt, unsafe or future-version storage
does not get overwritten. The existing SocialIdentityStore app families and
SocialAccountDetails records are neither migrated nor modified.

Local organization metadata is *not* verified Identity Center membership.
No tokens, account sessions, scopes, roles, authorization grants, API requests
or organization switching are involved. The old read-only verified membership
panel and disabled switcher remain in place.

## HOW TO USE

Open USER // SETTINGS → ORGANIZATIONS, enter a name, choose LLC, NONPROFIT or
OTHER, then select + ORGANIZATION. Rename with SAVE. Add a branch or program
beneath its organization with + BRANCH. Select ARCHIVE then CONFIRM ARCHIVE
to hide it; SHOW ARCHIVED and RESTORE undo the action. RELOAD DIRECTORY
re-reads the persisted file after a conflict or error.

## VERIFY

Run the tests in a disposable checkout:

    python3 -m unittest discover -s tests/messaging -p 'test_social_local_organizations.py' -v
    python3 -m unittest discover -s tests/messaging -p 'test_identity_center_settings_sections.py' -v

The tests cover editing, version/revision bounds, private storage, corrupt-file
refusal, UI action wiring, unchanged settings route and disabled switcher. CI is
not live Quickshell or a compositor visual test.

## WATCH OUT FOR

Local data is owner-only but not encrypted or safe against malicious same-UID
processes. No live production authentication or company creation is implied.
Do not restart the desktop, install services, change real company records or
claim authenticated organization selection from a local label.

## CHECKLIST

- [x] Private local organization/branch store, separate from verified IPC
- [x] Existing Settings editor, archive/restore instead of destructive delete
- [x] Bounded validation and revision-checked atomic edits
- [x] Synthetic unit tests and CI workflow
- [ ] Exact-head CI verification
- [ ] Independent security/UI review and operator acceptance
- [ ] Separately authorized live desktop verification

## NEXT

Review PR checks and merged source as needed. Live rollout needs a separate
operator-controlled local update and visual/persistence check.

## DECISIONS

This authorization covers repository implementation only. No PR merge, local
filesystem writes or Quickshell restart was authorized. Identity Center remains
the exclusive authority for verified memberships and permissions.
