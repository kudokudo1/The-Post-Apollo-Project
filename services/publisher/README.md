# SocialW Publisher // P1 local foundation

**Owner:** Post-Apollo Publisher subsystem. **State:** P1.1 merged; P1.2
proposed on a separate review branch. **Authority:** explicitly selected
local-only records. No account login, external publishing, upload or queue.

## Architecture

- Publisher remains an exclusive companion surface inside SocialW's existing
  FloatingWindow. No second window, provider index, chat adapter, or account
  identity writer.
- **P1.1** uses \`PublisherDraftStore\` as the only writer of
  \`Quickshell.dataDir/publisher-drafts-v1.json\` (text-only v1).
- **P1.2** uses a distinct single writer, \`PublisherMediaStore\`, for
  \`Quickshell.dataDir/publisher-media-v1.json\`. A media record contains a
  local file URI, harmless display name/type/byte length, stat-based stamp,
  and time. A link contains an existing draft ID and asset ID.
- The media catalog is a **reference library**, not a file upload, backup,
  snapshot, encryption service, or Camera/Trash collection. It NEVER
  deletes, copies, moves, rewrites, or scans a whole directory.
- \`PublisherMediaProbe.py\` runs read-only after explicit user selection
  and again before every preview. It requires a regular, user-owned,
  single-linked file, resolves within HOME, refuses hidden/symlinked file
  sources, validates extension + header + size, and issues a stamp from
  inode/device/size/mtime. This is **change detection**, not content integrity
  or a defense against an attacker modifying the file immediately afterward.
- Selected images preview locally in QML only after the second probe. The
  optional QtMultimedia video viewer loads lazily and never auto-plays.
  Video playback is user-triggered and muted.
- A draft must already be saved to link media. Maximum eight linked items per
  draft, 250 media records. Unlink is confirmed and only removes the
  relationship; it never touches the source file.
- Both stores use bounded versioned JSON, FileView atomicWrites, single
  pending mutation, explicit reload and fail-closed corrupt/newer-version
  errors. A FileView onSaved signal is only local write acknowledgment,
  not independent OS-level integrity proof.

## Accepted local files

Images: PNG, JPG/JPEG, WebP (32 MiB maximum each).
Videos: MP4, WebM, MOV (1 GiB maximum each).
Only files owned by the current user **inside the real HOME** are accepted.
Cloud URLs, SMB shares, hidden directories, sandboxed document-portal paths
and external drives are not granted by this slice. A file picker may provide
a portal URI; the probe will refuse if it is not an allowed local path.

There is no archive copy. If the original is renamed, replaced, edited or
deleted, a later preview fails and the reference remains for manual review.

## Operator route once merged and installed

Social → PUBLISHER → COMPOSE → SAVE DRAFT → MEDIA.
In MEDIA, IMPORT IMAGE / VIDEO adds a reference after validation and a
confirmed local metadata save. Select an item to recheck and preview it.
ATTACH TO DRAFT creates a separate local link. UNLINK requires a second click.
LIBRARY continues to display text drafts; attachments appear on the
COMPOSE MEDIA button as an actual count.

## Limitations and safety

- Both JSON stores are **unencrypted**. File names and local paths should not
  describe confidential HR, financial, health or family materials.
- A local Social identity label is NOT an authenticated person/company
  permission. P1.5 must establish the proper ownership boundary before
  multi-tenant publishing.
- No calendar scheduler, upload queue, remote tokens, API access or auto-post.
- The media probe and UI source tests run in CI, but local Wayland + Qt
  visual/runtime acceptance remains with the operator. Optional QtMultimedia
  preview availability must be confirmed on the actual host.
- Do not merge or deploy without the project's review/approval path.

## NEXT

P1.3: approved reusable templates and locked factual content, after P1.2
runtime review. P1.4: durable scheduler and queue, requiring crash-safe
reconciliation. P1.5: account permissions. P1.6: history and recovery.

## Recovery

An unmerged P1.2 branch can be closed without affecting production.
Existing P1.1 drafts require **no schema migration**. The new media file is
independent and no media originals are altered by this feature.

## P1.3 // Local reusable templates and locked source facts

- **Dependency:** P1.3 is stacked on P1.2's draft branch. Do not merge P1.3
  independently while the media-library dependency remains unaccepted.
- **Storage:** one separate local `PublisherTemplateStore` and
  `publisher-templates-v1.json`. No change to P1.1 draft or P1.2 media data.
- **Template fields:** name, category (recruitment/resource/announcement/
  creator), informational language code, freeform wording, and up to twelve
  explicit `key = value` factual fields. Versioned strict schema, bounded
  file, single-writer FileView, atomic-write acknowledgement. Unencrypted.
- **Mechanism:** `{{key}}` substitutes the exact supplied value. Unknown,
  malformed, missing, duplicated or unused locked fields reject the render.
  Recruitment requires `role`, `location`, `apply_url`; resource entries
  require `resource` and `contact`. Starter formats contain intentionally
  blank values: they cannot pass preview until the user fills them.
- **Interface:** Social → PUBLISHER → TEMPLATES → choose category → LOAD
  STARTER → fill facts → VALIDATE & PREVIEW → SAVE TEMPLATE. USE IN COMPOSE
  creates a new, **unsaved**, manually editable text draft. Existing unsaved
  Compose edits block replacement to prevent data loss.
- **Limits:** no AI rewrite, translation, platform API, authenticated facts,
  outreach automation or outgoing posts. Language is metadata only. Factual
  fields are preserved by deterministic rendering, but a user may subsequently
  edit the resulting freeform draft. Later publish gates must revalidate source
  claims and permissions; P1.3 does **not** provide that gate.
- **Verify:** Node executes the real template policy (positive rendering,
  missing fact refusal, unknown placeholders, immutable saves, corruption,
  version mismatches, language and category limits). Python source checks
  preserve the Social companion and existing draft/media writers. Native
  Quickshell UI acceptance remains separate.

**Recovery:** Close or discard the P1.3 branch without changing deployed
components. No original media or prior draft file requires migration.


## P1.4 // Durable queue and timezone scheduling (no publisher)

- **Scope:** deny-only SQLite queue. The queue is independent from the
  SocialW window; no external account, post, upload, or notification exists.
- **Storage:** owner-local \`Quickshell.dataDir/publisher-queue-v1.sqlite3\`.
  SQLite WAL, synchronous=FULL, serialized BEGIN IMMEDIATE mutations and
  stable numeric job IDs. Job records contain source draft ID/revision/digest,
  schedule details and review state, not tokens or post bodies.
- **Source check:** every schedule references an already saved P1.1 draft.
  On its due tick, its revision and SHA-256 source digest must match, otherwise
  the job is BLOCKED rather than released for review. Edits never silently
  replace a scheduled snapshot.
- **Time:** local YYYY-MM-DDTHH:MM plus IANA zone (UTC is explicit default).
  DST gaps/ambiguous times are refused on initial scheduling. Recurrences may
  be once/daily/weekly; after a due item is manually marked reviewed, an
  operator may explicitly REARM. A skipped DST gap is skipped, an ambiguous
  future slot refuses rearm. No automatic resending or backlog replay.
- **States:** scheduled, paused, needs_review, reviewed, blocked, cancelled.
  Due detection transitions to needs_review, *never published*. Cancel keeps
  history. No delete or hidden queuing.
- **Idempotency:** duplicate scheduling intents share a stable DB key and
  return the existing job, including when the original has become due.
- **User controls:** Social → PUBLISHER → CALENDAR/QUEUE. Select a saved
  draft, enter local date/time and zone, choose recurrence, and add schedule.
  REFRESH and CHECK DUE run local state checks. Pause/resume, two-click
  cancel, mark reviewed and explicit recurrence rearm are provided.
- **Independent execution:** Python CLI exposes \`tick\` and opt-in \`watch\`
  loop that can operate without an open SocialW. No systemd user unit is
  installed or started by this PR, so unattended background ticking on the
  user's actual desktop is **NOT active** until separately deployed. Queued
  due times remain durable even without the loop; REFRESH alone never sends.
- **Limitations:** \`needs_review\` is not a publication receipt. The queue
  stores no authenticated destination, no outgoing payload and no permission
  to send. P2 provider grants and transport result reconciliation are future
  work. No production or live workstation changes occur from this branch.
- **Recovery:** discard P1.4 branch without touching existing P1.1/1.2/1.3
  records. SQLite file is separately created only on first CLI use after
  deployment. An unfinished PR is not live acceptance.

**Dependency warning:** P1.3 template code is present on the feature
branch from which this work is stacked but was not yet present in the inspected
\`main\` tree. Restore/land that code through its own accepted path before
P1.4 can land. Do not treat a merged PR label as proof of mainline ancestry.


## P1.5 // Account-specific access intent foundation (grant gate CLOSED)

- **Dependency:** Stack on P1.4 draft PR #1961. No merge or workstation
  activation without explicit operator authorization. The P1.3 mainline
  continuity problem remains a separate dependency.
- **Scope:** Social → PUBLISHER → ACCESS. Select one of the *local Social layout
  identities* and enter an unverified account display alias, a supported
  provider and a narrowly defined operation such as \`post.video\`.
  This creates a local **request intent** only.
- **Storage:** \`Quickshell.dataDir/publisher-access-intents-v1.json\`,
  versioned, bounded, single-writer, FileView atomicWrites. Records store
  only a request ID, local layout identity ID, personal/organization context,
  provider identifier, account alias, one requested scope, request status and
  timestamps. No cookies, tokens, credentials, bearer claims, or access grants.
  Account aliases can still be private metadata, so do not enter secrets.
- **Statuses:** REQUESTED and WITHDRAWN. The interface requires a second click
  to withdraw; it retains local history. A matching repeat request is
  idempotent. A withdrawn request may be followed by a new request with a
  new identifier, but neither record conveys any authority.
- **Fail-closed:** Policy and singleton publish-decision methods return
  \`allowed:false\` regardless of any supplied fake approval, token,
  host-connected flag or signed receipt. \`canPublish\` is false and the
  granted-capabilities list is empty by construction.
- **Why:** A saved Social identity is an organizer layout, and account
  labels are not verified provider accounts. A browser profile or keyring
  service being available also does not verify the account owner.
- **Future trusted boundary (not implemented here):** A separate
  Connections/Identity-owned, protected host broker must independently bind
  (a) verified invoking signed program, (b) real provider account identity,
  (c) explicit operator consent and exact provider scope, (d) permitted
  personal/organization tenant, (e) expiry and revocation, and (f) a fresh
  evidence check at each publish/refresh/retry boundary. Publisher must use a
  host-owned broker result, never mutable QML flags or local JSON as a grant.
  Coordinate host ownership instead of modifying the existing broker now.
- **No publishing:** P1.4 due items remain NEEDS_REVIEW. P1.5 does not change
  SQLite jobs, add target accounts, upload content, or activate P2 APIs.
- **Recovery:** Discard P1.5 branch without touching P1.1–P1.4 data,
  provider credentials, active Social sessions, or desktop state.


## P1.6 // Local operation history, crash recovery and integrity audit

- **Dependency:** P1.6 is stacked on P1.5 PR #1964, which is stacked on P1.4
  PR #1961. Do not merge out of sequence or bypass review/visual acceptance.
- **What HISTORY means:** only local queue activity. A stored event is NOT a
  platform post, delivery receipt, Instagram/YouTube upload, OAuth permission,
  or actual provider confirmation. Each history response advertises
  \`source=LOCAL_QUEUE_ONLY\`, \`canPublish=false\`, \`posted=0\`, and
  \`providerReceipt=null\`.
- **Atomic history:** queue SQLite schema v2 adds an append-only application
  event ledger. New scheduled jobs, due/review decisions, source blocks,
  pause/resume, cancellation, acknowledgments and recurring rearm append a
  matching event within the same BEGIN IMMEDIATE transaction as the job
  mutation. Repeated idempotent scheduling produces no duplicate event.
- **Version-1 migration:** a preexisting v1 queue gets an explicit
  \`legacy_snapshot\` event for each surviving job. Its detail is
  \`LEGACY_BASELINE_UNVERIFIED\`. It does not manufacture operation history
  that was not recorded. New empty databases are created and migrated to v2.
- **Audit:** checks SQLite integrity, verifies last event/current job status
  and occurrence, scans the local event continuity trail, and compares saved
  draft revision+digest for active local jobs. Reports inconsistent history
  and stale source files without silently editing or deleting anything.
  This is consistency checking, not cryptographic tamper evidence against
  an attacker with write access to the same user-owned database.
- **Explicit reconcile:** after inspection, the operator may select a
  two-step BLOCK STALE action. It transactionally changes *only* scheduled
  or paused jobs whose original draft no longer matches to BLOCKED and
  records a local event. It cannot recreate a missing draft, re-enable
  publishing, delete a file, or bypass an inconsistent history ledger.
- **Recovery after restart:** committed jobs and local events survive process
  restart. An aborted transaction rolls back both records; repeated schedule
  calls use the original idempotency key. The headless due checker remains
  opt-in only and never dispatches posts.
- **UI:** Social → PUBLISHER → HISTORY → RELOAD HISTORY or
  AUDIT STORAGE & SOURCES; if there are stale jobs and consistent records,
  BLOCK STALE requires a second click. This view does not install services.
- **Limits:** 500 jobs and 4,000 local events; list returns the latest
  200 events. When capacity is reached, mutations fail closed instead of
  silently discarding history. The queue is owner-local, unencrypted.
- **P2 gate:** a future, separately authorized platform dispatch service
  will need verified per-account consent, immutable source/media snapshots,
  provider receipt reconciliation, retry idempotency, and security review.
  No current P1 state may be relabeled as DELIVERED/PUBLISHED.
- **Recovery:** discard this unmerged source branch without affecting P1.1
  draft, P1.2 media, P1.3 template or P1.5 request files. No live desktop
  state has been changed by this PR. Native visual acceptance is separate.
