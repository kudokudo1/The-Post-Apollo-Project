# 🏥 Hospital / Trash++ // Batch 1 coordinated Room Trash + Restore

PATIENTS // The-Post-Apollo-Project + The-Post-Apollo-Dev-Exp (PX)
ROOM // Hospital Room Trash++ Integration
STAFF // External Hospital-compatible DOC (live registration not verified)
ASSIGNMENT // Operator-approved consolidated Trash/Restore delivery, Burn separate

## IMPLEMENTATION

**Backend dependency:** PX PR #130 is stacked on existing Room name schema PR #121.
- PX 12 adds \`room_lifecycle\` state, revision and receipts.
- No original Room rows or linked Session/message/report/chart evidence is deleted.
- \`px hospital rooms\` excludes TRASHED Rooms; \`room-lifecycle-bin\` is
  metadata-only and reports no Burn capability; \`room-lifecycle-review\`
  verifies the exact Room digest and revision.
- TRASH and RESTORE are atomic with expected revision, graph digest,
  a repeated exact Room ID, and a **pinned, signed one-use authorization
  grant**. Source SQL triggers reject writers on TRASHED Rooms.
- CLI requests without `--signed-authorization-file` refuse. Pinned Ed25519
  grant checks bind action/Room/Patient/repository/revision/digest/retention
  and current host, with replay prevention inside the same transaction.
  Signing and operator consent are *not* supplied by the PX source.
- Neither a local JSON cache nor GIO is allowed to own Hospital records.

**Application partner:**
- The existing Hospital Room detail screen now reads PX's lifecycle
  revision, shows blocked/eligible controls and implements an explicit
  second confirmation step, without replacing Quick, Chat or Attach.
- The existing Trash++ **TRASH** menu adds a \`HOSP\` filter and source
  \`[HOSPITAL]\` rows from PX. They never enter file/copy BURN or BURN ALL.
- Hospital Restore uses its own read/revision check, its own PX command,
  and updates source inventory only after a matching committed receipt.
- The GIO and managed-copy source families and all their Restore/Burn
  behaviors remain separate.

## HOW TO USE (AFTER SECURE ACTIVATION)

Hospital → SURGERY → SHOW WORKERS → ROOM → TRASH++ REVIEW  
Trash++ → TRASH → HOSP → select exact Room → review → Restore

**Production hold:** the current PX v12 source contract deliberately says
\`operatorAuthenticated:false\` and \`requiresOwnerReview:true\`. The
application's \`permissionReady\` therefore fails closed and the controls
are not executable through the desktop UI. This is not a missing click
handler: the source authorization and retention decision have not been
delivered by the independently trusted PX/Connections owner. CLI
\`--confirm-room-id\` proves an explicit request but is not secure
operator identity. Never flip these flags in QML to force execution.

## VERIFY
- App UI scope and policy tests, Hospital Acceptance and Trash++ workflow.
- PX owner must verify PR #130 and its disposable v11→v12 migration,
  recovery, source writer denial, stale/concurrent-request refusal.
- Native PX + Quickshell testing requires approved installation and
  actual verified permission broker. Not done in this PR.

## WATCH OUT FOR
- The combined feature is implemented **in source**, but safe production
  enablement is blocked on trusted operator identity/seat/grant and source
  retention policy. Unmerged PRs are not installed locally.
- PX PR #121 schema v11 must land before v12; old PX binaries cannot
  read a migrated database. Backup, signed installation and rollback
  plan require independent review.
- No secure native authorization or legal hold state may be inferred from
  UI confirmation or from PX CLI flags.
- Trashed Rooms remain physically in their original SQLite DB and are
  not independent immutable snapshots. This is soft-trash, not a backup.
- Linked sessions with no endedAt and active Assignment/Chart evidence
  remain blocked, even if they look stale in the worker roster.
- Do not merge without PX+Trash++ owner security review or activate on
  the operator workstation without separate approval.

## NEXT
1. Independent PX and Trash++ review against exact heads, especially
   overlapping PX staffing/schema PRs and reader/writer query completeness.
2. Trusted source identity/retention grant bridge, installed-version gate
   and official recovery/backup rehearsal. Only then allow production UI
   permissionReady and real operator Trash/Restore.
3. Burn is Batch 2, only after separate user consent and protected custody.

## DECISIONS
Operator asked for fewer, larger deliverables; this is one PX + app batch,
not a chain of tiny rehearsal PRs. No Room mutation or live deletion performed.
