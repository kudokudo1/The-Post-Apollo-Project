# Social Organizations / Private Backup Snapshots v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT, external Hospital-compatible, live Room/Staff Role/Assignment unverified.
ASSIGNMENT: Control 6, safe first phase: snapshot creation, list and validated restore preview.
STATE: Draft PR. Not merged, deployed or operator-accepted.

## IMPLEMENTATION

Preserve one page under Social → USER → SETTINGS → ORGANIZATIONS. Add BACK UP NOW, LIST BACKUPS and VALIDATE FOR RESTORE next to the existing controls. RESTORE // LOCKED remains visibly disabled, not a simulated action.

The seven organization-label JSON files are separately written with individual atomic writes and per-file locks. That does not provide a crash-safe multi-file restore transaction. This change therefore does not overwrite a single live record file. Full restore requires independently reviewed multi-file rollback, crash recovery, live revision checks and concurrency tests.

The new services/social/SocialLocalOrgBackup.py CLI accepts only list, create and verify with an allowlisted snapshot identifier. Its snapshots contain the existing seven local Organization, Portfolio, Structure, Function/Location, Branch/Location, Reporting and Social Association documents only. They exclude contact details, account credential stores, provider tokens, authentication sessions and grant records.

Backups are written under the owner-private XDG data root, post-apollo/social/organization-backups-v1, mode 0700; files are 0600. Up to 40 snapshots are retained without auto-deletion. A create acquires all original writer locks in deterministic nonblocking order, loads/validates each source, attaches SHA-256 checksums, and creates a durable new no-clobber snapshot. List returns filenames only. Verify rejects path traversal, symlinks, oversized files, unknown/incomplete schemas, invalid documents, duplicate JSON keys and checksum mismatch. The Qt UI shows filename and success/errors, not raw document contents.

## HOW TO USE

Once operator-authorized PR merge and separate desktop update occur: Social → USER → SETTINGS → ORGANIZATIONS. Press BACK UP NOW when all seven stores are ready, LIST BACKUPS to view snapshots, choose one, then VALIDATE FOR RESTORE to check its schema and checksums. Restore remains locked pending separately authorized transaction work. This is an in-app private backup, not a download to arbitrary destinations.

## VERIFY

Temp-XDG tests check no-clobber, file/directory mode, locked writer refusal, path traversal, malformed or altered backup, checksum and strict store scope. Actual offscreen Qt6 Settings test exercises the three UI actions with synthetic process response data, guards while stores busy, and disabled restore. Existing organization/portfolio/structure/links/refresh/feedback suites remain in CI.

## WATCH OUT FOR

A backup of these seven organization labels is not a complete Post-Apollo backup. Backups are private and not encrypted. They may contain sensitive company/identity display labels, so never publish them. Manual acceptance for all previous controls is deferred by the operator, not considered complete. Do not enable Restore until multi-file safety is independently verified.

## CHECKLIST

- [x] Verify Control 5 PR #1167 merged, no overlapping Social ownership
- [x] Review Syntagma/Hospital and seven storage formats
- [x] Implement private create/list/verify and locked restore on same page
- [x] Add deferred manual UI testing register
- [ ] Exact-head GitHub CI green
- [ ] Operator PR merge and eventual manual acceptance
- [ ] Separate safe multi-file restore implementation

## NEXT

Fix any bounded CI defects. Later Control 7 is local activity history, without inventing server audit claims. Semantic color/glow work follows function control completion. No local system modifications, self-merge or Quickshell restart.

## DECISIONS

Operator elected to defer manual UI testing while continuing development. All deferred items are carried forward explicitly. The destructive restore action is unavailable until it can preserve multi-file consistency under failure and concurrent writers.
